"""
sockets.py
----------
All SocketIO event handlers.
Imports app/socketio from app.py and hardware from hardware.py.
"""

import json
import os
import time
import imageProcess
from flask import request
from flask_socketio import emit

from app import socketio, thread_lock
from hardware import net, ios
from logger import logEvent
from services.config_service import update_fish_params


FLASH_SETTLE_SECONDS = float(os.getenv("FLASH_SETTLE_SECONDS", "0.03"))
FLASH_FRAME_SKIP = int(os.getenv("FLASH_FRAME_SKIP", "2"))
FLASH_FRAME_TIMEOUT = float(os.getenv("FLASH_FRAME_TIMEOUT", "0.35"))

# Scale polling.  At 9600 baud 8N2 a read_registers round trip costs ~20 ms of
# line time plus the instrument's own response delay, so the old 25 ms tension
# period was asking for more than the bus can deliver and produced timeouts.
WEIGHT_POLL_INTERVAL = float(os.getenv("WEIGHT_POLL_INTERVAL", "0.25"))
TENSION_POLL_INTERVAL = float(os.getenv("TENSION_POLL_INTERVAL", "0.05"))
SCALE_ERROR_BACKOFF = float(os.getenv("SCALE_ERROR_BACKOFF", "1.0"))
CALIBRATION_LEASE_SECONDS = float(os.getenv("CALIBRATION_LEASE_SECONDS", "300"))


# ─────────────────────────── background helpers ───────────────────────────

def frame_is_ready():
    socketio.emit('frame_ready', "frame ready")


# Last reading produced by the poller, so the on-demand handlers can answer
# from cache instead of putting a second reader on the RS485 bus.  Keyed by
# mode: a weight snapshot must never be served as a tension reading.
_last_snapshot = {"weight": None, "tension": None}
_poller_started = False
_poller_task = None
_calibration_owner_sid = None
_calibration_last_activity = 0.0


class CalibrationBusyError(RuntimeError):
    """Raised when another Socket.IO client owns the calibration session."""


def _release_calibration(sid=None, force=False):
    """Release the calibration lease and resume weight polling."""
    global _calibration_owner_sid, _calibration_last_activity

    if _calibration_owner_sid is None:
        if force:
            net.setCalibrating(False)
        return None
    if not force and sid != _calibration_owner_sid:
        return None

    released_owner = _calibration_owner_sid
    _calibration_owner_sid = None
    _calibration_last_activity = 0.0
    net.setCalibrating(False)
    return released_owner


def _expire_calibration_if_needed():
    """Expire an abandoned calibration without affecting another client."""
    if _calibration_owner_sid is None:
        return False
    if time.monotonic() - _calibration_last_activity < CALIBRATION_LEASE_SECONDS:
        return False

    owner = _release_calibration(force=True)
    socketio.emit(
        "calibration_expired",
        {"error": "La sesion de calibracion vencio por inactividad"},
    )
    logEvent(
        etapa="CALIBRATION",
        status="ERROR",
        error_code="CALIBRATION_TIMEOUT",
        error_msg="La calibracion vencio por inactividad",
        additional_data={"owner_sid": owner},
    )
    return True


def _claim_calibration(sid):
    """Claim or refresh the calibration lease for one Socket.IO client."""
    global _calibration_owner_sid, _calibration_last_activity

    _expire_calibration_if_needed()
    if _calibration_owner_sid not in (None, sid):
        raise CalibrationBusyError("Otra sesion ya esta calibrando la bascula")
    _calibration_owner_sid = sid
    _calibration_last_activity = time.monotonic()
    _last_snapshot["weight"] = None
    _last_snapshot["tension"] = None
    net.setCalibrating(True)


def _ensure_poller():
    """Start the polling greenlet once, on the first client connection.

    update_net_status() used to be dead code - nothing ever started it - so
    every view had to drive its own setInterval and the sample rate depended
    on the browser.
    """
    global _poller_started, _poller_task
    if _poller_started:
        return
    try:
        task = socketio.start_background_task(update_net_status)
    except Exception:
        _poller_started = False
        _poller_task = None
        raise
    _poller_task = task
    _poller_started = True


def _emit_scale_snapshot(snapshot, tension_mode):
    """Push one reading to the UI.

    `weight_update` / `tension_update` keep carrying the bare number so older
    views keep working; `scale_status` carries stability and instrument faults
    straight from the STATUS REGISTER so the UI no longer has to guess.
    """
    value = snapshot["net"]
    socketio.emit('tension_update' if tension_mode else 'weight_update', value)
    socketio.emit('scale_status', {
        "value": value,
        "gross": snapshot["gross"],
        "stable": snapshot["stable"],
        "near_zero": snapshot["near_zero"],
        "faults": snapshot["faults"],
        "ok": snapshot["ok"],
        "stale": snapshot.get("stale", False),
        "age_seconds": snapshot.get("age_seconds", 0.0),
        "mode": "tension" if tension_mode else "weight",
    })


def _poller_loop():
    """Background thread: continuously pushes weight or tension to the UI.

    This loop must never die: before, a single NoResponseError from the
    transmitter killed the greenlet and the weight silently froze for the rest
    of the session.
    """
    consecutive_errors = 0
    last_faults = None

    while True:
        _expire_calibration_if_needed()
        tension_mode = net.isOnTensionMode()
        try:
            snapshot = (net.readTensionSnapshot() if tension_mode
                        else net.readWeightSnapshot())
        except Exception as e:                       # noqa: BLE001
            _last_snapshot["tension" if tension_mode else "weight"] = None
            consecutive_errors += 1
            if consecutive_errors in (1, 5) or consecutive_errors % 50 == 0:
                logEvent(
                    etapa="SYSTEM", status="ERROR",
                    error_code="SCALE_READ_ERROR", error_msg=str(e),
                    additional_data={"consecutive_errors": consecutive_errors,
                                     "mode": "tension" if tension_mode else "weight"},
                )
                socketio.emit('scale_error', {"error": str(e),
                                              "consecutive": consecutive_errors})
            socketio.sleep(SCALE_ERROR_BACKOFF)
            continue

        consecutive_errors = 0

        # Surface load-cell / ADC / overload faults once per transition instead
        # of on every poll.
        faults = tuple(snapshot["faults"])
        if faults != last_faults:
            if faults:
                logEvent(
                    etapa="SYSTEM", status="ERROR",
                    error_code="SCALE_FAULT", error_msg=", ".join(faults),
                    additional_data={"faults": list(faults)},
                )
            last_faults = faults

        if snapshot.get("calibrating"):
            socketio.sleep(WEIGHT_POLL_INTERVAL)
            continue

        _last_snapshot["tension" if tension_mode else "weight"] = snapshot
        _emit_scale_snapshot(snapshot, tension_mode)
        socketio.sleep(TENSION_POLL_INTERVAL if tension_mode
                       else WEIGHT_POLL_INTERVAL)


def update_net_status():
    """Supervise the polling loop and restart it after unexpected failures."""
    global _poller_started, _poller_task

    try:
        while True:
            try:
                _poller_loop()
            except Exception as exc:  # noqa: BLE001 - supervisor must stay alive
                try:
                    logEvent(
                        etapa="SYSTEM",
                        status="ERROR",
                        error_code="SCALE_POLLER_ERROR",
                        error_msg=str(exc),
                        additional_data={"action": "poller_restart"},
                    )
                except Exception:
                    print("Scale poller failed:", exc)
                try:
                    socketio.emit(
                        "scale_error", {"error": str(exc), "supervisor": True}
                    )
                except Exception:
                    pass
                socketio.sleep(SCALE_ERROR_BACKOFF)
    finally:
        _poller_started = False
        _poller_task = None


# ─────────────────────────── connection ───────────────────────────────────

@socketio.on('connect')
def on_connect(auth):
    print("Client connected")
    ios.set_laser(True)
    ios.set_flash(False)
    _ensure_poller()


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print("Client disconnected")
    owner = _release_calibration(sid=sid)
    if owner is not None:
        logEvent(
            etapa="CALIBRATION",
            status="WARNING",
            error_code="CALIBRATION_ABANDONED",
            error_msg="El cliente se desconecto durante la calibracion",
            additional_data={"owner_sid": owner},
        )


# ─────────────────────────── hardware / scale ─────────────────────────────

@socketio.event
def calibrate_load_cell(data):
    sid = request.sid
    try:
        if not isinstance(data, dict):
            raise ValueError("Los datos de calibracion deben ser un objeto")
        step = data['step']
        args = data['args']
        _claim_calibration(sid)

        with thread_lock:
            print("calibrate load cell step:", step, " args:", args)
            net.remote_calibration(step, args)
            logEvent(
                etapa="CALIBRATION", status="SUCCESS",
                additional_data={"calibration_type": "load_cell", "step": step, "args": args},
            )
        if step == 4:
            _release_calibration(sid=sid)
        emit('calibration_step_commited', "step commited")
    except CalibrationBusyError as exc:
        logEvent(
            etapa="CALIBRATION",
            status="WARNING",
            error_code="CALIBRATION_BUSY",
            error_msg=str(exc),
            additional_data={"request_sid": sid},
        )
        emit('calibration_error', {"error": str(exc)})
    except Exception as e:
        # Never leave isCalibrating latched on: readWeight() returns 0 while it
        # is set, so a failed step used to freeze the weight display at zero
        # until the operator happened to reopen the calibration dialog.
        _release_calibration(sid=sid)
        logEvent(
            etapa="CALIBRATION", status="ERROR",
            error_code="LOAD_CELL_CALIB_ERROR", error_msg=str(e),
            additional_data={"calibration_type": "load_cell",
                             "step": data.get('step') if isinstance(data, dict) else None,
                             "args": data.get('args') if isinstance(data, dict) else None},
        )
        emit('calibration_error', {"error": str(e)})


@socketio.event
def resume_net_update(data=None):
    sid = request.sid
    if _calibration_owner_sid not in (None, sid):
        emit('calibration_error', {"error": "Otra sesion controla la calibracion"})
        return
    _release_calibration(sid=sid, force=_calibration_owner_sid is None)


@socketio.event
def enter_to_tension_test(data=None):
    # This used to only print, so READING_MODE never left weight mode and the
    # belly view had to poll get_tension by hand.
    with thread_lock:
        net.enterToTensionTest()


@socketio.event
def enter_to_weight_mode(data=None):
    with thread_lock:
        net.enterToWeightMode()


@socketio.event
def set_zero(data=None):
    with thread_lock:
        net.setZero(bool(data))


@socketio.event
def set_tare(data=None):
    with thread_lock:
        net.setTare(bool(data))


@socketio.event
def clear_tare(data=None):
    with thread_lock:
        net.clearTare(bool(data))


def _read_scale_snapshot(tension_mode):
    try:
        return (net.readTensionSnapshot() if tension_mode
                else net.readWeightSnapshot())
    except Exception as exc:  # noqa: BLE001 - surface hardware unavailability
        emit('scale_error', {"error": str(exc), "on_demand": True})
        return None


def _serve_cached(tension_mode):
    """Answer an on-demand poll from the poller's cache.

    Hitting the bus again here would put a second reader on the same RS485
    line as the background poller and roughly double the traffic.  Falls back
    to a real read only until the poller has produced its first sample for
    that mode.
    """
    key = "tension" if tension_mode else "weight"
    snapshot = _last_snapshot[key]
    if snapshot is None:
        snapshot = _read_scale_snapshot(tension_mode)
        if snapshot is None:
            return
        _last_snapshot[key] = snapshot
    _emit_scale_snapshot(snapshot, tension_mode)


@socketio.event
def update_net(data=None):
    _serve_cached(tension_mode=False)


@socketio.event
def get_tension(data=None):
    _serve_cached(tension_mode=True)


@socketio.event
def get_scale_status(data=None):
    """Full instrument state on demand: value, stability and faults."""
    snapshot = _last_snapshot["weight"] or _read_scale_snapshot(False)
    if snapshot is None:
        return
    emit('scale_status', {
        "value": snapshot["net"],
        "gross": snapshot["gross"],
        "stable": snapshot["stable"],
        "near_zero": snapshot["near_zero"],
        "faults": snapshot["faults"],
        "ok": snapshot["ok"],
        "division": snapshot["division"],
        "stale": snapshot.get("stale", False),
        "age_seconds": snapshot.get("age_seconds", 0.0),
    })


# ─────────────────────────── vision / capture ─────────────────────────────

@socketio.event
def get_analysis_data(data=None):
    emit('analysis_data', imageProcess.get_analysis_data())


def _run_analysis_in_tpool(frame=None):
    """Publish a capture only after OpenCV returns a fresh valid result.

    The CPU-bound analysis runs in a real OS thread via eventlet.tpool so the
    eventlet IO loop is never blocked. frame_is_ready() (which calls
    socketio.emit) is invoked here, AFTER tpool.execute() returns, so we are
    back in greenlet context; run_analysis() must NOT call it itself.

    A capture is published only when run_analysis() reports ok. Otherwise the
    previous fish's measurements would stay on screen as if they were new.
    """
    import eventlet.tpool

    try:
        result = eventlet.tpool.execute(imageProcess.run_analysis, frame)
        if not result or not result.get("ok"):
            error_msg = (result or {}).get("reason", "El analisis no produjo resultados")
            socketio.emit("analysis_error", {"error": error_msg})
            logEvent(
                etapa="CAPTURE",
                status="ERROR",
                error_code="ANALYSIS_INVALID",
                error_msg=error_msg,
            )
            return

        frame_is_ready()
        logEvent(
            etapa="CAPTURE",
            status="SUCCESS",
            additional_data={
                "action": "capture_completed",
                "raw_image_path": result.get("image_path"),
            },
        )
    except Exception as exc:  # noqa: BLE001 - protect SocketIO worker
        logEvent(
            etapa="CAPTURE",
            status="ERROR",
            error_code="CAPTURE_ERROR",
            error_msg=str(exc),
        )
        socketio.emit("analysis_error", {"error": "Error interno durante el analisis"})


def _capture_with_synced_flash():
    """Synchronize flash and capture against actual camera frames.

    Old flow used a fixed sleep after turning the flash on. This waits for
    fresh frames that are known to arrive after the flash trigger, which cuts
    latency and makes timing tunable by frame count instead of guesswork.
    """
    flash_started = False
    try:
        print("capturing")
        logEvent(etapa="CAPTURE", status="INFO",
                 additional_data={
                     "action": "capture_started",
                     "flash_sync": {
                         "settle_seconds": FLASH_SETTLE_SECONDS,
                         "frame_skip": FLASH_FRAME_SKIP,
                         "timeout": FLASH_FRAME_TIMEOUT,
                     },
                 })

        with thread_lock:
            frame_marker = imageProcess.get_frame_marker()
            ios.set_laser(False)
            ios.set_flash(True)
            flash_started = True

        if FLASH_SETTLE_SECONDS > 0:
            socketio.sleep(FLASH_SETTLE_SECONDS)

        frame = imageProcess.wait_for_frame_since(
            frame_marker["seq"],
            skip_frames=FLASH_FRAME_SKIP,
            timeout=FLASH_FRAME_TIMEOUT,
        )

        with thread_lock:
            ios.set_flash(False)
            ios.set_laser(True)
            flash_started = False

            captured_frame = imageProcess.handle_capture(frame_is_ready, frame=frame)
            socketio.start_background_task(_run_analysis_in_tpool, captured_frame)
    except Exception as e:
        if flash_started:
            try:
                with thread_lock:
                    ios.set_flash(False)
                    ios.set_laser(True)
            except Exception:
                pass
        logEvent(etapa="CAPTURE", status="ERROR",
                 error_code="CAPTURE_ERROR", error_msg=str(e))
        print(f"Error en captura: {e}")


@socketio.event
def capture(data=None):
    socketio.start_background_task(_capture_with_synced_flash)


@socketio.event
def reset(data=None):
    try:
        print("reseting")
        imageProcess.handle_reset()
        logEvent(etapa="RESET", status="SUCCESS",
                 additional_data={"action": "reset_completed"})
    except Exception as e:
        logEvent(etapa="RESET", status="ERROR",
                 error_code="RESET_ERROR", error_msg=str(e))


@socketio.event
def reset_defects(data=None):
    print("reseting defects")


@socketio.event
def laser(data=None):
    print("laser")


# ─────────────────────────── fish params ──────────────────────────────────

@socketio.event
def set_fish_data(data):
    print("set fish data recibido:", data)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as ex:
            print("Error parseando datos:", ex)
            emit("fishParamsResponse", {"error": "Formato inválido"})
            return
    result = update_fish_params(data)
    result.pop("_http_status", None)
    emit("fishParamsResponse", result)

"""
sockets.py
----------
All SocketIO event handlers.
Imports app/socketio from app.py and hardware from hardware.py.
"""

import json
import os
import imageProcess
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


# ─────────────────────────── background helpers ───────────────────────────

def frame_is_ready():
    socketio.emit('frame_ready', "frame ready")


# Last reading produced by the poller, so the on-demand handlers can answer
# from cache instead of putting a second reader on the RS485 bus.  Keyed by
# mode: a weight snapshot must never be served as a tension reading.
_last_snapshot = {"weight": None, "tension": None}
_poller_started = False


def _ensure_poller():
    """Start the polling greenlet once, on the first client connection.

    update_net_status() used to be dead code - nothing ever started it - so
    every view had to drive its own setInterval and the sample rate depended
    on the browser.
    """
    global _poller_started
    if _poller_started:
        return
    _poller_started = True
    socketio.start_background_task(update_net_status)


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
        "mode": "tension" if tension_mode else "weight",
    })


def update_net_status():
    """Background thread: continuously pushes weight or tension to the UI.

    This loop must never die: before, a single NoResponseError from the
    transmitter killed the greenlet and the weight silently froze for the rest
    of the session.
    """
    consecutive_errors = 0
    last_faults = None

    while True:
        tension_mode = net.isOnTensionMode()
        try:
            snapshot = (net.readTensionSnapshot() if tension_mode
                        else net.readWeightSnapshot())
        except Exception as e:                       # noqa: BLE001
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


# ─────────────────────────── connection ───────────────────────────────────

@socketio.on('connect')
def on_connect(auth):
    print("Client connected")
    ios.set_laser(True)
    ios.set_flash(False)
    _ensure_poller()


@socketio.on('disconnect')
def on_disconnect():
    print("Client disconnected")


# ─────────────────────────── hardware / scale ─────────────────────────────

@socketio.event
def calibrate_load_cell(data):
    try:
        with thread_lock:
            net.setCalibrating(True)
            step = data['step']
            args = data['args']
            print("calibrate load cell step:", step, " args:", args)
            net.remote_calibration(step, args)
            logEvent(
                etapa="CALIBRATION", status="SUCCESS",
                additional_data={"calibration_type": "load_cell", "step": step, "args": args},
            )
        emit('calibration_step_commited', "step commited")
    except Exception as e:
        # Never leave isCalibrating latched on: readWeight() returns 0 while it
        # is set, so a failed step used to freeze the weight display at zero
        # until the operator happened to reopen the calibration dialog.
        net.setCalibrating(False)
        logEvent(
            etapa="CALIBRATION", status="ERROR",
            error_code="LOAD_CELL_CALIB_ERROR", error_msg=str(e),
            additional_data={"calibration_type": "load_cell",
                             "step": data.get('step'), "args": data.get('args')},
        )
        emit('calibration_error', {"error": str(e)})


@socketio.event
def resume_net_update(data=None):
    net.setCalibrating(False)


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
        snapshot = (net.readTensionSnapshot() if tension_mode
                    else net.readWeightSnapshot())
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
    snapshot = _last_snapshot["weight"] or net.readWeightSnapshot()
    emit('scale_status', {
        "value": snapshot["net"],
        "gross": snapshot["gross"],
        "stable": snapshot["stable"],
        "near_zero": snapshot["near_zero"],
        "faults": snapshot["faults"],
        "ok": snapshot["ok"],
        "division": snapshot["division"],
    })


# ─────────────────────────── vision / capture ─────────────────────────────

@socketio.event
def get_analysis_data(data=None):
    emit('analysis_data', imageProcess.get_analysis_data())


def _run_analysis_in_tpool():
    """Greenlet that offloads the CPU-intensive OpenCV analysis to a real OS
    thread via eventlet.tpool so the eventlet IO loop is never blocked.

    IMPORTANT: frame_is_ready() (which calls socketio.emit) is called here,
    AFTER tpool.execute() returns, so we are back in greenlet context.
    run_analysis() must NOT call the callback itself.
    """
    import eventlet.tpool
    try:
        eventlet.tpool.execute(imageProcess.run_analysis)
        # Back in greenlet context — safe to emit socket events
        frame_is_ready()
        logEvent(etapa="CAPTURE", status="SUCCESS",
                 additional_data={"action": "capture_completed"})
    except Exception as e:
        logEvent(etapa="CAPTURE", status="ERROR",
                 error_code="CAPTURE_ERROR", error_msg=str(e))
        print(f"Error en análisis: {e}")


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

        imageProcess.handle_capture(frame_is_ready, frame=frame)
        socketio.start_background_task(_run_analysis_in_tpool)
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
    update_fish_params(data)

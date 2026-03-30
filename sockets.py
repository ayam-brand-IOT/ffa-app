"""
sockets.py
----------
All SocketIO event handlers.
Imports app/socketio from app.py and hardware from hardware.py.
"""

import json
import time
import imageProcess
from flask_socketio import emit

from app import socketio, thread_lock
from hardware import net, ios
from logger import logEvent
from services.config_service import update_fish_params


# ─────────────────────────── background helpers ───────────────────────────

def frame_is_ready():
    socketio.emit('frame_ready', "frame ready")


def update_net_status():
    """Background thread: continuously pushes weight or tension to the UI."""
    while True:
        if net.isOnTensionMode():
            socketio.emit('tension_update', net.readTenstion())
            socketio.sleep(0.025)
        else:
            socketio.emit('weight_update', net.readWeight())
            socketio.sleep(0.5)


# ─────────────────────────── connection ───────────────────────────────────

@socketio.on('connect')
def on_connect(auth):
    print("Client connected")
    ios.set_laser(True)
    ios.set_flash(False)


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
    with thread_lock:
        print("enter to tension test")


@socketio.event
def enter_to_weight_mode(data=None):
    with thread_lock:
        net.enterToWeightMode()


@socketio.event
def set_zero(data=None):
    with thread_lock:
        net.setZero()


@socketio.event
def set_tare(data=None):
    with thread_lock:
        net.setTare(bool(data))


@socketio.event
def update_net(data=None):
    print("net update")
    with thread_lock:
        weight = net.readWeight()
    socketio.emit('weight_update', weight)


@socketio.event
def get_tension(data=None):
    print("tension update")
    with thread_lock:
        tension = net.readTenstion()
    socketio.emit('tension_update', tension)


# ─────────────────────────── vision / capture ─────────────────────────────

@socketio.event
def get_analysis_data(data=None):
    emit('analysis_data', imageProcess.get_analysis_data())


def _run_analysis_in_tpool():
    """Greenlet that offloads the CPU-intensive OpenCV analysis to a real OS
    thread via eventlet.tpool so the eventlet IO loop is never blocked."""
    import eventlet.tpool
    try:
        eventlet.tpool.execute(imageProcess.run_analysis)
        logEvent(etapa="CAPTURE", status="SUCCESS",
                 additional_data={"action": "capture_completed"})
    except Exception as e:
        logEvent(etapa="CAPTURE", status="ERROR",
                 error_code="CAPTURE_ERROR", error_msg=str(e))
        print(f"Error en análisis: {e}")


@socketio.event
def capture(data=None):
    try:
        ios.timered_flash()
        time.sleep(1)
        print("capturing")
        logEvent(etapa="CAPTURE", status="INFO",
                 additional_data={"action": "capture_started"})
        # Snapshot frame and store callback immediately (fast)
        imageProcess.handle_capture(frame_is_ready)
        # Dispatch heavy analysis to a real OS thread; returns immediately
        socketio.start_background_task(_run_analysis_in_tpool)
    except Exception as e:
        logEvent(etapa="CAPTURE", status="ERROR",
                 error_code="CAPTURE_ERROR", error_msg=str(e))
        print(f"Error en captura: {e}")


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

#!/usr/bin/env python3
"""Focused tests for calibration leases and poller startup supervision."""

import sys
import threading
import types
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
APP_DIR = TESTS_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


class FakeSocketIO:
    def __init__(self):
        self.emitted = []
        self.started = []

    def event(self, function):
        return function

    def on(self, event_name):
        return lambda function: function

    def emit(self, event_name, payload=None):
        self.emitted.append((event_name, payload))

    def sleep(self, seconds):
        return None

    def start_background_task(self, function, *args):
        task = object()
        self.started.append((function, args, task))
        return task


class FakeNet:
    def __init__(self):
        self.calibrating = False

    def setCalibrating(self, value):
        self.calibrating = bool(value)


socketio = FakeSocketIO()
net = FakeNet()
request = types.SimpleNamespace(sid="client-a")

app_module = types.ModuleType("app")
app_module.app = object()
app_module.socketio = socketio
app_module.thread_lock = threading.Lock()
sys.modules["app"] = app_module

hardware_module = types.ModuleType("hardware")
hardware_module.net = net
hardware_module.ios = types.SimpleNamespace()
sys.modules["hardware"] = hardware_module

image_process_module = types.ModuleType("imageProcess")
sys.modules["imageProcess"] = image_process_module

flask_module = types.ModuleType("flask")
flask_module.request = request
sys.modules["flask"] = flask_module

flask_socketio_module = types.ModuleType("flask_socketio")
flask_socketio_module.emit = lambda *args, **kwargs: None
sys.modules["flask_socketio"] = flask_socketio_module

logger_module = types.ModuleType("logger")
logger_module.logEvent = lambda **kwargs: None
sys.modules["logger"] = logger_module

config_service_module = types.ModuleType("services.config_service")
config_service_module.update_fish_params = lambda data: {"status": "ok"}
sys.modules["services.config_service"] = config_service_module

import sockets  # noqa: E402


def reset_state():
    sockets._calibration_owner_sid = None
    sockets._calibration_last_activity = 0.0
    sockets._poller_started = False
    sockets._poller_task = None
    socketio.emitted.clear()
    socketio.started.clear()
    net.calibrating = False


def test_calibration_is_owned_by_one_client():
    reset_state()
    sockets._claim_calibration("client-a")
    assert net.calibrating is True

    try:
        sockets._claim_calibration("client-b")
    except sockets.CalibrationBusyError:
        pass
    else:
        raise AssertionError("A second client must not take over calibration")

    assert sockets._release_calibration(sid="client-b") is None
    assert net.calibrating is True
    assert sockets._release_calibration(sid="client-a") == "client-a"
    assert net.calibrating is False


def test_abandoned_calibration_expires():
    reset_state()
    original_monotonic = sockets.time.monotonic
    clock = [100.0]
    sockets.time.monotonic = lambda: clock[0]
    sockets.CALIBRATION_LEASE_SECONDS = 10.0
    try:
        sockets._claim_calibration("client-a")
        clock[0] = 111.0
        assert sockets._expire_calibration_if_needed() is True
        assert sockets._calibration_owner_sid is None
        assert net.calibrating is False
        assert socketio.emitted[-1][0] == "calibration_expired"
    finally:
        sockets.time.monotonic = original_monotonic


def test_owner_disconnect_releases_calibration():
    reset_state()
    request.sid = "client-a"
    sockets._claim_calibration(request.sid)

    sockets.on_disconnect()

    assert sockets._calibration_owner_sid is None
    assert net.calibrating is False


def test_poller_start_is_latched_only_after_success():
    reset_state()
    sockets._ensure_poller()
    assert sockets._poller_started is True
    assert sockets._poller_task is socketio.started[0][2]
    sockets._ensure_poller()
    assert len(socketio.started) == 1

    reset_state()
    original_start = socketio.start_background_task

    def fail_start(function, *args):
        raise RuntimeError("cannot start poller")

    socketio.start_background_task = fail_start
    try:
        try:
            sockets._ensure_poller()
        except RuntimeError:
            pass
        else:
            raise AssertionError("Poller startup failure must be surfaced")
        assert sockets._poller_started is False
        assert sockets._poller_task is None
    finally:
        socketio.start_background_task = original_start


def main():
    test_calibration_is_owned_by_one_client()
    test_abandoned_calibration_expires()
    test_owner_disconnect_releases_calibration()
    test_poller_start_is_latched_only_after_success()
    print("Socket availability tests passed")


if __name__ == "__main__":
    main()

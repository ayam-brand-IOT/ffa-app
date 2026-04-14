# eventlet.monkey_patch() MUST be the very first thing that runs.
# It replaces Python's stdlib (socket, threading, time, etc.) with
# eventlet-compatible greenlet versions.  Doing this after any import
# that touches those modules is too late and causes subtle bugs.
import hardware
from hardware import DEV_MODE
import eventlet
eventlet.monkey_patch()

# hardware must be imported first so that net/ios are available before
# sockets.py and routes.py are loaded.
import sockets   # noqa: F401 - registers all SocketIO handlers
import routes    # noqa: F401 - registers all HTTP routes

from app import app, socketio
from logger import logEvent


if __name__ == "__main__":
    logEvent(
        etapa="SYSTEM",
        status="INFO",
        additional_data={
            "event_type": "app_startup",
            "description": "FFA Application started",
            "dev_mode": DEV_MODE,
        },
    )

    try:
        socketio.run(app, host="0.0.0.0", port="3030", allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logEvent(
            etapa="SYSTEM",
            status="INFO",
            additional_data={
                "event_type": "app_shutdown",
                "description": "FFA Application stopped by user",
            },
        )
    except Exception as e:
        logEvent(
            etapa="SYSTEM",
            status="ERROR",
            error_code="APP_CRASH",
            error_msg=str(e),
            additional_data={
                "event_type": "app_crash",
                "description": "FFA Application crashed unexpectedly",
            },
        )
        raise
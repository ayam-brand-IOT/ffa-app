# hardware must be imported first so that net/ios are available before
# sockets.py and routes.py are loaded.
import hardware  # noqa: F401 - side-effect import (sets up net/ios)
import sockets   # noqa: F401 - registers all SocketIO handlers
import routes    # noqa: F401 - registers all HTTP routes

from app import app, socketio
from hardware import DEV_MODE
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

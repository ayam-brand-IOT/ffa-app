import logging
from threading import Lock
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

app = Flask(__name__,
            static_folder="./dist/static",
            template_folder="./dist")
app.config['SECRET_KEY'] = 'secret!'
CORS(app)

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    # No transports restriction: allows WebSocket upgrade, falling back to polling.
    # Forcing polling-only caused 'Too many packets in payload' errors under load.
)

# Shared lock used by socket handlers that call hardware directly.
# Note: TLB_MODBUS and imageProcess now have their own internal locks,
# so this lock is only needed to sequence multi-step operations in handlers.
thread_lock = Lock()

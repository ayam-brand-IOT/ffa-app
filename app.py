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
    async_mode='eventlet',  # eventlet provides its own WSGI server with native WebSocket support
    logger=False,
    engineio_logger=False,
)

# Shared lock used by socket handlers that call hardware directly.
# Note: TLB_MODBUS and imageProcess now have their own internal locks,
# so this lock is only needed to sequence multi-step operations in handlers.
thread_lock = Lock()

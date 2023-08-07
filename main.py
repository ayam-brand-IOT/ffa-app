import cv2
import json
import keyboard
import IOs as ios
import imageProcess
import TLB_MODBUS as net
from threading import Lock
from flask_cors import CORS
from flask_socketio import SocketIO, send, emit
from flask import Flask, render_template, Response, stream_with_context, request, copy_current_request_context


async_mode = None

app = Flask(__name__,
            static_folder = "./dist/static",
            template_folder = "./dist")

app.config['SECRET_KEY'] = 'secret!'
CORS(app)

socketio = SocketIO(app,cors_allowed_origins="*", async_mode='threading')
keyboard_thread = None
net_thread = None
thread_lock = Lock()


################################################ callbacks  ################################################

def update_status(keys):
    # print(keys)
    socketio.emit('indicator_update', keys)

def frameIsReady():
    socketio.emit('frame_ready', "frame ready")

def update_net_status():
     while True:
        # print("net status: ", net.readWeight())
        if net.isOnTensionMode():
            socketio.emit('tension_update', net.readTenstion())
            socketio.sleep(.025)
        else:
            socketio.emit('weight_update', net.readWeight())
            socketio.sleep(.5)

############################################ SocketIO Handlers ############################################

@socketio.event
def calibrate_load_cell(data):
    net.isCalibrating = True
    step = data['step']
    args = data['args'] 

    # print values
    print("calibrate load cell step: ", step , " args: ", args)

    print("calibrate load cell")
    net.remote_calibration(step, args)
    emit('calibration_step_commited', "step commited")

@socketio.event
def resume_net_update():
    net.isCalibrating = False

@socketio.event
def tare():
    net.setTare()

@socketio.event
def enter_to_tension_test(data):
    print("enter to tension test")
    net.enterToTensionTest()
    print(net.isOnTensionMode())

@socketio.event
def enter_to_weight_mode(data):
    net.enterToWeightMode()

# @socketio.event
# def update_indicator_status(data):
#     # print(data)
#     emit('indicator_update', keyboard.get_keys())

@socketio.event
def get_analysis_data(data):
    emit('analysis_data', imageProcess.get_analysis_data())

@socketio.event
def capture(data):
    print("capturing")
    imageProcess.handle_capture(frameIsReady)

@socketio.event
def reset(data):
    print("reseting")
    imageProcess.handle_reset()

@socketio.event
def reset_defects(data):
    print("reseting defects")
    keyboard.reset_keys()

@socketio.event
def laser(data):
    print("laser")
    ios.laser()

@socketio.on('connect')
def connect(auth):
    # print('Client connected')
    # keyboard.set_callback(update_status)
    global net_thread
    with thread_lock:
        if net_thread is None:
            # keyboard_thread = socketio.start_background_task(keyboard.async_key_check)
            net_thread = socketio.start_background_task(update_net_status)
            
    # emit('indicator_update', keyboard.get_keys())

@socketio.on('disconnect')
def disconnect():
    print('Client disconnected')


############################################## Route Handlers ##############################################

def video_stream():
    while True:
        frame = imageProcess.updateImage()
        ret, buffer = cv2.imencode('.jpeg',frame)
        yield (b' --frame\r\n' b'Content-type: imgae/jpeg\r\n\r\n' + buffer.tobytes() +b'\r\n')

def analyzed_image():
    frame = imageProcess.getAnalyzedImage()
    ret, buffer = cv2.imencode('.jpeg',frame)
    socketio.emit('analysis_data', imageProcess.get_analysis_data())
    yield (b' --frame\r\n' b'Content-type: imgae/jpeg\r\n\r\n' + buffer.tobytes() +b'\r\n')


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
# @app.route("/")
def index(path):
    global async_mode

    return render_template("index.html", async_mode=socketio.async_mode)

# @app.route("/capture")
# def capture():
#     imageProcess.handle_capture()
#     return "captured"

# @app.route("/reset")
# def reset():
#     imageProcess.handle_reset()
#     return "reset"

@app.route('/video_feed')
def video_feed():
    return Response(video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/analyzed_image')
def getAnalyzedImage():
    return Response(analyzed_image(), mimetype='multipart/x-mixed-replace; boundary=frame')

################################################# Main #####################################################

socketio.run(app, host='0.0.0.0', port='3030')

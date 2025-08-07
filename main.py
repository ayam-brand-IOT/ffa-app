DEV_MODE = False

if DEV_MODE:
    import TLB_MODBUS_dev as net
else:
    import TLB_MODBUS as net

import cv2
import json
import time
import IOs as ios
import imageProcess
from threading import Lock
from flask_cors import CORS
from flask_socketio import SocketIO, send, emit
from flask import Flask, render_template, Response, request, stream_with_context

async_mode = None

app = Flask(__name__,
            static_folder="./dist/static",
            template_folder="./dist")
app.config['SECRET_KEY'] = 'secret!'
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
net_thread = None
thread_lock = Lock()

######################################## Callbacks ########################################

def update_status(keys):
    socketio.emit('indicator_update', keys)

def frameIsReady():
    socketio.emit('frame_ready', "frame ready")

def update_net_status():
    while True:
        if net.isOnTensionMode():
            socketio.emit('tension_update', net.readTenstion())
            socketio.sleep(0.025)
        else:
            socketio.emit('weight_update', net.readWeight())
            socketio.sleep(0.5)

######################################## SocketIO Handlers ########################################

@socketio.event
def calibrate_load_cell(data):
    net.isCalibrating = True
    step = data['step']
    args = data['args']
    print("calibrate load cell step:", step, " args:", args)
    net.remote_calibration(step, args)
    emit('calibration_step_commited', "step commited")

@socketio.event
def resume_net_update():
    net.isCalibrating = False

@socketio.event
def enter_to_tension_test(data):
    print("enter to tension test")

@socketio.event
def enter_to_weight_mode(data):
    net.enterToWeightMode()

@socketio.event
def set_zero(data):
    net.setZero()

@socketio.event
def set_tare(data):
    net.setTare(bool(data))

@socketio.event
def update_net(data):
    print("net update")
    socketio.emit('weight_update', net.readWeight())

@socketio.event
def get_tension(data):
    print("tension update")
    socketio.emit('tension_update', net.readTenstion())

@socketio.event
def get_analysis_data(data):
    emit('analysis_data', imageProcess.get_analysis_data())

@socketio.event
def capture(data):
    ios.timered_flash()
    time.sleep(1)
    print("capturing")
    imageProcess.handle_capture(frameIsReady)

@socketio.event
def reset(data):
    print("reseting")
    imageProcess.handle_reset()

@socketio.event
def reset_defects(data):
    print("reseting defects")

@socketio.event
def laser(data):
    print("laser")

# Handler para actualizar parámetros vía SocketIO
@socketio.event
def set_fish_data(data):
    """
    Recibe mediante SocketIO un objeto con la estructura:
    { "species": "mackerel", "type": "HG" }
    y actualiza los parámetros en imageProcess.
    """
    print("set fish data recibido:", data)
    # Si viene como string, se parsea
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as ex:
            print("Error parseando datos:", ex)
            emit("fishParamsResponse", {"error": "Formato inválido"})
            return
    result = update_fish_params_func(data)
    # emit("fishParamsResponse", result)

@socketio.on('connect')
def connect(auth):
    print("Client connected")
    ios.set_laser(True)
    ios.set_flash(False)

@socketio.on('disconnect')
def disconnect():
    print("Client disconnected")

######################################## Función Común para Actualizar Fish Params ########################################

def update_fish_params_func(data):
    """
    Recibe un diccionario con la selección:
      { "species": "mackerel", "type": "HG" }
    y actualiza los parámetros de procesamiento mediante imageProcess.update_fish_parameters.
    Retorna un diccionario con el resultado.
    """
    species_name = data.get("species")
    type_name = data.get("type")
    print("Solicitud para actualizar parámetros para especie:", species_name, "y tipo:", type_name)
    
    CONFIG_FILE = "./vision_config.json"
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except Exception as e:
        error_msg = f"Error al leer vision_config.json: {e}"
        print(error_msg)
        return {"error": error_msg}
    
    species_list = config.get("species_params", [])
    for species in species_list:
        if species.get("name") == species_name:
            for tipo in species.get("types", []):
                if tipo.get("typeName") == type_name:
                    params = tipo.get("parameters")
                    # Llama a la función en imageProcess para actualizar los parámetros internamente
                    imageProcess.update_fish_parameters(params)
                    print("Parámetros actualizados en imageProcess:", params)
                    return {"status": "ok", "parameters": params}
    return {"error": "Especie o tipo no encontrado"}

######################################## Endpoints HTTP ########################################

def video_stream():
    while True:
        frame = imageProcess.updateImage()
        cv2.line(frame, (200, 0), (200, 1000), (255, 0, 0), 1)
        cv2.line(frame, (0, 330), (1000, 330), (255, 0, 0), 1)
        ret, buffer = cv2.imencode('.jpeg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def analyzed_image():
    frame = imageProcess.getAnalyzedImage()
    ret, buffer = cv2.imencode('.jpeg', frame)
    socketio.emit('analysis_data', imageProcess.get_analysis_data())
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template("index.html", async_mode=socketio.async_mode)

@app.route('/length_calibration', methods=['POST'])
def length_calibration():
    data = request.get_json()
    print("Length calibration data:", data)
    imageProcess.write_px_mm_ratio(data['ratio'])
    return "ok"

@app.route('/calibrate_zoi', methods=['POST'])
def calibrate_zoi():
    data = request.get_json()
    print("Calibrate ZOI data:", data)
    imageProcess.writeZOI(data)
    return "ok"

@app.route('/update_fish_params', methods=['POST'])
def update_fish_params_route():
    """
    Endpoint HTTP para actualizar los parámetros de la especie y tipo seleccionados.
    """
    data = request.get_json()
    result = update_fish_params_func(data)
    if result.get("status") == "ok":
        return json.dumps(result), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps(result), 404, {"Content-Type": "application/json"}

@app.route('/video_feed')
def video_feed():
    return Response(video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/analyzed_image')
def getAnalyzedImage():
    return Response(analyzed_image(), mimetype='multipart/x-mixed-replace; boundary=frame')

######################################## Main ########################################

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port='3030', allow_unsafe_werkzeug=True)

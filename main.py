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
import logging

async_mode = None

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
    transports=['polling'],
)
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
    with thread_lock:
        net.isCalibrating = True
        step = data['step']
        args = data['args']
        print("calibrate load cell step:", step, " args:", args)
        net.remote_calibration(step, args)
    emit('calibration_step_commited', "step commited")

@socketio.event
def resume_net_update():
    with thread_lock:
        net.isCalibrating = False

@socketio.event
def enter_to_tension_test(data):
    with thread_lock:
        print("enter to tension test")

@socketio.event
def enter_to_weight_mode(data):
    with thread_lock:
        net.enterToWeightMode()

@socketio.event
def set_zero(data):
    with thread_lock:
        net.setZero()

@socketio.event
def set_tare(data):
    with thread_lock:
        net.setTare(bool(data))

@socketio.event
def update_net(data):
    print("net update")
    with thread_lock:
        weight = net.readWeight()
    socketio.emit('weight_update', weight)

@socketio.event
def get_tension(data):
    print("tension update")
    with thread_lock:
        tension = net.readTenstion()
    socketio.emit('tension_update', tension)

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
    species_name = data.get("fish_species")
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
        if frame is None:
            time.sleep(0.1)
            continue
        cv2.line(frame, (200, 0), (200, 1000), (0, 0, 255), 1) # blue vertical line
        cv2.line(frame, (0, 330), (1000, 330), (0, 0, 255), 1) # blue horizontal line
        ret, buffer = cv2.imencode('.jpeg', frame)
        if not ret:
            time.sleep(0.1)
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

def analyzed_image():
    frame = imageProcess.getAnalyzedImage()
    if frame is None:
        return
    ret, buffer = cv2.imencode('.jpeg', frame)
    if not ret:
        return
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

@app.route('/update_config', methods=['POST'])
def update_config():
    """
    Endpoint HTTP para modificar los valores de configuración.
    Puede actualizar tailTrigger y/o species_params según name y typeName.
    
    Formato esperado:
    {
        "tailTrigger": 45,  // opcional
        "species_params": {  // opcional
            "name": "MACK",
            "typeName": "HG", 
            "parameters": {
                "A": 15,
                "B": 18,
                "C": 25
            }
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return json.dumps({"error": "No data provided"}), 400, {"Content-Type": "application/json"}
        
        CONFIG_FILE = "./vision_config.json"
        
        # Leer configuración actual
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except Exception as e:
            return json.dumps({"error": f"Error reading config file: {e}"}), 500, {"Content-Type": "application/json"}
        
        updated_fields = []
        
        # Actualizar tailTrigger si está presente
        if "tailTrigger" in data:
            config["tailTrigger"] = data["tailTrigger"]
            updated_fields.append("tailTrigger")
        
        # Actualizar species_params si está presente
        if "species_params" in data:
            species_data = data["species_params"]
            required_fields = ["name", "typeName", "parameters"]
            
            if not all(field in species_data for field in required_fields):
                return json.dumps({
                    "error": "species_params must contain name, typeName, and parameters"
                }), 400, {"Content-Type": "application/json"}
            
            species_name = species_data["name"]
            type_name = species_data["typeName"]
            new_parameters = species_data["parameters"]
            
            # Buscar y actualizar la especie y tipo específicos
            found = False
            species_list = config.get("species_params", [])
            
            for species in species_list:
                if species.get("name") == species_name:
                    for fish_type in species.get("types", []):
                        if fish_type.get("typeName") == type_name:
                            fish_type["parameters"] = new_parameters
                            found = True
                            updated_fields.append(f"species_params.{species_name}.{type_name}")
                            break
                    if found:
                        break
            
            if not found:
                return json.dumps({
                    "error": f"Species '{species_name}' with type '{type_name}' not found"
                }), 404, {"Content-Type": "application/json"}
        
        # Guardar configuración actualizada
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Error writing config file: {e}"}), 500, {"Content-Type": "application/json"}
        
        # Recargar configuración en imageProcess si es necesario
        if "tailTrigger" in updated_fields:
            # El tailTrigger se relee automáticamente cuando se inicializa imageProcess
            print(f"tailTrigger updated to: {config['tailTrigger']}")
        
        return json.dumps({
            "status": "success",
            "message": f"Configuration updated successfully",
            "updated_fields": updated_fields,
            "config": config
        }), 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}), 500, {"Content-Type": "application/json"}

@app.route('/get_config', methods=['GET'])
def get_config():
    """
    Endpoint HTTP para obtener la configuración actual.
    """
    try:
        CONFIG_FILE = "./vision_config.json"
        
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        return json.dumps(config), 200, {"Content-Type": "application/json"}
        
    except Exception as e:
        return json.dumps({"error": f"Error reading config: {str(e)}"}), 500, {"Content-Type": "application/json"}

@app.route('/video_feed')
def video_feed():
    return Response(video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/analyzed_image')
def getAnalyzedImage():
    return Response(analyzed_image(), mimetype='multipart/x-mixed-replace; boundary=frame')

######################################## Main ########################################

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port='3030', allow_unsafe_werkzeug=True)

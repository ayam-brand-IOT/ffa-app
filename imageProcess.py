import cv2
import numpy as np
import math
import json
import time
import os
from threading import Lock, Thread

# Initialize camera lazily to avoid errors when the device is missing. Track
# when the camera is unavailable so we do not spam warnings by retrying on
# every frame.
cap = None
_camera_unavailable = False
_frame_lock = Lock()   # protects _latest_frame (camera thread)
_state_lock = Lock()  # protects captured, captured_data, last_frame, frameReadyCallback
_latest_frame = None
_pending_frame = None  # frame snapshotted at capture time, consumed by run_analysis()
_capture_thread = None

def _open_camera():
    """Try to open the configured camera and return True on success."""
    global cap, _camera_unavailable
    if _camera_unavailable:
        return False
    if cap is not None and cap.isOpened():
        return True
    source = os.environ.get("CAMERA_INDEX", "0")
    # Allow either numeric index or device path
    try:
        source = int(source)
    except ValueError:
        pass
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Warning: cannot open camera {source}")
        cap.release()
        cap = None
        _camera_unavailable = True
        return False
    return True


def _capture_loop():
    """Background thread that continuously grabs frames from the camera."""
    global _latest_frame
    while True:
        if not _open_camera():
            time.sleep(0.5)
            continue
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue
        frame = cv2.resize(frame, (1000, 650))
        with _frame_lock:
            _latest_frame = frame
        time.sleep(0.03)


def get_stream_frame():
    """Return the most recent camera frame, starting the capture thread if needed."""
    global _capture_thread
    if _capture_thread is None or not _capture_thread.is_alive():
        _capture_thread = Thread(target=_capture_loop, daemon=True)
        _capture_thread.start()
    with _frame_lock:
        if _latest_frame is None:
            return None
        return _latest_frame.copy()

__RATIO__ = 16/9
__CAMERA_WIDTH__ = 550
__CAMERA_HEIGTH__ = math.floor(__CAMERA_WIDTH__/__RATIO__)
__FRAMESIZE__ = (1000, 650)
__MAIN_PATH__ ="./muestras/opencv_frame_" # path to save images

__CONFIG_PATH__ = "./vision_config.json"

last_frame = None
captured_data = None
frameReadyCallback = None

coef_calibration = 0.23 #0.19*1.22
zoi_x1 = 40
zoi_y1 = 100
zoi_x2 = 500
zoi_y2 = 500
tailTriggerDiameter : 40 # previously >> Z1 = 40  # Size of the tail we want


captured = False
# pause_image = False
lytho = 1.2  # user threshold 1.2
img_counter = 0
zero_line = 200

# Parámetros de pescado (estos se actualizarán según la selección)
fish_parameters = {
    "BODY_OFFSET":              None, # A : Body Offset : to avoid false measurement of width when ther is a block for HG/T 
    "HEAD_CUT_OFFSET":          None, # B:  Head Cut Offset : the offset between the Laser and the real head cut
    "TAIL_TRIGGER_DIAMETER":    None  # C : Tail Trigger Diameter : the minimum diameter of the fish that determine the tail cut >> when we reach this diameter we stop measuring pixels
}

def loadConfig():
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        global zoi_x1, zoi_y1, zoi_x2, zoi_y2, coef_calibration, tailTriggerDiameter
        zoi_x1, zoi_y1 = math.floor(config['zoi'][0]['x']), math.floor(config['zoi'][0]['y'])
        zoi_x2, zoi_y2 = math.floor(config['zoi'][1]['x']), math.floor(config['zoi'][1]['y'])
        coef_calibration = config['ppmm']
        # tailTriggerDiameter = math.floor(config['tailTrigger'])
    except Exception as e:
        print(f"Error al cargar la configuración: {e}")
    

loadConfig()

# Función para actualizar los parámetros de pescado.
def update_fish_parameters(params):
    """
    Actualiza la variable global fish_parameters con los valores nuevos.
    Además, persiste estos valores en vision_config.json bajo la clave "current_fish_params"
    si se desea (opcional).
    """
    global fish_parameters
    fish_parameters = params
    print("Fish parameters updated:", fish_parameters)
    # (Opcional) Actualizar el archivo de configuración:
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
    except Exception as e:
        print("Error al leer vision_config.json:", e)
        config = {}
    # Puedes elegir guardar estos parámetros en una nueva clave para referencia,
    # por ejemplo, "current_fish_params"
    config["current_fish_params"] = params
    try:
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print("Error al escribir los fish parameters en vision_config.json:", e)

# captured = False
# # pause_image = False
# ZOI_start = [zoi_x1, zoi_y1]
# ZOI_end = [zoi_x2, zoi_y2]
# lytho = 1.2  # user threshold 1.2
# img_counter = 0
# zero_line = 200

def write_px_mm_ratio(ratio):
    global coef_calibration
    coef_calibration = ratio
    print("set ratio: ", ratio)
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        config['ppmm'] = ratio
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print(f"Error writting px/mm: {e}")

def writeZOI(points):
    global zoi_x1, zoi_y1, zoi_x2, zoi_y2
    zoi_x1, zoi_y1 = math.floor(points[0]['x']), math.floor(points[0]['y'])
    zoi_x2, zoi_y2 = math.floor(points[1]['x']), math.floor(points[1]['y'])
    print("set zoi: ", points)
    try:
        with open(__CONFIG_PATH__, 'r') as archivo:
            config = json.load(archivo)
        config['zoi'] = points
        with open(__CONFIG_PATH__, 'w') as archivo:
            json.dump(config, archivo, indent=4)
    except Exception as e:
        print(f"Error writting ZOI: {e}")

def handle_capture(callback):
    """Snapshot the current frame and store callback. Analysis is triggered
    separately via run_analysis() in a real OS thread."""
    global _pending_frame, frameReadyCallback
    print("capture")
    with _state_lock:
        frameReadyCallback = callback
        _pending_frame = get_stream_frame()  # snapshot BEFORE returning to caller

def getAnalyzedImage():
    with _state_lock:
        return last_frame
    
def get_analysis_data():
    with _state_lock:
        return captured_data

def handle_reset():
    global captured, captured_data
    with _state_lock:
        captured = False
        captured_data = None
    print("reset")

def run_analysis():
    """Full OpenCV analysis pipeline. MUST be called via eventlet.tpool.execute()
    so it runs in a real OS thread and does not block the eventlet IO loop
    during CPU-intensive processing.
    """
    global img_counter, last_frame, captured_data
    with _state_lock:
        frame = _pending_frame
        _callback = frameReadyCallback
    if frame is None:
        print("run_analysis: no pending frame, skipping")
        return

    print("Capturing image")

    # Early dimension validation
    height, width = frame.shape[:2]
    if zero_line >= width or zoi_x2 > width or zoi_y2 > height:
        print(f"ERROR: Dimensiones inválidas - frame: {width}x{height}, zoi_x2: {zoi_x2}, zero_line: {zero_line}")
        return

    # Save raw frame in a background thread so we don't wait on disk IO
    img_name = __MAIN_PATH__ + "{}.png".format(img_counter)
    Thread(target=lambda: cv2.imwrite(img_name, frame), daemon=True).start()
    print("{} saving in background...".format(img_name))

    im = frame.copy()
    img_counter += 1
        
    body_offset_value = 0.0
    head_cut_offset_value = 0.0
    tail_trigger_diameter_value = 0.0
    if fish_parameters:

        raw_BO = fish_parameters.get("BODY_OFFSET")
        if raw_BO is not None:
            try:
                body_offset_value = float(raw_BO)
            except (TypeError, ValueError):
                body_offset_value = 0.0

        raw_HC = fish_parameters.get("HEAD_CUT_OFFSET")
        if raw_HC is not None:
            try:
                head_cut_offset_value = float(raw_HC)
            except (TypeError, ValueError):
                head_cut_offset_value = 0.0

        raw_TD = fish_parameters.get("TAIL_TRIGGER_DIAMETER")
        if raw_TD is not None:
            try:
                tail_trigger_diameter_value = float(raw_TD)
            except (TypeError, ValueError):
                tail_trigger_diameter_value = 0.0

    img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(img, (5, 5), 0)
    ret3, th3 = cv2.threshold(blur, 0, 1, cv2.THRESH_OTSU)
    ret4, BW = cv2.threshold(blur, ret3 * lytho, 1, cv2.THRESH_BINARY)

    height, width = BW.shape
    print(f"Dimensiones de BW: {BW.shape}")

    if coef_calibration > 0:
        Body_Offset = int(round(body_offset_value / coef_calibration))
        Head_Cut_Offset = int(round(head_cut_offset_value / coef_calibration))
        Tail_Trigger_Diameter = int(round(tail_trigger_diameter_value / coef_calibration))
    else:
        Body_Offset = int(round(body_offset_value))
        Head_Cut_Offset = int(round(head_cut_offset_value))
        Tail_Trigger_Diameter = int(round(tail_trigger_diameter_value))

    max_offset = max(0, width - zero_line)
    Body_Offset = np.clip(Body_Offset, 0, max_offset)
    Head_Cut_Offset = np.clip(Head_Cut_Offset, 0, max_offset)
    Tail_Trigger_Diameter = np.clip(Tail_Trigger_Diameter, 0, max_offset)
    print(f"Offsets (px) -> A: {Body_Offset}, B: {Head_Cut_Offset}, C: {Tail_Trigger_Diameter}")

    if zero_line >= zoi_x2:
        print(f"Ajustando zero_line de {zero_line} a {zoi_x1}")
        zero_line = zoi_x1

    zoi_y1_clipped = max(0, min(zoi_y1, height))
    zoi_y2_clipped = max(0, min(zoi_y2, height))
    zero_line_clipped = max(0, min(zero_line + Body_Offset + Head_Cut_Offset, width))
    zoi_x2_clipped = max(0, min(zoi_x2, width))

    ROIBW = BW[zoi_y1_clipped:zoi_y2_clipped, zero_line_clipped:zoi_x2_clipped]

    if ROIBW.size == 0 or ROIBW.shape[1] == 0:
        print("ROIBW tiene dimensiones inválidas.")
        return

    print(f"ROIBW shape: {ROIBW.shape}")

    cv2.line(im, (zero_line, 0), (zero_line, 1000), (0, 0, 255), 1)
    cv2.line(im, (0, 330), (1000, 330), (0, 0, 255), 1)
    cv2.rectangle(im, (zoi_x1, zoi_y1), (zoi_x2, zoi_y2), (0, 255, 0), 1)
    cv2.rectangle(im, (zero_line_clipped, zoi_y1_clipped), (zoi_x2_clipped, zoi_y2_clipped), (0, 0, 255), 1)
    cv2.putText(im, "Zone Of Interest", (zoi_x2-150, zoi_y2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 0), 1)
    cv2.line(im, (zero_line + Head_Cut_Offset, zoi_y1), (zero_line + Head_Cut_Offset, zoi_y2), (0, 165, 255), 1)
    cv2.line(im, (zero_line + Body_Offset + Head_Cut_Offset, zoi_y1), (zero_line + Body_Offset + Head_Cut_Offset, zoi_y2), (200, 200, 200), 1)

    diameter = np.sum(1 - ROIBW, axis=0).tolist()

    tail_indices = np.where(np.array(diameter) <= Tail_Trigger_Diameter)[0]
    j = tail_indices[0] if len(tail_indices) > 0 else len(diameter) - 1

    if len(diameter) == 0:
        print("La lista 'diameter' está vacía.")
        return

    bodyLength = j + Body_Offset
    bodyLength_start_x = zero_line + Head_Cut_Offset
    bodyLength_end_x = zero_line + bodyLength + Head_Cut_Offset
    body_color = (138, 43, 226)
    bodyLength_mm = bodyLength * coef_calibration

    cv2.line(im, (bodyLength_end_x, zoi_y1), (bodyLength_end_x, zoi_y2), (255, 0, 0), 1)
    cv2.arrowedLine(im, (bodyLength_start_x, zoi_y1+20), (bodyLength_end_x, zoi_y1+20), (0, 0, 255), 2, 1, 0, 0.03)
    cv2.arrowedLine(im, (bodyLength_end_x, zoi_y1+20), (bodyLength_start_x, zoi_y1+20), (0, 0, 255), 2, 1, 0, 0.03)
    cv2.putText(im, "bodyLength : " + str(round(bodyLength_mm, 1)) + " mm", (bodyLength+zero_line+20, zoi_y1+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(im, "Head Cut offset : " + str(round(head_cut_offset_value, 1)) + " mm", (bodyLength+zero_line+20, zoi_y1+90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
    cv2.putText(im, "Body offset : " + str(round(body_offset_value, 1)) + " mm", (bodyLength+zero_line+20, zoi_y1+130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(im, "bodyLength_body : " + str(round(bodyLength_mm, 1)) + " mm", (bodyLength+zero_line+20, zoi_y1+170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, body_color, 2)

    bodySurface = np.sum(1 - ROIBW[:, 1:bodyLength])
    print('Black area is: ' + str(bodySurface))

    bodyDiameter = np.max(diameter[:j+1]) if j > 0 else 0
    bodyDiameterindex = int(np.argmax(diameter[:j+1])) if j > 0 else 0
    c = (1 - ROIBW[:, bodyDiameterindex])

    for i in range(len(c)):
        if c[i] == 1:
            cv2.circle(im, (zero_line + bodyDiameterindex + Head_Cut_Offset + Body_Offset, i+zoi_y1), 1, (200, 0, 255), 1)

    print('bodyDiameter is: ' + str(bodyDiameter))
    cv2.putText(im, "bodyDiameter : " + str(round(bodyDiameter*coef_calibration, 1)) + " mm", (bodyDiameterindex+zero_line+20, zoi_y1+250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 255), 3)

    zoi_x1_clipped = max(0, min(zoi_x1, width))
    zoi_x2_clipped = max(0, min(zoi_x2, width))
    ROIBW_HEAD = BW[zoi_y1_clipped:zoi_y2_clipped, zoi_x1_clipped:zero_line_clipped]

    if ROIBW_HEAD.size == 0 or ROIBW_HEAD.shape[1] == 0:
        print("ROIBW_HEAD tiene dimensiones inválidas.")
        return

    head_diameter = np.sum(1 - ROIBW_HEAD, axis=0)
    head_indices = np.where(head_diameter > 2)[0]
    if len(head_indices) > 0:
        j = head_indices[0]
        headLength = zero_line - j - zoi_x1
    else:
        headLength = 0
    print('headLength is: ' + str(headLength))

    cv2.line(im, (zero_line - headLength, zoi_y1), (zero_line - headLength, zoi_y2), (255, 0, 0), 1)
    cv2.arrowedLine(im, (zero_line + Head_Cut_Offset, zoi_y2), (zero_line - headLength, zoi_y2), (0, 0, 255), 2, 1, 0, 0.04)
    cv2.arrowedLine(im, (zero_line - headLength, zoi_y2), (zero_line + Head_Cut_Offset, zoi_y2), (0, 0, 255), 2, 1, 0, 0.04)
    cv2.putText(im, "headLength : " + str(abs(round(headLength*coef_calibration, 1))) + " mm", (headLength+zero_line+20, zoi_y2+40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    _new_data = json.dumps({
        "length": round(bodyLength_mm, 1),
        "height": round(bodyDiameter * coef_calibration, 1),
        "head": abs(round(headLength * coef_calibration, 1)),
        "tail_trigger": round(Tail_Trigger_Diameter * coef_calibration, 1)
    })

    with _state_lock:
        last_frame = im
        captured_data = _new_data
    # Call callback OUTSIDE the lock to avoid deadlocks
    if _callback:
        _callback()


def updateImage():
    """Lightweight: returns the latest camera frame for the live video stream.
    Analysis is done separately in run_analysis() via a real OS thread.
    """
    return get_stream_frame()

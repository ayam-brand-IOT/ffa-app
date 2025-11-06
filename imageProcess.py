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
_frame_lock = Lock()
_latest_frame = None
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
    global captured, frameReadyCallback
    print("capture")
    frameReadyCallback = callback
    captured = True

def getAnalyzedImage():
    return last_frame
    
def get_analysis_data():
    global captured_data
    return captured_data

def handle_reset():
    global captured, captured_data
    captured = False
    # pause_image = False
    captured_data = None
    print("reset")

def updateImage():
    global captured, img_counter, last_frame, zoi_x1, captured_data, frameReadyCallback, zero_line
    frame = get_stream_frame()
    if frame is None:
        return None
    if captured:
        print("Capturing image")

        img_name = __MAIN_PATH__ + "{}.png".format(img_counter)
        cv2.imwrite(img_name, frame)
        print("{} written!".format(img_name))

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
        blur = cv2.GaussianBlur(img, (13, 13), 0)
        ret3, th3 = cv2.threshold(blur, 0, 1, cv2.THRESH_OTSU)
        ret4, BW = cv2.threshold(blur, ret3 * lytho, 1, cv2.THRESH_BINARY)

        # Verificar dimensiones de la imagen
        height, width = BW.shape
        print(f"Dimensiones de BW: {BW.shape}")

        # Convert the user-provided A, B, and C lengths (mm) into pixel offsets.
        if coef_calibration > 0:
            Body_Offset = int(round(body_offset_value / coef_calibration))
            Head_Cut_Offset = int(round(head_cut_offset_value / coef_calibration))
            Tail_Trigger_Diameter = int(round(tail_trigger_diameter_value / coef_calibration))
        else:
            Body_Offset = int(round(body_offset_value))
            Head_Cut_Offset = int(round(head_cut_offset_value))
            Tail_Trigger_Diameter = int(round(tail_trigger_diameter_value))

        max_offset = max(0, width - zero_line)
        Body_Offset = max(0, min(Body_Offset, max_offset))
        Head_Cut_Offset = max(0, min(Head_Cut_Offset, max_offset))
        Tail_Trigger_Diameter = max(0, min(Tail_Trigger_Diameter, max_offset))
        print(f"Offsets (px) -> A: {Body_Offset}, B: {Head_Cut_Offset}, C: {Tail_Trigger_Diameter}")

        # Asegurarse de que zero_line < zoi_x2
        if zero_line >= zoi_x2:
            print(f"Ajustando zero_line de {zero_line} a {zoi_x1}")
            zero_line = zoi_x1

        # Clipping de índices para estar dentro de los límites de la imagen
        zoi_y1_clipped = max(0, min(zoi_y1, height))
        zoi_y2_clipped = max(0, min(zoi_y2, height))
        zero_line_clipped = max(0, min(zero_line+Body_Offset + Head_Cut_Offset, width))
        zoi_x2_clipped = max(0, min(zoi_x2, width))

        # Definir la Zona de Interés (ZOI)
        ROIBW = BW[zoi_y1_clipped:zoi_y2_clipped, zero_line_clipped:zoi_x2_clipped]

        # Verificar si ROIBW tiene dimensiones válidas
        if ROIBW.size == 0 or ROIBW.shape[1] == 0:
            print("ROIBW tiene dimensiones inválidas. Verifique los valores de zoi_y1, zoi_y2, zero_line y zoi_x2.")
            return

        print(f"ROIBW shape: {ROIBW.shape}")
        
        
        cv2.line(im, (zero_line, 0), (zero_line, 1000), (0, 0, 255), 1) # red vertical line of the laser
        cv2.line(im, (0, 330), (1000, 330), (0, 0, 255), 1) # red horizontal line of the laser

        cv2.rectangle(im, (zoi_x1, zoi_y1), (zoi_x2, zoi_y2), (0, 255, 0), 1)
        cv2.rectangle(im, (zero_line_clipped, zoi_y1_clipped), (zoi_x2_clipped, zoi_y2_clipped), (0, 0, 255), 1)
        cv2.putText(im, "Zone Of Interest", (zoi_x2-150, zoi_y2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,150,0), 1)
        # cv2.line(im, (zero_line, zoi_y1), (zero_line, zoi_y2), (0,0,255), 1) # red vertical line >> line of the zero
        cv2.line(im, (zero_line + Head_Cut_Offset, zoi_y1), (zero_line + Head_Cut_Offset, zoi_y2), (0,165,255), 1) # orange vertical >> head cut line
        cv2.line(im, (zero_line + Body_Offset + Head_Cut_Offset, zoi_y1), (zero_line + Body_Offset + Head_Cut_Offset, zoi_y2), (200,200,200), 1) # grey vertical line >> of the body offset

        # Size of the fish from zero line to tail
        diameter = []
        for j in range(ROIBW.shape[1]): # shape[0] = on the height (y-axis) and shape[1] on the width (x-axis)
            w = np.sum(1 - ROIBW[:, j]) # sum all the '0' pixel on the Y (ROIBW[x,y])
            diameter.append(w)          # the tab diameter have all the diameter of the fish for each x0...xn
            if w <= Tail_Trigger_Diameter:                 # stop the loop when the size of the diameter of the tail is reached
                print(w)
                break

        # Verificar que la lista 'diameter' no esté vacía
        if len(diameter) == 0:
            print("La lista 'diameter' está vacía, no se puede calcular el máximo. Verifique los valores de ROIBW.")
            return

        bodyLength = j + Body_Offset
        
        bodyLength_start_x = zero_line + Head_Cut_Offset
        bodyLength_end_x = zero_line + bodyLength + Head_Cut_Offset
        body_color = (138, 43, 226)
        bodyLength_mm = bodyLength * coef_calibration
        
        # Display Line bodyLength
        cv2.line(im, (bodyLength_end_x, zoi_y1), (bodyLength_end_x, zoi_y2), (255,0,0), 1) # Blue Line to show the end of the fish
        cv2.arrowedLine(im, (bodyLength_start_x, zoi_y1+20), (bodyLength_end_x, zoi_y1+20), (0,0,255), 2, 1, 0, 0.03)
        cv2.arrowedLine(im, (bodyLength_end_x, zoi_y1+20), (bodyLength_start_x, zoi_y1+20), (0,0,255), 2, 1, 0, 0.03)
        cv2.putText(im, "bodyLength : " + str(round(bodyLength_mm,1)) + " mm", (bodyLength+zero_line+20, zoi_y1+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)


        cv2.putText(im, "Head Cut offset : " + str(round(head_cut_offset_value,1)) + " mm", (bodyLength+zero_line+20, zoi_y1+90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,165,0), 2)
        cv2.putText(im, "Body offset : " + str(round(body_offset_value,1)) + " mm", (bodyLength+zero_line+20, zoi_y1+130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        cv2.putText(im, "bodyLength_body : " + str(round(bodyLength_mm,1)) + " mm", (bodyLength+zero_line+20, zoi_y1+170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, body_color, 2)

        # Calcular el área negra
        bodySurface = np.sum(np.sum(1 - ROIBW[:, 1:bodyLength]))
        print('Black area is: ' + str(bodySurface))

        # Calcular el diámetro máximo
        bodyDiameter = np.max(diameter)
        bodyDiameterindex = diameter.index(bodyDiameter)
        c = (1 - ROIBW[:, bodyDiameterindex])

        for i in range(len(c)):
            if c[i] == 1:
                cv2.circle(im, (zero_line + bodyDiameterindex + Head_Cut_Offset + Body_Offset, i+zoi_y1), 1, (200, 0, 255), 1)

        print('bodyDiameter is: ' + str(bodyDiameter))

        cv2.putText(im, "bodyDiameter : " + str(round(bodyDiameter*coef_calibration,1)) + " mm", (bodyDiameterindex+zero_line+20, zoi_y1+250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200,0,255), 3)

        # Ajuste de índices para la cabeza
        zoi_x1_clipped = max(0, min(zoi_x1, width))
        zoi_x2_clipped = max(0, min(zoi_x2, width))
        ROIBW_HEAD = BW[zoi_y1_clipped:zoi_y2_clipped, zoi_x1_clipped:zero_line_clipped]

        # Verificar si ROIBW_HEAD tiene dimensiones válidas
        if ROIBW_HEAD.size == 0 or ROIBW_HEAD.shape[1] == 0:
            print("ROIBW_HEAD tiene dimensiones inválidas. Verifique los valores de zoi_x1 y zero_line.")
            return

        # Calcular el tamaño de la cabeza
        for j in range(ROIBW_HEAD.shape[1]):
            w2 = np.sum(1 - ROIBW_HEAD[:, j])
            if w2 > 2:
                break
        headLength = zero_line - j - zoi_x1
        print('headLength is: ' + str(headLength))

        cv2.line(im, (zero_line - headLength, zoi_y1), (zero_line - headLength, zoi_y2), (255,0,0), 1)
        cv2.arrowedLine(im, (zero_line + Head_Cut_Offset, zoi_y2), (zero_line - headLength, zoi_y2), (0,0,255), 2, 1, 0, 0.04)
        cv2.arrowedLine(im, (zero_line - headLength, zoi_y2), (zero_line + Head_Cut_Offset, zoi_y2), (0,0,255), 2, 1, 0, 0.04)
        cv2.putText(im, "headLength : " + str(abs(round(headLength*coef_calibration,1))) + " mm", (headLength+zero_line+20, zoi_y2+40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)

        last_frame = im
        
        captured_data = '{ "length": '+str(round(bodyLength_mm,1))+', "height": '+str(round(bodyDiameter*coef_calibration,1))+', "head": '+str(abs(round(headLength*coef_calibration,1)))+', "tail_trigger": '+str(round(Tail_Trigger_Diameter*coef_calibration,1))+' }'

        captured = False
        frameReadyCallback()
        return frame

    else:
        return frame

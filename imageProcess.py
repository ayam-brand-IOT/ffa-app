import cv2
import numpy as np
import math
import json
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from logger import logEvent
from services.config_store import read_config, update_config as update_config_store

# Use native (unpatched) threading locks so they work correctly from both
# eventlet greenlets AND real OS threads (eventlet.tpool). After
# eventlet.monkey_patch() runs, threading.Lock() becomes an eventlet lock
# which cannot be safely acquired from a tpool OS thread.
import eventlet.patcher as _patcher
_native_threading = _patcher.original('threading')
_native_time = _patcher.original('time')

CAMERA_RETRY_INITIAL = float(os.getenv("CAMERA_RETRY_INITIAL", "0.5"))
CAMERA_RETRY_MAX = float(os.getenv("CAMERA_RETRY_MAX", "10.0"))
CAMERA_READ_FAILURE_LIMIT = int(os.getenv("CAMERA_READ_FAILURE_LIMIT", "3"))

# Initialize camera lazily to avoid errors when the device is missing. Track
# when the camera is unavailable so we do not spam warnings by retrying on
# every frame.
cap = None
_camera_unavailable = False
_frame_lock = _native_threading.Lock()   # protects _latest_frame (camera thread)
_state_lock = _native_threading.Lock()  # protects captured, captured_data, last_frame, frameReadyCallback
_analysis_lock = _native_threading.Lock()  # serializes access to shared vision state
_latest_frame = None
_latest_frame_seq = 0
_latest_frame_time = 0.0
_pending_frame = None  # frame snapshotted at capture time, consumed by run_analysis()
_capture_thread = None
_camera_retry_delay = CAMERA_RETRY_INITIAL
_camera_next_retry_at = 0.0
_camera_read_failures = 0
_camera_failure_reported = False


def _mark_camera_unavailable(reason):
    """Release the device and schedule a bounded reconnect attempt."""
    global cap, _camera_unavailable, _camera_retry_delay, _camera_next_retry_at
    global _camera_failure_reported

    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass
    cap = None
    _camera_unavailable = True
    _camera_next_retry_at = _native_time.monotonic() + _camera_retry_delay
    _camera_retry_delay = min(
        CAMERA_RETRY_MAX,
        max(CAMERA_RETRY_INITIAL, _camera_retry_delay * 2),
    )

    if not _camera_failure_reported:
        logEvent(
            etapa="SYSTEM",
            status="ERROR",
            error_code="CAMERA_NOT_FOUND",
            error_msg=reason,
            additional_data={"action": "camera_reconnect_scheduled"},
        )
        _camera_failure_reported = True

def _open_camera():
    """Try to open the configured camera and return True on success."""
    global cap, _camera_unavailable, _camera_retry_delay, _camera_next_retry_at
    global _camera_read_failures, _camera_failure_reported

    if cap is not None and cap.isOpened():
        return True
    if _native_time.monotonic() < _camera_next_retry_at:
        return False

    source = os.environ.get("CAMERA_INDEX", "0")
    # Allow either numeric index or device path
    try:
        source = int(source)
    except ValueError:
        pass

    try:
        candidate = cv2.VideoCapture(source)
    except Exception as exc:  # noqa: BLE001 - OpenCV backend errors vary
        _mark_camera_unavailable("No se pudo abrir la camara {0}: {1}".format(source, exc))
        return False
    if not candidate.isOpened():
        try:
            candidate.release()
        except Exception:
            pass
        _mark_camera_unavailable("No se pudo abrir la camara {0}".format(source))
        return False

    cap = candidate
    recovered = _camera_failure_reported
    _camera_unavailable = False
    _camera_retry_delay = CAMERA_RETRY_INITIAL
    _camera_next_retry_at = 0.0
    _camera_read_failures = 0
    _camera_failure_reported = False
    if recovered:
        logEvent(
            etapa="SYSTEM",
            status="SUCCESS",
            additional_data={"action": "camera_reconnected", "source": str(source)},
        )
    return True


def _capture_loop():
    """Background thread that continuously grabs frames from the camera."""
    global _latest_frame, _latest_frame_seq, _latest_frame_time
    global _camera_read_failures

    while True:
        if not _open_camera():
            _native_time.sleep(0.1)
            continue
        try:
            ret, frame = cap.read()
        except Exception as exc:  # noqa: BLE001 - backend may raise C++ errors
            _mark_camera_unavailable(
                "Error leyendo frames de la camara: {0}".format(exc)
            )
            _native_time.sleep(0.05)
            continue
        if not ret:
            _camera_read_failures += 1
            if _camera_read_failures >= CAMERA_READ_FAILURE_LIMIT:
                _camera_read_failures = 0
                _mark_camera_unavailable("La camara dejo de entregar frames")
            _native_time.sleep(0.05)
            continue
        _camera_read_failures = 0
        try:
            frame = cv2.resize(frame, (1000, 650))
        except Exception as exc:  # noqa: BLE001 - malformed backend frame
            _mark_camera_unavailable(
                "La camara entrego un frame invalido: {0}".format(exc)
            )
            continue
        with _frame_lock:
            _latest_frame = frame
            _latest_frame_seq += 1
            _latest_frame_time = _native_time.monotonic()
        _native_time.sleep(0.03)


def get_stream_frame():
    """Return the most recent camera frame, starting the capture thread if needed."""
    global _capture_thread
    if _capture_thread is None or not _capture_thread.is_alive():
        _capture_thread = _native_threading.Thread(target=_capture_loop, daemon=True)
        _capture_thread.start()
    with _frame_lock:
        if _latest_frame is None:
            return None
        return _latest_frame.copy()


def get_frame_marker():
    """Return the latest frame sequence/time.

    Capture synchronization uses this marker before turning the flash on, then
    waits for one or more newer camera frames instead of sleeping a fixed time.
    """
    get_stream_frame()
    with _frame_lock:
        return {
            "seq": _latest_frame_seq,
            "time": _latest_frame_time,
            "has_frame": _latest_frame is not None,
        }


def wait_for_frame_since(seq, skip_frames=1, timeout=0.35):
    """Wait for a fresh frame captured after `seq`.

    Args:
        seq: Frame sequence observed before the external trigger.
        skip_frames: Number of new frames to wait for after the trigger. Some
            cameras need one extra frame for exposure/illumination to settle.
        timeout: Maximum wait in seconds before falling back to the latest frame.

    Returns:
        A copy of the fresh frame, or the latest available frame on timeout.
    """
    target_seq = seq + max(1, int(skip_frames))
    deadline = time.monotonic() + timeout
    get_stream_frame()

    while time.monotonic() < deadline:
        with _frame_lock:
            if _latest_frame is not None and _latest_frame_seq >= target_seq:
                return _latest_frame.copy()
        time.sleep(0.005)

    return get_stream_frame()

__RATIO__ = 16/9
__CAMERA_WIDTH__ = 550
__CAMERA_HEIGTH__ = math.floor(__CAMERA_WIDTH__/__RATIO__)
__FRAMESIZE__ = (1000, 650)
SAMPLE_IMAGES_PATH = Path(
    os.getenv("SAMPLE_IMAGES_PATH", Path(__file__).resolve().parent / "muestras")
).resolve()
SAMPLE_IMAGES_PATH.mkdir(parents=True, exist_ok=True)

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
zero_line = 200

# Parámetros de pescado (estos se actualizarán según la selección)
fish_parameters = {
    "BODY_OFFSET":              None, # A : Body Offset : to avoid false measurement of width when ther is a block for HG/T 
    "HEAD_CUT_OFFSET":          None, # B:  Head Cut Offset : the offset between the Laser and the real head cut
    "TAIL_TRIGGER_DIAMETER":    None  # C : Tail Trigger Diameter : the minimum diameter of the fish that determine the tail cut >> when we reach this diameter we stop measuring pixels
}

def loadConfig():
    """Load valid vision settings or stop startup instead of measuring with defaults."""
    config = read_config()
    try:
        points = config["zoi"]
        if not isinstance(points, list) or len(points) != 2:
            raise ValueError("zoi must contain exactly two points")
        if any(
            isinstance(point.get(axis), bool)
            for point in points
            if isinstance(point, dict)
            for axis in ("x", "y")
        ):
            raise ValueError("zoi coordinates must be numeric")
        x1, y1 = math.floor(float(points[0]["x"])), math.floor(float(points[0]["y"]))
        x2, y2 = math.floor(float(points[1]["x"])), math.floor(float(points[1]["y"]))
        if isinstance(config["ppmm"], bool):
            raise ValueError("ppmm must be numeric")
        ratio = float(config["ppmm"])
        if not math.isfinite(ratio) or not 0.001 <= ratio <= 10:
            raise ValueError("ppmm must be between 0.001 and 10")
        if min(x1, y1) < 0 or x2 <= x1 or y2 <= y1:
            raise ValueError("zoi coordinates are invalid")
        if x2 > __FRAMESIZE__[0] or y2 > __FRAMESIZE__[1]:
            raise ValueError("zoi exceeds capture dimensions")
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise RuntimeError("Configuracion de vision invalida: {0}".format(exc)) from exc

    global zoi_x1, zoi_y1, zoi_x2, zoi_y2, coef_calibration
    zoi_x1, zoi_y1, zoi_x2, zoi_y2 = x1, y1, x2, y2
    coef_calibration = ratio
    

loadConfig()


def update_fish_parameters(params):
    """Validate, persist and apply the fish parameters.

    The normalized values are written to vision_config.json under
    "current_fish_params" through the atomic config store, then applied to
    the running analysis.
    """
    normalized = validate_fish_parameters(params)
    update_config_store(
        lambda config: config.__setitem__("current_fish_params", normalized)
    )

    global fish_parameters
    fish_parameters = normalized
    print("Fish parameters updated:", fish_parameters)


def get_px_mm_ratio():
    """Return the px/mm ratio currently driving the analysis."""
    return coef_calibration


def write_px_mm_ratio(ratio):
    if isinstance(ratio, bool):
        raise ValueError("La calibracion px/mm debe ser numerica")
    try:
        validated_ratio = float(ratio)
    except (TypeError, ValueError) as exc:
        raise ValueError("La calibracion px/mm debe ser numerica") from exc
    if not math.isfinite(validated_ratio) or not 0.001 <= validated_ratio <= 10:
        raise ValueError("La calibracion px/mm debe estar entre 0.001 y 10")

    update_config_store(lambda config: config.__setitem__("ppmm", validated_ratio))
    global coef_calibration
    coef_calibration = validated_ratio
    print("set ratio:", validated_ratio)


def writeZOI(points):
    if not isinstance(points, list) or len(points) != 2:
        raise ValueError("La ZOI debe contener exactamente dos puntos")
    try:
        if any(
            isinstance(point.get(axis), bool)
            for point in points
            if isinstance(point, dict)
            for axis in ("x", "y")
        ):
            raise ValueError
        x1, y1 = math.floor(float(points[0]["x"])), math.floor(float(points[0]["y"]))
        x2, y2 = math.floor(float(points[1]["x"])), math.floor(float(points[1]["y"]))
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("La ZOI contiene coordenadas invalidas") from exc
    if min(x1, y1) < 0 or x2 <= x1 or y2 <= y1:
        raise ValueError("La ZOI debe tener un area positiva")
    if x2 > __FRAMESIZE__[0] or y2 > __FRAMESIZE__[1]:
        raise ValueError("La ZOI excede el tamano de captura")

    normalized_points = [{"x": x1, "y": y1}, {"x": x2, "y": y2}]
    update_config_store(lambda config: config.__setitem__("zoi", normalized_points))
    global zoi_x1, zoi_y1, zoi_x2, zoi_y2
    zoi_x1, zoi_y1, zoi_x2, zoi_y2 = x1, y1, x2, y2
    print("set zoi:", normalized_points)


def _save_raw_frame(image_path, frame):
    try:
        if not cv2.imwrite(str(image_path), frame):
            raise RuntimeError("cv2.imwrite returned False")
        logEvent(
            etapa="CAPTURE",
            status="SUCCESS",
            additional_data={"action": "raw_image_saved", "path": str(image_path)},
        )
        return True
    except Exception as exc:  # noqa: BLE001 - OpenCV returns and raises failures
        error_msg = "No se pudo guardar la imagen de muestra {0}: {1}".format(
            image_path, exc
        )
        print(error_msg)
        logEvent(
            etapa="CAPTURE",
            status="ERROR",
            error_code="RAW_IMAGE_SAVE_ERROR",
            error_msg=error_msg,
        )
        return False


def handle_capture(callback, frame=None):
    """Snapshot the current frame and store callback. Analysis is triggered
    separately via run_analysis() in a real OS thread."""
    global _pending_frame, frameReadyCallback
    print("capture")
    with _state_lock:
        frameReadyCallback = callback
        # Snapshot BEFORE returning to caller. When capture is synchronized with
        # flash, the caller can pass the exact fresh frame selected after flash.
        _pending_frame = frame.copy() if frame is not None else get_stream_frame()
        return _pending_frame

def getAnalyzedImage():
    with _state_lock:
        return last_frame
    
def get_analysis_data():
    with _state_lock:
        return captured_data

def handle_reset():
    global captured, captured_data, last_frame, _pending_frame
    with _state_lock:
        captured = False
        captured_data = None
        last_frame = None
        _pending_frame = None
    print("reset")

def validate_fish_parameters(params):
    """Return the three offsets as floats, or raise if any is missing/invalid.

    An explicit 0 is a legitimate setting; a missing or non-numeric value is
    not, and must never be silently coerced to 0.0 -- that would publish a
    measurement computed with offsets the operator never chose.
    """
    if not isinstance(params, dict):
        raise ValueError("No hay parametros de pescado cargados")

    values = {}
    for field in ("BODY_OFFSET", "HEAD_CUT_OFFSET", "TAIL_TRIGGER_DIAMETER"):
        try:
            if isinstance(params[field], bool):
                raise ValueError
            value = float(params[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Falta o es invalido el parametro {0}".format(field)) from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(
                "El parametro {0} debe ser un numero positivo".format(field))
        values[field] = value
    return values


def _run_analysis(frame=None):
    """Full OpenCV analysis pipeline. MUST be called via eventlet.tpool.execute()
    so it runs in a real OS thread and does not block the eventlet IO loop
    during CPU-intensive processing.
    """
    global last_frame, captured_data, _pending_frame
    with _state_lock:
        if frame is None:
            frame = _pending_frame
        _pending_frame = None
        last_frame = None
        captured_data = None
    if frame is None:
        print("run_analysis: no pending frame, skipping")
        return {"ok": False, "reason": "No hay frame pendiente para analizar"}

    print("Capturing image")

    # Early dimension validation
    height, width = frame.shape[:2]
    analysis_zero_line = zero_line if zero_line < zoi_x2 else zoi_x1
    if analysis_zero_line >= width or zoi_x2 > width or zoi_y2 > height:
        print(f"ERROR: Dimensiones inválidas - frame: {width}x{height}, zoi_x2: {zoi_x2}, zero_line: {analysis_zero_line}")
        return {"ok": False, "reason": "Las dimensiones de analisis no son validas"}

    try:
        params = validate_fish_parameters(fish_parameters)
    except ValueError as exc:
        error_msg = "Parametros de pescado invalidos: {0}".format(exc)
        print("ERROR: {0}".format(error_msg))
        logEvent(etapa="ANALISIS", status="ERROR",
                 error_code="FISH_PARAMETERS_INVALID", error_msg=error_msg)
        return {"ok": False, "reason": error_msg}
    body_offset_value = params["BODY_OFFSET"]
    head_cut_offset_value = params["HEAD_CUT_OFFSET"]
    tail_trigger_diameter_value = params["TAIL_TRIGGER_DIAMETER"]

    # Persist the audit image before analysis can be published. Losing this
    # image is a failed capture, not a background warning.
    img_name = SAMPLE_IMAGES_PATH / "opencv_frame_{0}_{1}.png".format(
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"),
        os.urandom(4).hex(),
    )
    if not _save_raw_frame(img_name, frame):
        return {"ok": False, "reason": "No se pudo guardar la imagen de auditoria"}
    print("{} saved".format(img_name))

    im = frame.copy()

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

    max_offset = max(0, width - analysis_zero_line)
    Body_Offset = np.clip(Body_Offset, 0, max_offset)
    Head_Cut_Offset = np.clip(Head_Cut_Offset, 0, max_offset)
    Tail_Trigger_Diameter = np.clip(Tail_Trigger_Diameter, 0, max_offset)
    print(f"Offsets (px) -> A: {Body_Offset}, B: {Head_Cut_Offset}, C: {Tail_Trigger_Diameter}")

    zoi_y1_clipped = max(0, min(zoi_y1, height))
    zoi_y2_clipped = max(0, min(zoi_y2, height))
    zero_line_clipped = max(0, min(analysis_zero_line + Body_Offset + Head_Cut_Offset, width))
    zoi_x2_clipped = max(0, min(zoi_x2, width))

    ROIBW = BW[zoi_y1_clipped:zoi_y2_clipped, zero_line_clipped:zoi_x2_clipped]

    if ROIBW.size == 0 or ROIBW.shape[1] == 0:
        print("ROIBW tiene dimensiones inválidas.")
        return {"ok": False, "reason": "La region del cuerpo no es valida"}

    print(f"ROIBW shape: {ROIBW.shape}")

    cv2.line(im, (analysis_zero_line, 0), (analysis_zero_line, 1000), (0, 0, 255), 1)
    cv2.line(im, (0, 330), (1000, 330), (0, 0, 255), 1)
    cv2.rectangle(im, (zoi_x1, zoi_y1), (zoi_x2, zoi_y2), (0, 255, 0), 1)
    cv2.rectangle(im, (zero_line_clipped, zoi_y1_clipped), (zoi_x2_clipped, zoi_y2_clipped), (0, 0, 255), 1)
    cv2.putText(im, "Zone Of Interest", (zoi_x2-150, zoi_y2+30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 0), 1)
    cv2.line(im, (analysis_zero_line + Head_Cut_Offset, zoi_y1), (analysis_zero_line + Head_Cut_Offset, zoi_y2), (0, 165, 255), 1)
    cv2.line(im, (analysis_zero_line + Body_Offset + Head_Cut_Offset, zoi_y1), (analysis_zero_line + Body_Offset + Head_Cut_Offset, zoi_y2), (200, 200, 200), 1)

    diameter = np.sum(1 - ROIBW, axis=0).tolist()

    tail_indices = np.where(np.array(diameter) <= Tail_Trigger_Diameter)[0]
    j = tail_indices[0] if len(tail_indices) > 0 else len(diameter) - 1

    if len(diameter) == 0:
        print("La lista 'diameter' está vacía.")
        return {"ok": False, "reason": "No se encontro perfil del cuerpo"}

    bodyLength = j + Body_Offset
    bodyLength_start_x = analysis_zero_line + Head_Cut_Offset
    bodyLength_end_x = analysis_zero_line + bodyLength + Head_Cut_Offset
    body_color = (138, 43, 226)
    bodyLength_mm = bodyLength * coef_calibration

    cv2.line(im, (bodyLength_end_x, zoi_y1), (bodyLength_end_x, zoi_y2), (255, 0, 0), 1)
    cv2.arrowedLine(im, (bodyLength_start_x, zoi_y1+20), (bodyLength_end_x, zoi_y1+20), (0, 0, 255), 2, 1, 0, 0.03)
    cv2.arrowedLine(im, (bodyLength_end_x, zoi_y1+20), (bodyLength_start_x, zoi_y1+20), (0, 0, 255), 2, 1, 0, 0.03)
    cv2.putText(im, "bodyLength : " + str(round(bodyLength_mm, 1)) + " mm", (bodyLength+analysis_zero_line+20, zoi_y1+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(im, "Head Cut offset : " + str(round(head_cut_offset_value, 1)) + " mm", (bodyLength+analysis_zero_line+20, zoi_y1+90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
    cv2.putText(im, "Body offset : " + str(round(body_offset_value, 1)) + " mm", (bodyLength+analysis_zero_line+20, zoi_y1+130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(im, "bodyLength_body : " + str(round(bodyLength_mm, 1)) + " mm", (bodyLength+analysis_zero_line+20, zoi_y1+170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, body_color, 2)

    bodySurface = np.sum(1 - ROIBW[:, 1:bodyLength])
    print('Black area is: ' + str(bodySurface))

    bodyDiameter = np.max(diameter[:j+1]) if j > 0 else 0
    bodyDiameterindex = int(np.argmax(diameter[:j+1])) if j > 0 else 0
    c = (1 - ROIBW[:, bodyDiameterindex])

    for i in range(len(c)):
        if c[i] == 1:
            cv2.circle(im, (analysis_zero_line + bodyDiameterindex + Head_Cut_Offset + Body_Offset, i+zoi_y1), 1, (200, 0, 255), 1)

    print('bodyDiameter is: ' + str(bodyDiameter))
    cv2.putText(im, "bodyDiameter : " + str(round(bodyDiameter*coef_calibration, 1)) + " mm", (bodyDiameterindex+analysis_zero_line+20, zoi_y1+250), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 0, 255), 3)

    zoi_x1_clipped = max(0, min(zoi_x1, width))
    zoi_x2_clipped = max(0, min(zoi_x2, width))
    ROIBW_HEAD = BW[zoi_y1_clipped:zoi_y2_clipped, zoi_x1_clipped:zero_line_clipped]

    if ROIBW_HEAD.size == 0 or ROIBW_HEAD.shape[1] == 0:
        print("ROIBW_HEAD tiene dimensiones inválidas.")
        return {"ok": False, "reason": "La region de la cabeza no es valida"}

    head_diameter = np.sum(1 - ROIBW_HEAD, axis=0)
    head_indices = np.where(head_diameter > 2)[0]
    if len(head_indices) > 0:
        j = head_indices[0]
        headLength = analysis_zero_line - j - zoi_x1
    else:
        headLength = 0
    print('headLength is: ' + str(headLength))

    cv2.line(im, (analysis_zero_line - headLength, zoi_y1), (analysis_zero_line - headLength, zoi_y2), (255, 0, 0), 1)
    cv2.arrowedLine(im, (analysis_zero_line + Head_Cut_Offset, zoi_y2), (analysis_zero_line - headLength, zoi_y2), (0, 0, 255), 2, 1, 0, 0.04)
    cv2.arrowedLine(im, (analysis_zero_line - headLength, zoi_y2), (analysis_zero_line + Head_Cut_Offset, zoi_y2), (0, 0, 255), 2, 1, 0, 0.04)
    cv2.putText(im, "headLength : " + str(abs(round(headLength*coef_calibration, 1))) + " mm", (headLength+analysis_zero_line+20, zoi_y2+40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

    _new_data = json.dumps({
        "length": round(bodyLength_mm, 1),
        "height": round(bodyDiameter * coef_calibration, 1),
        "head": abs(round(headLength * coef_calibration, 1)),
        "tail_trigger": round(Tail_Trigger_Diameter * coef_calibration, 1)
    })

    with _state_lock:
        last_frame = im
        captured_data = _new_data

    return {"ok": True, "image_path": str(img_name)}
    # NOTE: do NOT call the frame_ready callback here.
    # run_analysis() executes inside an eventlet.tpool OS thread, so calling
    # socketio.emit() from here would corrupt the eventlet IO loop.
    # The callback is invoked by _run_analysis_in_tpool() in sockets.py,
    # which runs in a greenlet after tpool.execute() returns.


def run_analysis(frame=None):
    """Serialize analysis and bind it to the snapshot selected at capture time."""
    with _analysis_lock:
        return _run_analysis(frame)


def updateImage():
    """Lightweight: returns the latest camera frame for the live video stream.
    Analysis is done separately in run_analysis() via a real OS thread.
    """
    return get_stream_frame()

"""
routes.py
---------
All HTTP routes (Flask blueprints not required at this scale;
routes are registered directly on the shared `app` instance).
"""

import cv2
import json
import eventlet
import imageProcess
from flask import render_template, Response, request

from app import app, socketio
from logger import logEvent
from services.config_service import update_fish_params, update_config, get_config


# ─────────────────────────── video helpers ────────────────────────────────

def _video_stream():
    while True:
        # eventlet.sleep(0) yields control to other greenlets so that
        # socket handlers, the analyzed_image route, etc. are not starved
        # by this tight encoding loop.
        eventlet.sleep(0)
        frame = imageProcess.updateImage()
        if frame is None:
            continue
        cv2.line(frame, (200, 0), (200, 1000), (0, 0, 255), 1)
        cv2.line(frame, (0, 330), (1000, 330), (0, 0, 255), 1)
        ret, buffer = cv2.imencode('.jpeg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


def _analyzed_image_response():
    """Return the analyzed frame as a single JPEG response (not a stream).
    Using an MJPEG stream for a static <img> tag kept the connection open
    indefinitely, causing 4-12 s delays before the image appeared.
    """
    frame = imageProcess.getAnalyzedImage()
    if frame is None:
        return None, None
    ret, buffer = cv2.imencode('.jpeg', frame)
    if not ret:
        return None, None
    return buffer.tobytes(), imageProcess.get_analysis_data()


# ─────────────────────────── SPA catch-all ────────────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template("index.html", async_mode=socketio.async_mode)


# ─────────────────────────── video feeds ──────────────────────────────────

@app.route('/video_feed')
def video_feed():
    return Response(_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/analyzed_image')
def analyzed_image():
    jpeg_bytes, analysis_data = _analyzed_image_response()
    if jpeg_bytes is None:
        return '', 204
    # Push analysis data alongside the image
    if analysis_data is not None:
        socketio.emit('analysis_data', analysis_data)
    return Response(jpeg_bytes, mimetype='image/jpeg')


# ─────────────────────────── calibration ──────────────────────────────────

@app.route('/length_calibration', methods=['POST'])
def length_calibration():
    try:
        data = request.get_json()
        print("Length calibration data:", data)
        old_ratio = imageProcess.get_px_mm_ratio() if hasattr(imageProcess, 'get_px_mm_ratio') else None
        imageProcess.write_px_mm_ratio(data['ratio'])
        logEvent(
            etapa="CALIBRATION", status="SUCCESS",
            vision_params={"old_ratio": old_ratio, "new_ratio": data['ratio']},
            additional_data={"calibration_type": "length"},
        )
        return "ok"
    except Exception as e:
        logEvent(etapa="CALIBRATION", status="ERROR",
                 error_code="LENGTH_CALIB_ERROR", error_msg=str(e),
                 additional_data={"calibration_type": "length"})
        return {"error": str(e)}, 500


@app.route('/calibrate_zoi', methods=['POST'])
def calibrate_zoi():
    try:
        data = request.get_json()
        print("Calibrate ZOI data:", data)
        imageProcess.writeZOI(data)
        logEvent(
            etapa="CALIBRATION", status="SUCCESS",
            vision_params={"zoi": data},
            additional_data={"calibration_type": "zoi"},
        )
        return "ok"
    except Exception as e:
        logEvent(etapa="CALIBRATION", status="ERROR",
                 error_code="ZOI_CALIB_ERROR", error_msg=str(e),
                 additional_data={"calibration_type": "zoi"})
        return {"error": str(e)}, 500


# ─────────────────────────── fish / config ────────────────────────────────

@app.route('/update_fish_params', methods=['POST'])
def update_fish_params_route():
    data = request.get_json()
    result = update_fish_params(data)
    status = 200 if result.get("status") == "ok" else 404
    return json.dumps(result), status, {"Content-Type": "application/json"}


@app.route('/update_config', methods=['POST'])
def update_config_route():
    data = request.get_json()
    result, status = update_config(data)
    return json.dumps(result), status, {"Content-Type": "application/json"}


@app.route('/get_config', methods=['GET'])
def get_config_route():
    result, status = get_config()
    return json.dumps(result), status, {"Content-Type": "application/json"}

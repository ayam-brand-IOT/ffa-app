#!/usr/bin/env python3
"""Regression tests for stale analysis state and audit-image persistence."""

import json
import os
import sys
import tempfile
import threading
import time as native_time
import types
from pathlib import Path

import cv2
import numpy as np


TESTS_DIR = Path(__file__).resolve().parent
APP_DIR = TESTS_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# imageProcess only needs eventlet.patcher to recover native threading here.
eventlet_module = types.ModuleType("eventlet")
eventlet_module.__path__ = []
patcher_module = types.ModuleType("eventlet.patcher")
patcher_module.original = lambda module_name: (
    threading if module_name == "threading" else native_time
)
eventlet_module.patcher = patcher_module
sys.modules.setdefault("eventlet", eventlet_module)
sys.modules.setdefault("eventlet.patcher", patcher_module)


temp_dir = tempfile.TemporaryDirectory()
config_path = Path(temp_dir.name) / "vision_config.json"
images_path = Path(temp_dir.name) / "muestras"
config_path.write_text(
    json.dumps(
        {
            "zoi": [{"x": 40, "y": 100}, {"x": 940, "y": 530}],
            "ppmm": 0.23,
            "species_params": [],
        }
    ),
    encoding="utf-8",
)
os.environ["VISION_CONFIG_PATH"] = str(config_path)
os.environ["SAMPLE_IMAGES_PATH"] = str(images_path)

import imageProcess  # noqa: E402


def test_failed_analysis_clears_previous_result():
    imageProcess.last_frame = np.ones((2, 2, 3), dtype=np.uint8)
    imageProcess.captured_data = '{"length": 999}'
    imageProcess._pending_frame = None

    result = imageProcess.run_analysis()

    assert result["ok"] is False
    assert imageProcess.getAnalyzedImage() is None
    assert imageProcess.get_analysis_data() is None


def test_pending_frame_is_consumed_once():
    frame = np.zeros((650, 1000, 3), dtype=np.uint8)
    imageProcess.handle_capture(None, frame)
    imageProcess.fish_parameters = {}

    first_result = imageProcess.run_analysis()
    second_result = imageProcess.run_analysis()

    assert first_result["ok"] is False
    assert "Parametros de pescado invalidos" in first_result["reason"]
    assert second_result["reason"] == "No hay frame pendiente para analizar"


def test_audit_image_write_is_verified():
    image_path = images_path / "audit.png"
    frame = np.zeros((20, 20, 3), dtype=np.uint8)

    assert imageProcess._save_raw_frame(image_path, frame) is True
    assert image_path.exists()
    assert cv2.imread(str(image_path)) is not None


def test_zero_line_fallback_is_local_to_one_analysis():
    original_zoi = (
        imageProcess.zoi_x1,
        imageProcess.zoi_y1,
        imageProcess.zoi_x2,
        imageProcess.zoi_y2,
    )
    original_zero_line = imageProcess.zero_line
    original_params = imageProcess.fish_parameters
    try:
        imageProcess.zoi_x1 = 40
        imageProcess.zoi_y1 = 100
        imageProcess.zoi_x2 = 150
        imageProcess.zoi_y2 = 530
        imageProcess.zero_line = 200
        imageProcess.fish_parameters = {
            "BODY_OFFSET": 0,
            "HEAD_CUT_OFFSET": 1,
            "TAIL_TRIGGER_DIAMETER": 0,
        }

        result = imageProcess.run_analysis(
            np.zeros((650, 1000, 3), dtype=np.uint8)
        )

        assert result["ok"] is True
        assert imageProcess.zero_line == 200
    finally:
        (
            imageProcess.zoi_x1,
            imageProcess.zoi_y1,
            imageProcess.zoi_x2,
            imageProcess.zoi_y2,
        ) = original_zoi
        imageProcess.zero_line = original_zero_line
        imageProcess.fish_parameters = original_params


def test_boolean_measurement_parameters_are_rejected():
    try:
        imageProcess.validate_fish_parameters(
            {
                "BODY_OFFSET": True,
                "HEAD_CUT_OFFSET": 1,
                "TAIL_TRIGGER_DIAMETER": 1,
            }
        )
    except ValueError:
        return
    raise AssertionError("Boolean fish parameters must not be accepted as numbers")


def test_camera_open_failure_can_recover_without_restart():
    original_video_capture = imageProcess.cv2.VideoCapture
    original_state = (
        imageProcess.cap,
        imageProcess._camera_unavailable,
        imageProcess._camera_retry_delay,
        imageProcess._camera_next_retry_at,
        imageProcess._camera_read_failures,
        imageProcess._camera_failure_reported,
    )
    open_results = iter((False, True))

    class FakeCapture:
        def __init__(self, opened):
            self.opened = opened
            self.released = False

        def isOpened(self):
            return self.opened

        def release(self):
            self.released = True

    imageProcess.cv2.VideoCapture = lambda source: FakeCapture(next(open_results))
    imageProcess.cap = None
    imageProcess._camera_unavailable = False
    imageProcess._camera_retry_delay = imageProcess.CAMERA_RETRY_INITIAL
    imageProcess._camera_next_retry_at = 0.0
    imageProcess._camera_read_failures = 0
    imageProcess._camera_failure_reported = False
    try:
        assert imageProcess._open_camera() is False
        assert imageProcess._camera_unavailable is True

        imageProcess._camera_next_retry_at = 0.0
        assert imageProcess._open_camera() is True
        assert imageProcess._camera_unavailable is False
        assert imageProcess.cap is not None
    finally:
        if imageProcess.cap is not None and imageProcess.cap is not original_state[0]:
            imageProcess.cap.release()
        imageProcess.cv2.VideoCapture = original_video_capture
        (
            imageProcess.cap,
            imageProcess._camera_unavailable,
            imageProcess._camera_retry_delay,
            imageProcess._camera_next_retry_at,
            imageProcess._camera_read_failures,
            imageProcess._camera_failure_reported,
        ) = original_state


def main():
    try:
        test_failed_analysis_clears_previous_result()
        test_pending_frame_is_consumed_once()
        test_audit_image_write_is_verified()
        test_zero_line_fallback_is_local_to_one_analysis()
        test_boolean_measurement_parameters_are_rejected()
        test_camera_open_failure_can_recover_without_restart()
        print("Image process safety tests passed")
    finally:
        temp_dir.cleanup()


if __name__ == "__main__":
    main()

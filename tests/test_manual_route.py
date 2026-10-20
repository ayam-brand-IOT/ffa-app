#!/usr/bin/env python3
"""The operator manual is served from dist/manual, not swallowed by the SPA catch-all."""

import sys
import tempfile
import types
import unittest
from pathlib import Path

from flask import Flask

TESTS_DIR = Path(__file__).resolve().parent
APP_DIR = TESTS_DIR.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Real Flask routing, stubbed hardware: only the HTTP layer is exercised.
DIST = tempfile.TemporaryDirectory()
(Path(DIST.name) / "index.html").write_text("<p>spa</p>")
(Path(DIST.name) / "manual" / "img").mkdir(parents=True)
(Path(DIST.name) / "manual" / "index.html").write_text("<title>FFA Station Manual</title>")
(Path(DIST.name) / "manual" / "img" / "a.jpg").write_bytes(b"jpg")

app_module = types.ModuleType("app")
app_module.app = Flask("ffa_test", template_folder=DIST.name)
app_module.socketio = types.SimpleNamespace(async_mode="threading")
sys.modules["app"] = app_module
for name in ("cv2", "eventlet", "imageProcess"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["logger"] = types.SimpleNamespace(logEvent=lambda *a, **k: None)
sys.modules["services.config_service"] = types.SimpleNamespace(
    update_fish_params=None, update_config=None, get_config=None)

import routes  # noqa: E402

routes.MANUAL_DIR = str(Path(DIST.name) / "manual")


class ManualRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_manual_index_and_assets(self):
        self.assertEqual(self.client.get("/manual").status_code, 302)
        page = self.client.get("/manual/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"FFA Station Manual", page.data)
        self.assertEqual(self.client.get("/manual/img/a.jpg").data, b"jpg")

    def test_missing_file_is_404_not_the_spa(self):
        self.assertEqual(self.client.get("/manual/img/nope.jpg").status_code, 404)

    def test_traversal_is_refused(self):
        self.assertEqual(self.client.get("/manual/../index.html").status_code, 404)

    def test_spa_routes_still_work(self):
        self.assertIn(b"spa", self.client.get("/config").data)


if __name__ == "__main__":
    unittest.main()

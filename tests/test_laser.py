#!/usr/bin/env python3
"""The laser is on only while a client shows the analysis screen."""
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_socket_availability as fixtures

sockets = fixtures.sockets


class LaserTests(unittest.TestCase):
    def setUp(self):
        fixtures.reset_state()
        self.laser = []
        self.flash = []
        fixtures.hardware_module.ios.set_laser = self.laser.append
        fixtures.hardware_module.ios.set_flash = self.flash.append
        sockets.ios = fixtures.hardware_module.ios
        sockets._ensure_poller = lambda: None

    def as_client(self, sid):
        fixtures.request.sid = sid

    def test_connecting_does_not_turn_the_laser_on(self):
        sockets.on_connect(None)
        self.assertNotIn(True, self.laser)

    def test_analysis_screen_turns_it_on_and_leaving_turns_it_off(self):
        self.as_client("kiosk")
        sockets.arm_laser()
        sockets.disarm_laser()
        self.assertEqual(self.laser, [True, False])

    def test_stays_on_while_another_client_is_analysing(self):
        self.as_client("kiosk")
        sockets.arm_laser()
        self.as_client("office")
        sockets.arm_laser()
        sockets.on_disconnect()
        self.assertEqual(self.laser[-1], True)
        self.as_client("kiosk")
        sockets.disarm_laser()
        self.assertEqual(self.laser[-1], False)

    def test_disconnect_of_the_last_analyser_turns_it_off(self):
        self.as_client("kiosk")
        sockets.arm_laser()
        sockets.on_disconnect()
        self.assertEqual(self.laser[-1], False)

    def test_arming_during_the_flash_waits_for_the_capture(self):
        self.as_client("kiosk")
        sockets._flash_on = True
        sockets.arm_laser()
        self.assertEqual(self.laser, [])

    def test_capture_restores_the_laser_only_on_the_analysis_screen(self):
        image_process = sockets.imageProcess
        image_process.get_frame_marker = lambda: {"seq": 0}
        image_process.wait_for_frame_since = lambda *a, **k: object()
        image_process.handle_capture = lambda callback, frame=None: frame
        for armed, expected in ((True, True), (False, False)):
            with self.subTest(armed=armed):
                self.laser.clear()
                sockets._laser_sids.clear()
                if armed:
                    sockets._laser_sids.add("kiosk")
                sockets._capture_with_synced_flash()
                self.assertEqual(self.laser, [False, expected])
                self.assertFalse(sockets._flash_on)


if __name__ == "__main__":
    unittest.main()

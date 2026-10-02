#!/usr/bin/env python3
"""Confirmed-weight detection and the GPIO 17 ready beep, without hardware."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_socket_availability as fixtures
from scale_ready import ReadyDetector

sockets = fixtures.sockets


def reading(net, stable=True, division=1.0, **extra):
    snapshot = {"net": net, "gross": net, "stable": stable, "division": division,
                "ok": True, "stale": False, "faults": [], "near_zero": False}
    snapshot.update(extra)
    return snapshot


class ReadyDetectorTests(unittest.TestCase):
    def feed(self, detector, values, **extra):
        return [detector.update(reading(v, **extra)) for v in values]

    def test_needs_consecutive_stable_readings(self):
        d = ReadyDetector(samples=3, min_grams=20)
        results = self.feed(d, (1000, 1000, 1000))
        self.assertEqual([r[0] for r in results], [False, False, True])
        self.assertEqual(results[-1], (True, 1000, True))

    def test_flicker_restarts_the_count_without_a_second_beep(self):
        d = ReadyDetector(samples=3, min_grams=20)
        self.feed(d, (1000, 1000, 1000))
        self.assertEqual(d.update(reading(1000, stable=False)), (False, None, False))
        results = self.feed(d, (1000, 1000, 1000))
        self.assertEqual(results[-1], (True, 1000, False))

    def test_early_stable_flag_on_a_settling_load_is_not_ready(self):
        # Bench: stability raised at 980 g, then the load settled at 1000 g.
        d = ReadyDetector(samples=3, min_grams=20)
        results = self.feed(d, (980, 990, 1000))
        self.assertFalse(any(r[0] for r in results))
        results = self.feed(d, (1000, 1000))
        self.assertEqual(results[-1], (True, 1000, True))

    def test_new_load_announces_and_empty_scale_rearms(self):
        d = ReadyDetector(samples=2, min_grams=20)
        self.assertTrue(self.feed(d, (500, 500))[-1][2])
        self.assertTrue(self.feed(d, (750, 750))[-1][2])  # changed beyond a division
        self.feed(d, (0, 0))
        self.assertTrue(self.feed(d, (750, 750))[-1][2])  # same weight, new fish

    def test_empty_faulty_stale_or_offline_readings_never_ready(self):
        cases = [dict(), dict(faults=["ADC_FAILURE"]), dict(stale=True), dict(ok=False)]
        for extra in cases:
            with self.subTest(extra=extra):
                d = ReadyDetector(samples=1, min_grams=20)
                self.assertFalse(d.update(reading(1000, **extra) if extra else reading(5))[0])


class ReadyBeepSocketTests(unittest.TestCase):
    def setUp(self):
        fixtures.reset_state()
        fixtures.request.sid = "home"
        self.buzzer = []
        fixtures.hardware_module.ios.set_buzzer = self.buzzer.append
        sockets.ios = fixtures.hardware_module.ios
        self.detector = patch.object(sockets, "_ready", ReadyDetector(samples=3, min_grams=20))
        self.detector.start()

    def tearDown(self):
        self.detector.stop()

    def beeps(self):
        # Run started background tasks; each beep is on then off.
        for function, args, _ in list(fixtures.socketio.started):
            function(*args)
        fixtures.socketio.started.clear()
        return self.buzzer

    def settle(self, value=1000):
        for _ in range(3):
            sockets._update_ready(reading(value))

    def test_capture_screen_gets_one_short_beep_per_load(self):
        sockets.arm_ready_beep()
        self.settle()
        self.settle()
        self.assertEqual(self.beeps(), [True, False])
        sockets._emit_scale_snapshot(reading(1000), tension_mode=False)
        status = fixtures.socketio.emitted[-1][1]
        self.assertTrue(status["ready"])
        self.assertEqual(status["ready_value"], 1000)

    def test_no_beep_outside_capture_screen(self):
        self.settle()
        self.assertEqual(self.beeps(), [])
        sockets.arm_ready_beep()
        sockets.disarm_ready_beep()
        sockets._update_ready(reading(0))
        self.settle(800)
        self.assertEqual(self.beeps(), [])

    def test_disconnect_disarms(self):
        sockets.arm_ready_beep()
        sockets.on_disconnect()
        self.settle()
        self.assertEqual(self.beeps(), [])

    def test_tension_mode_never_reports_ready(self):
        self.settle()
        sockets._emit_scale_snapshot(reading(1000), tension_mode=True)
        status = fixtures.socketio.emitted[-1][1]
        self.assertFalse(status["ready"])
        self.assertIsNone(status["ready_value"])

    def test_buzzer_is_switched_off_even_if_sleep_fails(self):
        with patch.object(fixtures.socketio, "sleep", side_effect=RuntimeError("hub")):
            sockets._beep_task()
        self.assertEqual(self.buzzer, [True, False])


if __name__ == "__main__":
    unittest.main()

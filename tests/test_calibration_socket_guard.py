#!/usr/bin/env python3
"""Socket calibration ownership, cancellation and raw-diagnostic contracts."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_socket_availability as fixtures

sockets = fixtures.sockets
net = fixtures.net


class CalibrationSocketGuardTests(unittest.TestCase):
    def setUp(self):
        fixtures.reset_state()
        fixtures.request.sid = "client-a"
        self.events = []
        self.calls = []
        self.emit = patch.object(sockets, "emit", lambda name, data: self.events.append((name, data)))
        self.emit.start()
        net.remote_calibration = self.calibrate
        net.readCalibrationDiagnostics = lambda belly: {"slave": 2 if belly else 1}

    def tearDown(self):
        self.emit.stop()

    def calibrate(self, step, mode):
        self.calls.append((step, mode))
        return {"net": 1000, "gross": 1000}

    def send(self, step=1, mode="weight"):
        sockets.calibrate_load_cell({"step": step, "args": mode, "request_id": "r1"})

    def test_success_is_correlated_and_finish_releases_cache(self):
        self.send()
        name, data = self.events[-1]
        self.assertEqual(name, "calibration_step_commited")
        self.assertEqual(data["step"], 1)
        self.assertEqual(data["request_id"], "r1")
        self.assertEqual(data["diagnostic"]["gross"], 1000)
        self.send(4)
        self.assertIsNone(sockets._calibration_owner_sid)
        self.assertFalse(sockets._calibration_inflight)
        self.assertFalse(net.calibrating)
        self.assertEqual(sockets._last_snapshot, {"weight": None, "tension": None})

    def test_only_confirmed_weight_steps_beep(self):
        started = fixtures.socketio.started
        fixtures.hardware_module.ios.set_buzzer = lambda value: None
        beeps = lambda: sum(1 for task in started if task[0] is sockets._beep_task)
        self.send(1)
        self.assertEqual(beeps(), 0)
        for step in (2, 3, 4):
            self.send(step)
        self.assertEqual(beeps(), 3)

        def fail(step, mode):
            raise RuntimeError("weight never stabilised")
        net.remote_calibration = fail
        self.send(1)
        self.send(2)
        self.assertEqual(beeps(), 3)
        del fixtures.hardware_module.ios.set_buzzer

    def test_bad_payloads_do_not_reach_driver(self):
        for payload in [None, [], "bad", {}, {"step": True, "args": "weight"},
                        {"step": 1, "args": "unknown"}]:
            sockets.calibrate_load_cell(payload)
            self.assertEqual(self.events[-1][0], "calibration_error")
        self.assertEqual(self.calls, [])

    def test_foreign_client_cannot_release_owner(self):
        self.send()
        fixtures.request.sid = "client-b"
        self.send()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(sockets._calibration_owner_sid, "client-a")
        self.assertTrue(net.calibrating)

    def test_overlapping_step_is_rejected_without_aborting_owner(self):
        def overlap(step, mode):
            self.calls.append((step, mode))
            self.send(step)
            self.assertTrue(sockets._calibration_inflight)
            self.assertFalse(sockets._calibration_release_pending)
            return {}

        net.remote_calibration = overlap
        self.send()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual([event[0] for event in self.events],
                         ["calibration_error", "calibration_step_commited"])

    def test_disconnect_defers_release_until_command_returns(self):
        def disconnect(step, mode):
            sockets.on_disconnect()
            self.assertEqual(sockets._calibration_owner_sid, "client-a")
            self.assertTrue(net.calibrating)
            self.assertTrue(sockets._calibration_release_pending)
            return {}

        net.remote_calibration = disconnect
        self.send()
        self.assertIsNone(sockets._calibration_owner_sid)
        self.assertFalse(net.calibrating)
        self.assertFalse(sockets._calibration_inflight)
        self.assertNotIn("calibration_step_commited", [event[0] for event in self.events])

    def test_cancel_does_not_claim_rollback_or_acknowledge_inflight_step(self):
        def cancel(step, mode):
            sockets.resume_net_update()
            self.assertTrue(net.calibrating)
            return {}

        net.remote_calibration = cancel
        self.send()
        self.assertEqual(self.events[-1][0], "calibration_error")
        self.assertIn("pudo haberse aplicado", self.events[-1][1]["error"])
        self.assertFalse(net.calibrating)

    def test_failed_driver_never_acknowledges_success(self):
        def fail(step, mode):
            raise RuntimeError("gross=1000 net=883.5")

        net.remote_calibration = fail
        self.send()
        self.assertEqual(self.events[-1][0], "calibration_error")
        self.assertIsNone(sockets._calibration_owner_sid)

    def test_hardware_changes_blocked_during_session(self):
        self.send()
        for handler in (sockets.set_zero, sockets.set_tare, sockets.clear_tare,
                        sockets.enter_to_weight_mode, sockets.enter_to_tension_test):
            # FakeNet has no hardware methods: reaching the driver would fail.
            handler()
            self.assertIn("No se permite", self.events[-1][1]["error"])

    def test_queued_hardware_change_rechecks_ownership_under_lock(self):
        class ClaimOnEnter:
            def __enter__(self):
                sockets._claim_calibration("client-a")

            def __exit__(self, *args):
                return False

        with patch.object(sockets, "thread_lock", ClaimOnEnter()):
            sockets.set_tare()
        self.assertEqual(self.events[-1][0], "calibration_error")

    def test_cancel_while_waiting_for_lock_does_not_call_driver(self):
        class CancelOnEnter:
            def __enter__(self):
                sockets.resume_net_update()

            def __exit__(self, *args):
                return False

        with patch.object(sockets, "thread_lock", CancelOnEnter()):
            self.send()
        self.assertEqual(self.calls, [])
        self.assertIsNone(sockets._calibration_owner_sid)
        self.assertEqual(self.events[-1][0], "calibration_error")

    def test_raw_diagnostic_endpoint_has_no_calibration_side_effect(self):
        sockets.get_scale_diagnostics({"mode": "belly"})
        self.assertEqual(self.events[-1], ("scale_diagnostics", {"slave": 2}))
        self.assertEqual(self.calls, [])
        self.assertFalse(net.calibrating)

    def test_diagnostics_blocked_during_calibration_and_on_invalid_input(self):
        for payload in [False, {"mode": "unknown"}]:
            sockets.get_scale_diagnostics(payload)
            self.assertEqual(self.events[-1][0], "scale_diagnostics_error")
        self.send()
        sockets.get_scale_diagnostics()
        self.assertEqual(self.events[-1][0], "scale_diagnostics_error")

    def test_real_driver_and_socket_complete_only_validated_steps(self):
        import test_tlb_registers as registers
        driver = registers.tlb
        registers.reset()
        inst = driver.instrument
        inst.registers[13] = 263
        inst.set_stable(True)
        with patch.object(sockets, "net", driver), \
                patch.object(driver, "CALIB_VERIFY_INTERVAL", 0.001):
            self.send(1)
            self.send(2)
            inst.set_gross(9960)
            inst.set_net(9960)
            self.send(3)
            self.send(4)
        self.assertEqual([data["step"] for name, data in self.events
                          if name == "calibration_step_commited"], [1, 2, 3, 4])
        self.assertEqual(inst.commands, [100, 101, 99])
        self.assertIsNone(driver._calibration_session)
        self.assertIsNone(sockets._calibration_owner_sid)

    def test_real_driver_failure_does_not_acknowledge_or_leave_lease(self):
        import test_tlb_registers as registers
        driver = registers.tlb
        registers.reset()
        inst = driver.instrument
        inst.registers[13] = 263
        inst.set_stable(True)
        inst.set_gross(1165)
        inst.set_net(0)
        with patch.object(sockets, "net", driver):
            self.send(1)
        self.assertEqual(self.events[-1][0], "calibration_error")
        self.assertEqual(inst.commands, [])
        self.assertFalse(driver.isCalibrating)
        self.assertIsNone(sockets._calibration_owner_sid)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Hardware-free evidence/validation tests, not proof of firmware compatibility."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_tlb_registers as registers

tlb = registers.tlb
FakeInstrument = registers.FakeInstrument


class CalibrationDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        registers.reset()
        tlb._division = None
        self.timeout = patch.object(tlb, "CALIB_VERIFY_TIMEOUT", 0.02)
        self.interval = patch.object(tlb, "CALIB_VERIFY_INTERVAL", 0.001)
        self.timeout.start()
        self.interval.start()
        for inst in (tlb.instrument, tlb.instrument2):
            inst.registers[13] = 263
            inst.set_stable(True)

    def tearDown(self):
        self.timeout.stop()
        self.interval.stop()
        tlb.setCalibrating(False)

    def begin(self, mode="weight"):
        tlb.remote_calibration(1, mode)
        tlb.remote_calibration(2, mode)

    def load_reference(self, inst=None):
        inst = inst or tlb.instrument
        inst.set_gross(9960)
        inst.set_net(9960)

    def test_unverified_status_blocks_all_calibration_entry_points(self):
        tlb.STATUS_MAP_VERIFIED = False
        actions = [lambda: tlb.remote_calibration(1, "weight"),
                   lambda: tlb.add_calibration_point(1000),
                   tlb.cancel_calibration, tlb.physical_calibration]
        for action in actions:
            with self.assertRaisesRegex(tlb.TLBCalibrationError, "verify"):
                action()
        self.assertEqual(tlb.instrument.commands, [])

    def test_diagnostics_read_real_registers_while_polling_is_paused(self):
        tlb.setCalibrating(True)
        tlb.instrument.set_gross(1165)
        tlb.instrument.set_net(0)
        tlb.instrument.registers[6] = 1 << 11
        snapshot = tlb.readCalibrationDiagnostics()
        self.assertEqual(snapshot["gross"], 116.5)
        self.assertEqual(snapshot["net"], 0)
        self.assertEqual(snapshot["status_raw"], 1 << 11)
        self.assertTrue(snapshot["status_candidates"]["legacy"]["stable"])
        self.assertFalse(snapshot["status_candidates"]["wtb_1_19_table"]["stable"])
        self.assertEqual(len(snapshot["registers_40001_40014"]), 14)
        self.assertIsNone(snapshot["registers_40001_40014"][5])
        self.assertEqual(tlb.instrument.commands, [])

    def test_diagnostics_never_read_write_only_command_register(self):
        original = tlb._read
        with patch.object(tlb, "_read", wraps=original) as read:
            tlb.readCalibrationDiagnostics()
        self.assertEqual([(call.args[1], call.args[2]) for call in read.call_args_list],
                         [(0, 5), (6, 8)])

    def test_bench_status_words_keep_zero_and_negative_half_gram_distinct(self):
        for status, magnitude, expected, near_zero in [
                (0x1800, 0, 0.0, True),
                (0x0980, 5, -0.5, False),
                (0x0800, 10000, 1000.0, False)]:
            with self.subTest(status=hex(status)):
                tlb.instrument.set_gross(magnitude)
                tlb.instrument.set_net(magnitude)
                tlb.instrument.registers[6] = status
                snapshot = tlb.readCalibrationDiagnostics()
                self.assertEqual(snapshot["gross"], expected)
                self.assertEqual(snapshot["net"], expected)
                self.assertTrue(snapshot["status_candidates"]["legacy"]["stable"])
                self.assertFalse(snapshot["status_candidates"]["legacy"]["net_mode"])
                self.assertEqual(snapshot["status_candidates"]["legacy"]["near_zero"],
                                 near_zero)

    def test_one_gram_reference_error_is_outside_one_division_tolerance(self):
        tlb.instrument.set_gross(9990)
        tlb.instrument.set_net(9990)
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "gross=999.0, net=999.0"):
            tlb._verify_calibration_value("reference_check", False, 1000.0, 263)
        self.assertEqual(tlb.instrument.commands, [])

    def test_diagnostics_never_return_stale_or_cached_configuration(self):
        tlb._division, tlb._unit = 0.001, "kg"
        self.assertEqual(tlb.readCalibrationDiagnostics()["unit"], "g")
        tlb._last_good[1] = (0, {"net": 123})
        with patch.object(FakeInstrument, "read_registers", side_effect=IOError("dead bus")):
            with self.assertRaises(tlb.TLBCommunicationError):
                tlb.readCalibrationDiagnostics()

    def test_observed_empty_offset_is_rejected_before_any_write(self):
        tlb.instrument.set_gross(1165)
        tlb.instrument.set_net(0)
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "Active tare"):
            tlb.remote_calibration(1, "weight")
        self.assertEqual(tlb.instrument.commands, [])

    def test_net_mode_rejected_even_if_net_and_gross_match(self):
        tlb.instrument.registers[6] |= tlb.ST_NET_MODE
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "Active tare"):
            tlb.remote_calibration(1, "weight")

    def test_ignored_zero_cannot_advance_to_reference(self):
        tlb.instrument.set_gross(1165)
        tlb.instrument.set_net(1165)
        tlb.remote_calibration(1, "weight")
        original = FakeInstrument.write_register

        def ignore_zero(inst, address, value):
            if address == tlb.REG_COMMAND and value == tlb.CMD_CALIB_TARE:
                inst.commands.append(value)
                return
            return original(inst, address, value)

        with patch.object(FakeInstrument, "write_register", ignore_zero):
            with self.assertRaisesRegex(tlb.TLBCalibrationError, "after_zero"):
                tlb.remote_calibration(2, "weight")
        self.assertEqual(tlb.instrument.commands, [100])
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "Out-of-order"):
            tlb.remote_calibration(3, "weight")

    def test_consumed_reference_does_not_mask_883_5_net(self):
        self.begin()
        self.load_reference()
        original = FakeInstrument.write_register

        def residual_tare(inst, address, value):
            original(inst, address, value)
            if address == tlb.REG_COMMAND and value == tlb.CMD_SAVE_FIRST:
                inst.set_net(8835)

        with patch.object(FakeInstrument, "write_register", residual_tare):
            with self.assertRaisesRegex(tlb.TLBCalibrationError, "gross=1000.0, net=883.5"):
                tlb.remote_calibration(3, "weight")
        self.assertEqual(tlb.instrument.registers[36:38], [0, 0])
        self.assertNotIn(99, tlb.instrument.commands)

    def test_consumed_but_incorrect_reference_is_rejected(self):
        self.begin()
        self.load_reference()
        original = FakeInstrument.write_register

        def incorrect_span(inst, address, value):
            original(inst, address, value)
            if address == tlb.REG_COMMAND and value == tlb.CMD_SAVE_FIRST:
                inst.set_gross(8835)
                inst.set_net(8835)

        with patch.object(FakeInstrument, "write_register", incorrect_span):
            with self.assertRaisesRegex(tlb.TLBCalibrationError, "after_reference"):
                tlb.remote_calibration(3, "weight")
        self.assertNotIn(99, tlb.instrument.commands)

    def test_missing_reference_is_rejected_before_writing(self):
        self.begin()
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "No positive"):
            tlb.remote_calibration(3, "weight")
        self.assertEqual(tlb.instrument.commands, [100])

    def test_configuration_change_aborts_before_zero(self):
        tlb.remote_calibration(1, "weight")
        tlb.instrument.registers[13] = 265
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "configuration changed"):
            tlb.remote_calibration(2, "weight")
        self.assertEqual(tlb.instrument.commands, [])

    def test_kg_not_accepted_until_ui_contract_supports_it(self):
        tlb.instrument.registers[13] = 16
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "unit g"):
            tlb.remote_calibration(1, "weight")

    def test_belly_uses_its_own_configuration(self):
        tlb.instrument.registers[13] = 16  # main in kg, belly in g
        self.begin("belly")
        self.load_reference(tlb.instrument2)
        snapshot = tlb.remote_calibration(3, "belly")
        self.assertEqual(snapshot["slave"], 2)
        self.assertEqual(tlb.instrument2.saved_samples, [10000])
        self.assertEqual(tlb.instrument.commands, [])

    def test_faults_and_wrong_sequence_never_write(self):
        for step, mode in [(True, "weight"), (1, "normal"), (3, "weight")]:
            with self.assertRaises(tlb.TLBCalibrationError):
                tlb.remote_calibration(step, mode)
        tlb.instrument.registers[6] |= tlb.ST_CELL_ERROR
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "LOAD_CELL_ERROR"):
            tlb.remote_calibration(1, "weight")
        self.assertEqual(tlb.instrument.commands, [])

    def test_replayed_step_cannot_restart_session_silently(self):
        self.begin()
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "already started"):
            tlb.remote_calibration(1, "weight")
        self.assertIsNone(tlb._calibration_session)
        self.assertEqual(tlb.instrument.commands, [100])

    def test_save_rechecks_reference_and_does_not_retry_lost_response(self):
        self.begin()
        self.load_reference()
        tlb.remote_calibration(3, "weight")
        original = FakeInstrument.write_register

        def lost_save(inst, address, value):
            original(inst, address, value)
            if address == tlb.REG_COMMAND and value == tlb.CMD_SAVE_EEPROM:
                raise IOError("reply lost after save")

        with patch.object(FakeInstrument, "write_register", lost_save):
            with self.assertRaises(tlb.TLBCommunicationError):
                tlb.remote_calibration(4, "weight")
        self.assertEqual(tlb.instrument.commands.count(99), 1)
        self.assertIsNone(tlb._calibration_session)

    def test_removed_reference_before_save_does_not_send_99(self):
        self.begin()
        self.load_reference()
        tlb.remote_calibration(3, "weight")
        tlb.instrument.set_gross(0)
        tlb.instrument.set_net(0)
        with self.assertRaisesRegex(tlb.TLBCalibrationError, "before_save"):
            tlb.remote_calibration(4, "weight")
        self.assertNotIn(99, tlb.instrument.commands)


if __name__ == "__main__":
    unittest.main()

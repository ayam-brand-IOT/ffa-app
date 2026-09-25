#!/usr/bin/env python3
"""Hardware-free setup-profile, measurement, and diagnostic transport checks."""

import copy
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tlb_setup", ROOT / "tools" / "tlb_setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def snapshot(weight=1000, captured_at=10):
    raw = int(round(abs(weight) * 10))
    status = 0x0980 if weight < 0 else (0x1800 if weight == 0 else 0x0800)
    return {
        "slave": 1, "firmware_register": 11102, "instrument_type_register": 105,
        "unit": "g", "division": 0.5, "division_register": 263,
        "registers_40001_40014": [11102, 105, 11, 1167, 96, None, status,
                                   raw >> 16, raw & 65535, raw >> 16, raw & 65535, 0, 0, 263],
        "status_raw": status, "net": weight, "gross": weight,
        "gross_minus_net": 0.0, "captured_at": captured_at, "stale": False,
        "faults": [], "interpretation": "legacy", "status_map_verified": False,
    }


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.profile = setup.load_profile(setup.PROFILE_PATH)

    def assess(self, weights=(1000, 1000, 1000), expected=1000):
        return setup.assess(self.profile, [snapshot(w, i) for i, w in enumerate(weights)], expected)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = setup.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_default_plan_does_not_open_a_connection(self):
        with patch.object(setup, "DiagnosticClient") as client:
            code, out, _ = self.cli()
        self.assertEqual(code, 0)
        self.assertIn("UNSET", out)
        self.assertIn("cancels real calibration", out)
        client.assert_not_called()

    def test_init_preserves_an_existing_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            self.assertEqual(self.cli("init", "--profile", str(path))[0], 0)
            before = path.read_bytes()
            self.assertEqual(self.cli("init", "--profile", str(path))[0], 2)
            self.assertEqual(path.read_bytes(), before)

    def test_sensitive_targets_must_not_be_guessed(self):
        for key in ("full_scale_g", "sensitivity_mv_v", "max_display_g", "resettable_zero_g"):
            self.assertIsNone(self.profile["keypad_targets"][key])

    def test_invalid_or_destructive_profiles_rejected(self):
        mutations = [
            ("full_scale_g", 0), ("full_scale_g", float("nan")),
            ("sensitivity_mv_v", 8), ("sensitivity_mv_v", "2"),
            ("filter", True), ("filter", 10), ("anti_peak", "unknown"),
            ("power_on_zero_g", 50), ("zero_tracking", 2),
            ("stop_bits", 1), ("display_coefficient", 2),
        ]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                profile = copy.deepcopy(self.profile)
                profile["keypad_targets"][key] = value
                with self.assertRaises(ValueError):
                    setup.validate_profile(profile)

    def test_belly_profile_and_misspelled_fields_rejected(self):
        self.profile["role"] = "belly"
        with self.assertRaises(ValueError):
            setup.validate_profile(self.profile)
        self.profile["role"] = "weight"
        self.profile["expected"]["divison"] = 0.5
        with self.assertRaises(ValueError):
            setup.validate_profile(self.profile)

    def test_pass_does_not_claim_keypad_or_production_validation(self):
        result = self.assess()
        self.assertTrue(result["automatic_check_passed"])
        self.assertFalse(result["keypad_settings_verified"])
        self.assertFalse(result["production_ready"])

    def test_one_gram_deviation_is_not_rounded_away(self):
        self.assertFalse(self.assess((999, 999, 999))["automatic_check_passed"])
        self.assertTrue(self.assess((999.5, 1000, 1000.5))["automatic_check_passed"])

    def test_zero_and_negative_half_gram_use_status_signs(self):
        self.assertTrue(self.assess((0, -0.5, 0), expected=0)["automatic_check_passed"])
        self.assertFalse(self.assess((0, -1, 0), expected=0)["automatic_check_passed"])

    def test_missing_samples_and_transport_errors_fail(self):
        self.assertFalse(self.assess((1000,))["automatic_check_passed"])
        self.assertFalse(setup.assess(self.profile, [], 1000, ["dead bus"])["automatic_check_passed"])

    def test_stale_fault_unstable_or_tare_samples_fail(self):
        for state in ("stale", "fault", "unstable", "tare"):
            samples = [snapshot(1000, i) for i in range(3)]
            d = samples[1]
            if state == "stale":
                d["stale"] = True
            elif state == "fault":
                d["status_raw"] |= 1
            elif state == "unstable":
                d["status_raw"] &= ~(1 << 11)
            else:
                d["status_raw"] |= 1 << 10
            d["registers_40001_40014"][6] = d["status_raw"]
            with self.subTest(state=state):
                self.assertFalse(setup.assess(self.profile, samples, 1000)["automatic_check_passed"])

    def test_duplicate_timestamps_or_instrument_changes_fail(self):
        for state in ("timestamp", "serial", "firmware"):
            samples = [snapshot(1000, i) for i in range(3)]
            if state == "timestamp":
                samples[1]["captured_at"] = 0
            elif state == "serial":
                samples[1]["registers_40001_40014"][3] = 2222
            else:
                samples[1]["firmware_register"] = 11103
                samples[1]["registers_40001_40014"][0] = 11103
            self.assertFalse(setup.assess(self.profile, samples, 1000)["automatic_check_passed"])

    def test_incorrect_decimal_decoder_is_rejected(self):
        samples = [snapshot(1000, i) for i in range(3)]
        for d in samples:
            d["registers_40001_40014"][8] = 2000
            d["registers_40001_40014"][10] = 2000
        self.assertFalse(setup.assess(self.profile, samples, 1000)["automatic_check_passed"])

    def test_malformed_raw_or_nonfinite_snapshot_rejected(self):
        for field, value in (("net", float("nan")), ("stale", None), ("status_raw", 42)):
            d = snapshot()
            d[field] = value
            with self.assertRaises(ValueError):
                setup.validate_snapshot(d)
        d = snapshot()
        d["registers_40001_40014"][5] = 0
        with self.assertRaises(ValueError):
            setup.validate_snapshot(d)

    def test_check_requires_ack_and_finite_arguments_before_connecting(self):
        with patch.object(setup, "DiagnosticClient") as client:
            for args in [(), ("--expected-g", "0"),
                         ("--expected-g", "nan", "--ack-connection-outputs"),
                         ("--expected-g", "0", "--samples", "0", "--ack-connection-outputs")]:
                self.assertEqual(self.cli("check", *args)[0], 2)
            client.assert_not_called()

    def test_check_reports_failure_and_closes_client(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            with patch.object(setup, "DiagnosticClient") as client, patch.object(setup.time, "sleep"):
                client.return_value.__enter__.return_value.read.side_effect = [snapshot(), RuntimeError("dead bus")]
                code, _, _ = self.cli("check", "--expected-g", "1000", "--samples", "3",
                                      "--ack-connection-outputs", "--report", str(path))
                client.return_value.__exit__.assert_called_once()
            self.assertEqual(code, 1)
            report = json.loads(path.read_text())
            self.assertFalse(report["automatic_check_passed"])
            self.assertIn("dead bus", report["problems"])

    def test_existing_report_prevents_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text("preserve")
            with patch.object(setup, "DiagnosticClient") as client:
                self.assertEqual(self.cli("check", "--expected-g", "0", "--report", str(path),
                                          "--ack-connection-outputs")[0], 2)
                client.assert_not_called()
            self.assertEqual(path.read_text(), "preserve")

    def test_transport_only_sends_diagnostic_event_and_answers_ping(self):
        client = setup.DiagnosticClient("http://127.0.0.1:3030")
        polls = iter(['0{"sid":"abc"}', '40{"sid":"socket"}',
                      '42["weight_update",123]\x1e42' + json.dumps(["scale_diagnostics", snapshot()]) + '\x1e2'])
        sent = []

        def request(url, payload=None):
            if payload is not None:
                sent.append(payload)
                return "ok"
            return next(polls)

        with patch.object(client, "request", side_effect=request):
            with client:
                self.assertEqual(client.read()["net"], 1000)
        self.assertEqual(sent, ['40', '42["get_scale_diagnostics",{"mode":"weight"}]', '3', '41\x1e1'])
        self.assertIsNone(client.url)

    def test_backend_diagnostic_errors_are_not_fallback_weights(self):
        client = setup.DiagnosticClient("http://127.0.0.1:3030")
        client.url = client.base
        with patch.object(client, "request", return_value='42["scale_diagnostics_error",{"error":"unsupported"}]'):
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                client.receive()

    def test_invalid_handshakes_fail_cleanly(self):
        for hello in ('0null', '0[]', '0{}', '0{"sid":false}', '42["other",1]'):
            client = setup.DiagnosticClient("http://127.0.0.1:3030")
            with patch.object(client, "request", return_value=hello):
                with self.assertRaises((ValueError, RuntimeError)):
                    client.__enter__()
            self.assertIsNone(client.url)

    def test_http_transport_uses_text_polling_and_finite_timeout(self):
        client = setup.DiagnosticClient("http://127.0.0.1:3030", timeout=2)
        with patch.object(setup, "urlopen") as opening:
            opening.return_value.__enter__.return_value.read.return_value = b"ok"
            self.assertEqual(client.request(client.base, "40"), "ok")
        request = opening.call_args.args[0]
        self.assertEqual(request.data, b"40")
        self.assertEqual(request.get_header("Content-type"), "text/plain;charset=UTF-8")
        self.assertIn("EIO=4&transport=polling&t=", request.full_url)
        self.assertEqual(opening.call_args.kwargs["timeout"], 2)

    def test_unsafe_url_forms_rejected(self):
        for url in ("file:///tmp/x", "http://user:secret@host", "http://host/api", "http://host?q=1"):
            with self.assertRaises(ValueError):
                setup.DiagnosticClient(url)


if __name__ == "__main__":
    unittest.main()

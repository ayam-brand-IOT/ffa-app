#!/usr/bin/env python3
"""Plan and verify an FFA weighing transmitter without Modbus writes.

Run without arguments for the keypad checklist. See docs/TLB_SETUP.md.
Uses the running diagnostic backend, never a second serial connection.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


PROFILE_PATH = Path(__file__).with_name("tlb_setup_profile.example.json")
# Division in grams -> raw register 40014 (unit g in the high byte, division
# index low) and the factor from display digits to grams.
SUPPORTED_DIVISIONS = {0.5: (263, 0.1), 1: (262, 1)}
MANUAL_LABELS = {
    "full_scale_g": "CALib / FS-tEO (g): rated system capacity, NOT net payload",
    "sensitivity_mv_v": "CALib / SEnSib (mV/V): use the load-cell datasheet",
    "max_display_g": "CALib / MASS (g): 0 disables the display limit",
    "filter": "FiLtEr: static weighing starting point, validate settling time",
    "anti_peak": "FiLtEr / anti-peak",
    "power_on_zero_g": "PArA 0 / AUTO 0 (g): 0 disables power-on zero",
    "zero_tracking": "PArA 0 / TRAC 0: NONE disables zero tracking",
    "resettable_zero_g": "PArA 0 / 0 SEt (g): read the decimal point carefully",
    "preset_tare_g": "P-tArE (g): do not use it for the permanent structure",
    "display_coefficient": "CALib / COEFF",
    "protocol": "SEriAL / rS485 protocol",
    "baudrate": "SEriAL / bAUd",
    "data_bits": "Serial data bits (backend setting)",
    "parity": "SEriAL / PArity",
    "stop_bits": "SEriAL / StOP (match the backend, not the factory default)",
    "response_delay_ms": "SEriAL / dELAY (ms)",
}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_profile(profile):
    if (not isinstance(profile, dict) or type(profile.get("schema_version")) is not int
            or profile["schema_version"] != 1):
        raise ValueError("Unsupported profile schema")
    if profile.get("role") != "weight":
        raise ValueError("This profile is for static weighing, not the belly test")
    expected = profile.get("expected", {})
    if not isinstance(expected, dict) or set(expected) != {
            "slave", "firmware_register", "instrument_type_register", "unit", "division"}:
        raise ValueError("expected must contain exactly the documented fields")
    for key in ("slave", "firmware_register", "instrument_type_register"):
        if type(expected.get(key)) is not int or expected[key] <= 0:
            raise ValueError("expected." + key + " must be a positive integer")
    if (expected["slave"] != 1 or expected.get("unit") != "g"
            or type(expected.get("division")) not in (int, float)
            or expected["division"] not in SUPPORTED_DIVISIONS):
        raise ValueError("This tool currently supports primary slave 1, grams, division 0.5 or 1")
    manual = profile.get("keypad_targets")
    if not isinstance(manual, dict) or set(manual) != set(MANUAL_LABELS):
        raise ValueError("keypad_targets must contain exactly the documented fields")
    for key in ("full_scale_g", "sensitivity_mv_v", "max_display_g", "resettable_zero_g"):
        value = manual[key]
        if value is not None and (not number(value) or value < 0):
            raise ValueError(key + " must be null or a finite non-negative number")
    if manual["full_scale_g"] == 0:
        raise ValueError("FS-tEO=0 resets factory settings; it is not a valid setup target")
    sensitivity = manual["sensitivity_mv_v"]
    if sensitivity is not None and not 0.5 <= sensitivity <= 7:
        raise ValueError("Sensitivity must be between 0.5 and 7 mV/V")
    if type(manual["filter"]) is not int or not 0 <= manual["filter"] <= 9:
        raise ValueError("Filter must be an integer from 0 to 9")
    if manual["anti_peak"] not in ("ON", "OFF"):
        raise ValueError("anti_peak must be ON or OFF")
    fixed = {"power_on_zero_g": 0, "zero_tracking": "NONE", "preset_tare_g": 0,
             "display_coefficient": 1, "protocol": "MODBUS-RTU", "baudrate": 9600,
             "data_bits": 8, "parity": "N", "stop_bits": 2, "response_delay_ms": 0}
    for key, value in fixed.items():
        if type(manual[key]) is not type(value) or manual[key] != value:
            raise ValueError(key + " must match this diagnostic baseline: " + str(value))
    full_scale = manual["full_scale_g"]
    if full_scale is not None:
        for key in ("max_display_g", "resettable_zero_g"):
            if manual[key] is not None and manual[key] > full_scale:
                raise ValueError(key + " cannot exceed full_scale_g")
    return profile


def load_profile(path):
    with Path(path).open(encoding="utf-8") as source:
        return validate_profile(json.load(source))


def write_json(path, data):
    # Preserve previous profiles/reports, including when a test is repeated.
    with Path(path).open("x", encoding="utf-8") as output:
        json.dump(data, output, indent=2, allow_nan=False)
        output.write("\n")


def checklist(profile):
    expected = profile["expected"]
    lines = ["FFA weighing transmitter setup plan (NO hardware writes)",
             "Targets below are NOT readings from the transmitter.",
             "Changing FS-tEO or SEnSib cancels real calibration. Do this before calibration.",
             "CALib / unit: g; CALib / diUiS: 0.5 g; SEriAL / Addr: 1."]
    for key, label in MANUAL_LABELS.items():
        value = profile["keypad_targets"][key]
        lines.append("- " + label + ": " + ("UNSET: inspect and record locally" if value is None else str(value)))
    lines.extend([
        "Expected raw firmware/type IDs: {}/{} (verify production compatibility, never guess).".format(
            expected["firmware_register"], expected["instrument_type_register"]),
        "The permanent lamp/frame counts toward physical cell capacity even after zeroing.",
        "Zero each assembled station separately; do not copy calibration/zero coefficients.",
        "Use a reliable reference and verify unloaded, loaded, reloaded, and power-cycled states.",
        "This tool does not send tare, zero, reference, save, reset, or parameter writes.",
        "Keep TLB_STATUS_MAP_VERIFIED=false until the installed map is independently verified.",
    ])
    return "\n".join(lines)


class DiagnosticClient:
    """Minimal Engine.IO polling client; only exposes the diagnostic read event."""

    def __init__(self, url, timeout=5):
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in ("", "/")):
            raise ValueError("Use an http(s) backend origin without credentials, path, or query")
        self.base = url.rstrip("/") + "/socket.io/?EIO=4&transport=polling"
        self.url = None
        self.timeout = timeout

    def request(self, url, payload=None):
        req = Request(url + "&" + urlencode({"t": time.monotonic_ns()}),
                      data=None if payload is None else payload.encode(),
                      headers={"Content-Type": "text/plain;charset=UTF-8"})
        with urlopen(req, timeout=self.timeout) as response:
            content = response.read(1_048_577)
        if len(content) > 1_048_576:
            raise ValueError("Backend response exceeds diagnostic size limit")
        return content.decode("utf-8")

    def receive(self, connecting=False):
        deadline = time.monotonic() + 2 * self.timeout
        while time.monotonic() < deadline:
            found = False
            result = None
            for packet in self.request(self.url).split("\x1e"):
                if packet == "2":
                    self.request(self.url, "3")
                elif packet.startswith("40") and connecting:
                    found = True
                elif packet.startswith("42") and not connecting:
                    event = json.loads(packet[2:])
                    if not isinstance(event, list) or len(event) < 2:
                        raise ValueError("Malformed Socket.IO event")
                    if event[0] == "scale_diagnostics_error":
                        raise RuntimeError("Backend diagnostic error: " + str(event[1]))
                    if event[0] == "scale_diagnostics":
                        found = True
                        result = event[1]
                elif packet == "1" or packet.startswith(("41", "44")):
                    raise RuntimeError("Backend disconnected or rejected the connection")
            if found:
                return result
        raise TimeoutError("No fresh diagnostic response; the backend may not support this event")

    def __enter__(self):
        hello = self.request(self.base)
        if not hello.startswith("0"):
            raise RuntimeError("Expected an Engine.IO v4 handshake")
        handshake = json.loads(hello[1:])
        if not isinstance(handshake, dict):
            raise ValueError("Malformed Engine.IO handshake")
        sid = handshake.get("sid")
        if not isinstance(sid, str) or not sid:
            raise ValueError("Missing Engine.IO session ID")
        self.url = self.base + "&" + urlencode({"sid": sid})
        try:
            self.request(self.url, "40")
            self.receive(connecting=True)
        except Exception:
            self.close()
            raise
        return self

    def read(self):
        self.request(self.url, '42["get_scale_diagnostics",{"mode":"weight"}]')
        return self.receive()

    def close(self):
        if self.url:
            try:
                self.request(self.url, "41\x1e1")
            except Exception:
                pass
            self.url = None

    def __exit__(self, *args):
        self.close()


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        raise ValueError("Diagnostic snapshot must be an object")
    words = snapshot.get("registers_40001_40014")
    if (not isinstance(words, list) or len(words) != 14 or words[5] is not None
            or any(type(word) is not int or not 0 <= word <= 65535
                   for index, word in enumerate(words) if index != 5)):
        raise ValueError("Invalid raw register block or write-only register was not skipped")
    if snapshot.get("interpretation") != "legacy":
        raise ValueError("Unsupported status interpretation; inspect firmware before use")
    for key in ("net", "gross", "division", "captured_at", "gross_minus_net"):
        if not number(snapshot.get(key)):
            raise ValueError("Invalid diagnostic numeric field: " + key)
    if (snapshot.get("status_raw") != words[6]
            or snapshot.get("firmware_register") != words[0]
            or snapshot.get("instrument_type_register") != words[1]
            or snapshot.get("division_register") != words[13]):
        raise ValueError("Decoded metadata disagrees with raw registers")
    if type(snapshot.get("stale")) is not bool or not isinstance(snapshot.get("faults"), list):
        raise ValueError("Missing freshness or fault metadata")
    return snapshot


def assess(profile, snapshots, expected_g, errors=()):
    problems = list(errors)
    target = profile["expected"]
    previous = None
    identity = None
    for index, d in enumerate(snapshots):
        validate_snapshot(d)
        reasons = []
        for key, value in target.items():
            if d.get(key) != value:
                reasons.append("{}: expected {}, got {}".format(key, value, d.get(key)))
        words, status = d["registers_40001_40014"], d["status_raw"]
        current_identity = tuple(words[:5])
        if identity is not None and current_identity != identity:
            reasons.append("Instrument identity changed during the check")
        identity = current_identity
        if previous is not None and d["captured_at"] <= previous:
            reasons.append("Diagnostic timestamp did not advance")
        previous = d["captured_at"]
        if d["stale"] or d["faults"] or status & 0x3F:
            reasons.append("Stale reading or transmitter fault")
        if not status & (1 << 11):
            reasons.append("Not stable under the legacy status map")
        if status & (1 << 10):
            reasons.append("NET mode/active tare; not automatically cleared")
        # Enforce the bench decimal mapping, not a division-count multiplier.
        raw_division, scale = SUPPORTED_DIVISIONS[target["division"]]
        if words[13] != raw_division:
            reasons.append("Raw division/unit differs from the {} g profile".format(target["division"]))
        else:
            for key, offset, sign in (("gross", 7, 7), ("net", 9, 8)):
                raw = (words[offset] << 16) | words[offset + 1]
                signed = raw - 2**32 if raw >= 2**31 else raw
                value = round(abs(signed) * (-scale if status & (1 << sign) else scale), 4)
                if abs(value - d[key]) > 0.0001:
                    reasons.append(key + " does not match raw display digits")
        tolerance = target["division"]
        if abs(d["gross"] - d["net"]) > tolerance:
            reasons.append("NET/GROSS mismatch")
        if any(abs(d[key] - expected_g) > tolerance for key in ("net", "gross")):
            reasons.append("Weight outside {:.1f} +/- {} g".format(expected_g, tolerance))
        problems.extend("sample {}: {}".format(index, reason) for reason in reasons)
    if len(snapshots) < 3:
        problems.append("At least three fresh readings are required")
    return {
        "schema_version": 1, "recorded_at": time.time(),
        "profile_sha256": hashlib.sha256(json.dumps(profile, sort_keys=True).encode()).hexdigest(),
        "profile": profile, "expected_g": expected_g,
        "automatic_check_passed": not problems, "problems": problems,
        "keypad_settings_verified": False, "production_ready": False,
        "limitations": ["Keypad targets are not readable through this diagnostic endpoint.",
                        "This is not proof of absolute accuracy or firmware compatibility.",
                        "Each station needs its own zero, reference, and power-cycle checks."],
        "snapshots": snapshots,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "init", "check"), nargs="?", default="plan")
    parser.add_argument("--profile", type=Path, help="profile to read, or new output path for init")
    parser.add_argument("--url", default="http://127.0.0.1:3030")
    parser.add_argument("--expected-g", type=float, help="0 for structure only, or known reference grams")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--interval", type=float, default=0.4)
    parser.add_argument("--report", type=Path, help="new JSON report; existing files are never overwritten")
    parser.add_argument("--ack-connection-outputs", action="store_true",
                        help="acknowledge that connecting turns the backend laser ON and flash OFF")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            if args.profile is None:
                raise ValueError("init requires --profile for a new file")
            write_json(args.profile, load_profile(PROFILE_PATH))
            print("Created profile: " + str(args.profile))
            print("Null targets must be inspected locally; this does not configure hardware.")
            return 0
        profile = load_profile(args.profile or PROFILE_PATH)
        if args.command == "plan":
            print(checklist(profile))
            return 0
        if not number(args.expected_g) or args.expected_g < 0:
            raise ValueError("check requires a finite, non-negative --expected-g")
        if not 3 <= args.samples <= 120 or not number(args.interval) or not 0.2 <= args.interval <= 10:
            raise ValueError("Use 3-120 samples and an interval of 0.2-10 seconds")
        if not args.ack_connection_outputs:
            raise ValueError("Clear the laser area, then pass --ack-connection-outputs; no connection opened")
        if args.report and args.report.exists():
            raise ValueError("Report already exists; choose a new path")
        samples, errors = [], []
        try:
            with DiagnosticClient(args.url) as client:
                for index in range(args.samples):
                    samples.append(validate_snapshot(client.read()))
                    if index + 1 < args.samples:
                        time.sleep(args.interval)
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        report = assess(profile, samples, args.expected_g, errors)
        if len(samples) != args.samples:
            report["automatic_check_passed"] = False
            report["problems"].append("Requested sample window was not completed")
        if args.report:
            write_json(args.report, report)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report["automatic_check_passed"] else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("tlb_setup: " + str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("tlb_setup: interrupted; no transmitter commands were sent", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())

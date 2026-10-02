#!/usr/bin/env python3
"""IOs.py keeps laser/flash working when GPIO 17 cannot be claimed."""
import sys
import types
import unittest

import _bootstrap  # noqa: F401 - adds project root to sys.path


class FakeOutput:
    def __init__(self, pin, pin_factory=None):
        self.pin = pin
        self.value = 0


class BusyBuzzer(FakeOutput):
    def __init__(self, pin, pin_factory=None):
        raise RuntimeError("GPIO busy")


def load_ios(buzzer_class):
    events = []
    gpiozero = types.ModuleType("gpiozero")
    gpiozero.LED = FakeOutput
    gpiozero.Buzzer = buzzer_class
    lgpio_pins = types.ModuleType("gpiozero.pins.lgpio")
    lgpio_pins.LGPIOFactory = lambda: object()
    logger = types.ModuleType("logger")
    logger.logEvent = lambda **kwargs: events.append(kwargs)
    sys.modules.update({"gpiozero": gpiozero, "gpiozero.pins": types.ModuleType("gpiozero.pins"),
                        "gpiozero.pins.lgpio": lgpio_pins, "logger": logger})
    sys.modules.pop("IOs", None)
    import IOs
    return IOs, events


class BuzzerFallbackTests(unittest.TestCase):
    def test_busy_buzzer_is_logged_and_ignored(self):
        ios, events = load_ios(BusyBuzzer)
        self.assertIsNone(ios.buzzer)
        self.assertEqual(events[0]["error_code"], "BUZZER_UNAVAILABLE")
        ios.set_buzzer(True)  # no exception
        ios.set_laser(1)
        self.assertEqual(ios.laser.value, 1)

    def test_available_buzzer_switches(self):
        ios, events = load_ios(FakeOutput)
        self.assertEqual(ios.buzzer.pin, 17)
        ios.set_buzzer(True)
        self.assertEqual(ios.buzzer.value, True)
        self.assertEqual(events, [])


if __name__ == "__main__":
    unittest.main()

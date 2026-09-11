#!/usr/bin/env python3
"""Register-level tests for TLB_MODBUS against a fake transmitter.

The fake exposes registers exactly as the TLB protocol manual v1.16 lays them
out (40001-based, weight as magnitude with the sign in the status register),
so these tests catch an off-by-one in the address map without hardware.

    python3 tests/test_tlb_registers.py
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------
# Fake minimalmodbus / pyserial, installed before TLB_MODBUS is imported.
# --------------------------------------------------------------------------

class FakeSerial:
    def __init__(self):
        self.baudrate = None
        self.bytesize = None
        self.parity = None
        self.stopbits = None
        self.timeout = None


class FakeInstrument:
    """A TLB with the register layout of the manual, indexed from 0."""

    #: shared across instances, keyed by slave address
    banks = {}

    def __init__(self, port, address):
        self.port = port
        self.address = address
        self.serial = FakeSerial()
        self.clear_buffers_before_each_transaction = False
        self.close_port_after_each_call = True
        self.commands = []
        FakeInstrument.banks.setdefault(address, self._fresh_bank())
        self.registers = FakeInstrument.banks[address]

    @staticmethod
    def _fresh_bank():
        bank = [0] * 80
        bank[0] = 116          # 40001 firmware version
        bank[13] = (1 << 8) | 9  # 40014: unit=grams(1), division index 9 -> 0.1
        return bank

    # -- helpers used by the tests -----------------------------------------

    def set_net(self, counts, negative=False):
        magnitude = abs(counts)
        self.registers[9] = (magnitude >> 16) & 0xFFFF
        self.registers[10] = magnitude & 0xFFFF
        self._set_status_bit(1 << 8, negative)

    def set_gross(self, counts, negative=False):
        magnitude = abs(counts)
        self.registers[7] = (magnitude >> 16) & 0xFFFF
        self.registers[8] = magnitude & 0xFFFF
        self._set_status_bit(1 << 7, negative)

    def set_peak(self, counts):
        self.registers[11] = (counts >> 16) & 0xFFFF
        self.registers[12] = counts & 0xFFFF

    def set_stable(self, value):
        self._set_status_bit(1 << 11, value)

    def set_fault(self, bit, value=True):
        self._set_status_bit(bit, value)

    def _set_status_bit(self, mask, value):
        if value:
            self.registers[6] |= mask
        else:
            self.registers[6] &= ~mask

    # -- minimalmodbus surface ---------------------------------------------

    def read_registers(self, address, count):
        if address + count > len(self.registers):
            raise ValueError("illegal data address")
        return list(self.registers[address:address + count])

    def write_register(self, address, value):
        if address == 5:
            self.commands.append(value)
            # Manual p.16: a successful save zeroes the sample weight pair.
            if value in (101, 106):
                self.registers[36] = 0
                self.registers[37] = 0
        else:
            self.registers[address] = value

    def write_registers(self, address, values):
        for offset, value in enumerate(values):
            self.registers[address + offset] = value


fake_minimalmodbus = types.ModuleType("minimalmodbus")
fake_minimalmodbus.Instrument = FakeInstrument
fake_minimalmodbus.BYTEORDER_BIG = 0
fake_minimalmodbus.BYTEORDER_LITTLE = 1
fake_minimalmodbus.BYTEORDER_BIG_SWAP = 2
fake_minimalmodbus.BYTEORDER_LITTLE_SWAP = 3

fake_serial = types.ModuleType("serial")
fake_serial.EIGHTBITS = 8
fake_serial.PARITY_NONE = "N"
fake_serial.STOPBITS_TWO = 2

sys.modules["minimalmodbus"] = fake_minimalmodbus
sys.modules["serial"] = fake_serial

import TLB_MODBUS as tlb  # noqa: E402


# --------------------------------------------------------------------------

FAILURES = []


def check(label, actual, expected):
    ok = actual == expected
    print("  {0} {1}: got {2!r}, expected {3!r}".format(
        "OK  " if ok else "FAIL", label, actual, expected))
    if not ok:
        FAILURES.append(label)


def reset():
    tlb._last_good.clear()
    tlb.isCalibrating = False
    for bank in FakeInstrument.banks.values():
        bank[:] = FakeInstrument._fresh_bank()


def test_addresses_match_the_manual():
    print("\nRegister addresses (manual number - 40001)")
    check("command 40006", tlb.REG_COMMAND, 40006 - 40001)
    check("status 40007", tlb.REG_STATUS, 40007 - 40001)
    check("gross H 40008", tlb.REG_GROSS_H, 40008 - 40001)
    check("net H 40010", tlb.REG_NET_H, 40010 - 40001)
    check("peak H 40012", tlb.REG_PEAK_H, 40012 - 40001)
    check("divisions 40014", tlb.REG_DIVISIONS, 40014 - 40001)
    check("sample weight 40037", tlb.REG_SAMPLE_WEIGHT, 40037 - 40001)


def test_reads_net_weight():
    print("\nNet weight decoding")
    reset()
    tlb.instrument.set_net(12345)      # 12345 counts x 0.1 = 1234.5 g
    tlb.instrument.set_gross(12800)
    tlb.instrument.set_stable(True)

    snapshot = tlb.readWeightSnapshot()
    check("net grams", snapshot["net"], 1234.5)
    check("gross grams", snapshot["gross"], 1280.0)
    check("counts", snapshot["counts_net"], 12345)
    check("stable", snapshot["stable"], True)
    check("faults", snapshot["faults"], [])
    check("readWeight()", tlb.readWeight(), 1234.5)


def test_peak_does_not_leak_into_the_reading():
    """The old address 10 + byteorder 3 returned NET_L + PEAK_H * 65536."""
    print("\nPeak register isolation (the +6553.6 jump)")
    reset()
    tlb.instrument.set_net(12345)
    tlb.instrument.set_peak(70000)     # peak above 65535 -> PEAK_H = 1

    old_style = (tlb.instrument.registers[10]
                 + tlb.instrument.registers[11] * 65536) / 10.0
    check("old code would report", old_style, 1234.5 + 6553.6)
    check("new code reports", tlb.readWeight(), 1234.5)


def test_net_weight_above_16_bits():
    print("\nWeights above 65535 counts")
    reset()
    tlb.instrument.set_net(120000)     # 12 kg at 0.1 g
    check("12000.0 g", tlb.readWeight(), 12000.0)


def test_negative_weight():
    print("\nNegative net weight (sign lives in status bit 8)")
    reset()
    tlb.instrument.set_net(43, negative=True)
    check("negative net", tlb.readWeight(), -4.3)

    reset()
    # Firmware that sends two's complement instead of magnitude.
    tlb.instrument.registers[9] = 0xFFFF
    tlb.instrument.registers[10] = 0xFFD5   # -43 as a signed 32-bit
    tlb.instrument.registers[6] |= (1 << 8)
    check("two's complement net", tlb.readWeight(), -4.3)


def test_faults_are_surfaced():
    print("\nFault bits")
    reset()
    tlb.instrument.set_net(1000)
    tlb.instrument.set_fault(tlb.ST_CELL_ERROR)
    tlb.instrument.set_fault(tlb.ST_ADC_FAILURE)
    check("faults", tlb.readWeightSnapshot()["faults"],
          ["LOAD_CELL_ERROR", "ADC_FAILURE"])


def test_division_is_read_from_the_instrument():
    print("\nDivision register 40014")
    reset()
    tlb._division = None
    check("division", tlb.getDivision(), 0.1)
    check("unit", tlb.getUnit(), "g")

    # Switch the instrument to 0.001 and confirm the scale follows.
    tlb._division = None
    tlb.instrument.registers[13] = (0 << 8) | 15   # kg, division 0.001
    tlb.instrument.set_net(12345)
    check("division after change", tlb.getDivision(), 0.001)
    check("rescaled reading", tlb.readWeight(), 12.345)
    tlb._division = None


def test_wtb_display_decimals():
    """Real WTB485: register 263 and raw 10000 mean 1000.0 g."""
    reset()
    try:
        for index, factor in ((0, 1), (4, 1), (6, 1), (7, 0.1),
                              (8, 0.1), (9, 0.1), (10, 0.01),
                              (11, 0.01), (13, 0.001), (16, 0.0001)):
            tlb._division = None
            tlb.instrument.registers[13] = (1 << 8) | index
            tlb.instrument.set_net(10000)
            tlb.instrument.set_gross(10000)
            tlb.instrument.set_peak(10000)
            snapshot = tlb.readWeightSnapshot()
            expected = round(10000 * factor, 4)
            check("net decimal index " + str(index), snapshot["net"], expected)
            check("gross decimal index " + str(index), snapshot["gross"], expected)
            check("peak decimal index " + str(index), tlb.readPeak(), expected)
            check("resolution retained", snapshot["division"], tlb._DIVISION_TABLE[index])
        tlb._division = None
        tlb.instrument.registers[13] = 263
        tlb.instrument.set_net(0)
        check("WTB zero", tlb.readWeight(), 0.0)
        tlb.instrument.set_net(25, negative=True)
        check("WTB negative", tlb.readWeight(), -2.5)
    finally:
        reset()
        tlb._division = None


def test_calibration_sequence():
    print("\nCalibration writes the manual's command sequence")
    reset()
    tlb._division = None
    tlb.instrument.set_stable(True)
    tlb.instrument.commands.clear()

    tlb.remote_calibration(1, "weight")
    tlb.remote_calibration(2, "weight")
    check("step 2 sends command 100", tlb.instrument.commands, [100])

    tlb.remote_calibration(3, "weight")
    check("step 3 sends command 101", tlb.instrument.commands, [100, 101])

    tlb.remote_calibration(4, "weight")
    check("step 4 sends command 99", tlb.instrument.commands, [100, 101, 99])
    check("isCalibrating cleared", tlb.isCalibrating, False)
    tlb._division = None


def test_calibration_rejects_a_silent_failure():
    print("\nCalibration verifies the instrument consumed the sample weight")
    reset()
    tlb._division = None
    tlb.instrument.set_stable(True)

    # Firmware that ignores command 101: the sample registers stay set.
    original = FakeInstrument.write_register

    def stubborn(self, address, value):
        if address == 5 and value in (101, 106):
            self.commands.append(value)
            return
        original(self, address, value)

    FakeInstrument.write_register = stubborn
    try:
        tlb.remote_calibration(3, "weight")
    except tlb.TLBCalibrationError as exc:
        check("raises TLBCalibrationError", "did not accept" in str(exc), True)
    else:
        check("raises TLBCalibrationError", False, True)
    finally:
        FakeInstrument.write_register = original
        tlb._division = None


def test_retry_then_stale_fallback():
    print("\nCommunication failure handling")
    reset()
    tlb.instrument.set_net(5000)
    tlb.readWeightSnapshot()           # prime the last-good cache

    original = FakeInstrument.read_registers

    def dead(self, address, count):
        raise IOError("no response")

    FakeInstrument.read_registers = dead
    try:
        snapshot = tlb.readWeightSnapshot()
        check("serves stale value", snapshot["net"], 500.0)
        check("marked not ok", snapshot["ok"], False)
        check("never stale-stable", snapshot["stable"], False)
    finally:
        FakeInstrument.read_registers = original


def main():
    print("=" * 68)
    print("TLB_MODBUS register tests (fake transmitter, manual v1.16)")
    print("=" * 68)

    for test in (
        test_addresses_match_the_manual,
        test_reads_net_weight,
        test_peak_does_not_leak_into_the_reading,
        test_net_weight_above_16_bits,
        test_negative_weight,
        test_faults_are_surfaced,
        test_division_is_read_from_the_instrument,
        test_wtb_display_decimals,
        test_calibration_sequence,
        test_calibration_rejects_a_silent_failure,
        test_retry_then_stale_fallback,
    ):
        test()

    print()
    print("=" * 68)
    if FAILURES:
        print("{0} FAILED: {1}".format(len(FAILURES), ", ".join(FAILURES)))
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

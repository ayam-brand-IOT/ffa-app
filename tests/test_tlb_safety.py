#!/usr/bin/env python3
"""Safety regressions for division decoding and non-idempotent commands."""

import os
import sys
import time


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

import test_tlb_registers as register_tests  # noqa: E402


tlb = register_tests.tlb
FakeInstrument = register_tests.FakeInstrument


def test_invalid_division_is_rejected():
    register_tests.reset()
    tlb._division = None
    tlb.instrument.registers[13] = (1 << 8) | 0xFF
    try:
        tlb.getDivision()
    except tlb.TLBCommunicationError:
        assert tlb._division is None
    else:
        raise AssertionError("Invalid division index was silently accepted")
    finally:
        tlb._division = None


def test_failed_division_read_is_retried_later():
    register_tests.reset()
    tlb._division = None
    original_read = tlb._read
    attempts = []

    def fail_first_division_read(inst, address, count):
        if address == tlb.REG_DIVISIONS:
            attempts.append(address)
            if len(attempts) == 1:
                raise tlb.TLBCommunicationError("temporary division read failure")
        return original_read(inst, address, count)

    tlb._read = fail_first_division_read
    try:
        try:
            tlb.getDivision()
        except tlb.TLBCommunicationError:
            pass
        else:
            raise AssertionError("The first failed division read must be surfaced")

        assert tlb._division is None
        assert tlb.getDivision() == 0.1
        assert len(attempts) == 2
    finally:
        tlb._read = original_read
        tlb._division = None


def test_command_is_not_retried_after_lost_response():
    register_tests.reset()
    original_write = FakeInstrument.write_register
    attempts = []

    def execute_then_lose_response(self, address, value):
        if address == tlb.REG_COMMAND:
            attempts.append(value)
            self.commands.append(value)
            raise IOError("response lost after command execution")
        return original_write(self, address, value)

    FakeInstrument.write_register = execute_then_lose_response
    try:
        try:
            tlb.setZero()
        except tlb.TLBCommunicationError:
            pass
        else:
            raise AssertionError("Lost command response should be surfaced")
        assert attempts == [tlb.CMD_ZERO]
    finally:
        FakeInstrument.write_register = original_write


def test_expired_stale_weight_is_not_served():
    register_tests.reset()
    tlb.instrument.set_net(5000)
    snapshot = tlb.readWeightSnapshot()
    tlb._last_good[tlb.instrument.address] = (
        time.monotonic() - tlb.STALE_MAX_AGE_SECONDS - 1,
        snapshot,
    )
    original_read = FakeInstrument.read_registers

    def dead_bus(self, address, count):
        raise IOError("no response")

    FakeInstrument.read_registers = dead_bus
    try:
        try:
            tlb.readWeightSnapshot()
        except tlb.TLBCommunicationError:
            pass
        else:
            raise AssertionError("An expired stale weight must not be served")
    finally:
        FakeInstrument.read_registers = original_read


def main():
    test_invalid_division_is_rejected()
    test_failed_division_read_is_retried_later()
    test_command_is_not_retried_after_lost_response()
    test_expired_stale_weight_is_not_served()
    print("TLB safety tests passed")


if __name__ == "__main__":
    main()

"""
TLB_MODBUS.py - Laumas TLB weight transmitter over Modbus-RTU (RS485).

Register map and semantics follow the "TLB COMMUNICATION PROTOCOLS" user
manual v1.16, section MODBUS-RTU PROTOCOL (pages 9-19).

REGISTER NUMBERING
    The manual lists registers as 40001-based.  minimalmodbus addresses them
    from 0, so every address here is (manual number - 40001):

        40006 COMMAND         -> 5
        40007 STATUS          -> 6
        40008/40009 GROSS H/L -> 7 / 8
        40010/40011 NET   H/L -> 9 / 10
        40012/40013 PEAK  H/L -> 11 / 12
        40014 DIVISIONS/UNITS -> 13
        40037/40038 SAMPLE W  -> 36 / 37

    The previous version read NET from address 10 and GROSS from address 8 -
    the LOW half of the *preceding* pair.  Reading a long from address 10
    returns (NET L, PEAK H), which equals the net weight only while both the
    weight and the recorded peak stay under 65535 divisions.  Once the peak
    passed 65535 every reading jumped by exactly 65536 divisions and stayed
    there: the "the scale decalibrates itself" symptom.

SIGN
    The weight registers carry the MAGNITUDE; the sign lives in the status
    register (bit 7 gross, bit 8 net).  _apply_sign() tolerates both a
    magnitude-only device and one that already sends two's complement.

SCALE
    The displayed value is (raw counts x division).  The division is read from
    register 40014 instead of being hard-coded, so changing it on the
    instrument keypad no longer silently rescales every reading.

LOCKING
    _lock is created at import time, which under the current main.py runs
    BEFORE eventlet.monkey_patch() - so it is a real OS lock, not a green one.
    Blocking on it from a greenlet blocks the whole hub, and sleeping while
    holding it deadlocks the process outright.  Therefore: the lock is held
    for exactly one Modbus transaction and never across a sleep.
"""

import os
import time
from threading import Lock

import serial
import minimalmodbus

from logger import logEvent

# ============================= DEVICE ADDRESSES =============================

SLAVE_ID = 1
BELLY_TEST_ID = 2

# ============================= MODBUS REGISTERS =============================
# manual number - 40001

REG_COMMAND = 5         # 40006  W   command register
REG_STATUS = 6          # 40007  R   status register
REG_GROSS_H = 7         # 40008  R   gross weight, high word
REG_NET_H = 9           # 40010  R   net weight, high word
REG_PEAK_H = 11         # 40012  R   peak weight, high word
REG_DIVISIONS = 13      # 40014  R   divisions + unit of measure
REG_SAMPLE_WEIGHT = 36  # 40037  R/W sample weight for calibration, high word

# One block read covers status + gross + net (40007..40011).
_BLOCK_START = REG_STATUS
_BLOCK_COUNT = 5        # status, gross_h, gross_l, net_h, net_l

# ============================= COMMAND REGISTER =============================
# Manual page 15, "POSSIBLE COMMANDS TO BE SENT TO THE COMMAND REGISTER".

CMD_TARE_SEMI = 7       # semi-automatic tare (show net weight)
CMD_ZERO = 8            # semi-automatic zero
CMD_TARE_DISABLE = 9    # semi-automatic tare disabling (show gross weight)
CMD_SAVE_EEPROM = 99    # save data in EEPROM
CMD_CALIB_TARE = 100    # tare weight zero setting for calibration
CMD_SAVE_FIRST = 101    # save first sample weight (drops previous points)
CMD_CALIB_CANCEL = 104  # cancel real calibration, back to theoretical
CMD_SAVE_NEXT = 106     # add sample weight (keeps previous points)

# ============================= STATUS REGISTER ==============================
# Manual page 13.

ST_CELL_ERROR = 1 << 0
ST_ADC_FAILURE = 1 << 1
ST_MAX_EXCEEDED = 1 << 2     # max weight exceeded by 9 divisions
ST_GROSS_OVER_110 = 1 << 3   # gross > 110% of full scale
ST_GROSS_OUT_RANGE = 1 << 4  # gross beyond +/-999999
ST_NET_OUT_RANGE = 1 << 5    # net beyond +/-999999
ST_GROSS_NEGATIVE = 1 << 7
ST_NET_NEGATIVE = 1 << 8
ST_NET_MODE = 1 << 10
ST_STABLE = 1 << 11
ST_NEAR_ZERO = 1 << 12       # within +/- 1/4 division around zero

_FAULT_NAMES = (
    (ST_CELL_ERROR, "LOAD_CELL_ERROR"),
    (ST_ADC_FAILURE, "ADC_FAILURE"),
    (ST_MAX_EXCEEDED, "MAX_WEIGHT_EXCEEDED"),
    (ST_GROSS_OVER_110, "GROSS_OVER_110_PCT"),
    (ST_GROSS_OUT_RANGE, "GROSS_OUT_OF_RANGE"),
    (ST_NET_OUT_RANGE, "NET_OUT_OF_RANGE"),
)

# ============================= DIVISION TABLE ===============================
# Manual page 14: low byte of register 40014 indexes this table.

_DIVISION_TABLE = (
    100.0, 50.0, 20.0, 10.0, 5.0, 2.0, 1.0,   # 0-6
    0.5, 0.2, 0.1,                            # 7-9
    0.05, 0.02, 0.01,                         # 10-12
    0.005, 0.002, 0.001,                      # 13-15
    0.0005, 0.0002, 0.0001,                   # 16-18
)

_UNIT_NAMES = (
    "kg", "g", "t", "lb", "N", "l", "bar",
    "atm", "pcs", "Nm", "kgm", "other",
)

# The division every historical reading and every stored sample assumes.
EXPECTED_DIVISION = 0.1

# ============================= SERIAL SETTINGS ==============================

PORT = os.getenv("TLB_PORT", "/dev/ttyUSB0")
BAUDRATE = int(os.getenv("TLB_BAUDRATE", "9600"))
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_TWO

# minimalmodbus defaults to 0.05 s, which at 9600 baud 8N2 is barely longer
# than the frame itself (17 bytes x 11 bits = ~19.5 ms) plus the instrument's
# own configurable response delay.  Any hiccup then raises NoResponseError.
TIMEOUT = float(os.getenv("TLB_TIMEOUT", "0.2"))
RETRIES = int(os.getenv("TLB_RETRIES", "2"))
RETRY_DELAY = float(os.getenv("TLB_RETRY_DELAY", "0.02"))

# Nominal sample weight used by the guided calibration, in grams.
CALIB_SAMPLE_GRAMS = float(os.getenv("TLB_CALIB_SAMPLE_GRAMS", "1000.0"))

# ============================= MODULE STATE =================================

__WEIGHT_MODE = 0
__TENSION_MODE = 1

READING_MODE = __WEIGHT_MODE
isCalibrating = False

# Serialises access to the shared serial port (minimalmodbus is not
# thread-safe and both instruments share one physical port).
# Held for one transaction only - see LOCKING in the module docstring.
_lock = Lock()

# Cached division/unit, read once from the instrument.
_division = None
_unit = None

# Last good reading per slave, so a single dropped frame does not surface as a
# zero or an exception in the UI.
_last_good = {}


class TLBCommunicationError(RuntimeError):
    """The transmitter did not answer after every retry."""


class TLBCalibrationError(RuntimeError):
    """The instrument rejected or ignored a calibration step."""


# ============================= INSTRUMENTS ==================================

def _build(slave_id):
    inst = minimalmodbus.Instrument(PORT, slave_id)
    inst.serial.baudrate = BAUDRATE
    inst.serial.bytesize = BYTESIZE
    inst.serial.parity = PARITY
    inst.serial.stopbits = STOPBITS
    inst.serial.timeout = TIMEOUT
    inst.clear_buffers_before_each_transaction = True
    inst.close_port_after_each_call = False
    return inst


# Note: minimalmodbus caches serial ports by name, so both instruments share
# one pyserial object.  _lock serialises every transaction across both.
instrument = _build(SLAVE_ID)
instrument2 = _build(BELLY_TEST_ID)


def _for(is_belly):
    return instrument2 if is_belly else instrument


# ============================= LOW LEVEL ====================================

def _transact(description, fn, *args):
    """Run one Modbus transaction under _lock, retrying on failure.

    The lock is taken and released inside the loop so the back-off sleep never
    happens while holding it.
    """
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            with _lock:
                return fn(*args)
        except Exception as exc:      # noqa: BLE001 - pyserial/minimalmodbus
            last_error = exc
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    raise TLBCommunicationError(
        "{0} failed after {1} attempts: {2}".format(
            description, RETRIES + 1, last_error)
    ) from last_error


def _read(inst, address, count):
    return _transact(
        "read {0}x{1} from slave {2}".format(count, address, inst.address),
        inst.read_registers, address, count)


def _write(inst, address, value):
    return _transact(
        "write {0} to register {1} of slave {2}".format(value, address, inst.address),
        inst.write_register, address, value)


def _write_many(inst, address, values):
    return _transact(
        "write {0} to registers from {1} of slave {2}".format(
            values, address, inst.address),
        inst.write_registers, address, values)


def _apply_sign(high, low, negative):
    """Combine the H/L pair into a signed count.

    The manual documents the sign as a status bit, implying the registers hold
    a magnitude.  Some firmware revisions send two's complement instead, so
    normalise to a magnitude first and then apply the status bit.  Both
    layouts end up with the same value.
    """
    raw = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
    if raw >= 0x80000000:
        raw -= 0x100000000
    magnitude = abs(raw)
    return -magnitude if negative else magnitude


def _faults(status):
    return [name for bit, name in _FAULT_NAMES if status & bit]


# ============================= DIVISION / SCALE =============================

def _load_division():
    """Read register 40014 once and cache the division + unit."""
    global _division, _unit
    if _division is not None:
        return _division

    try:
        raw = _read(instrument, REG_DIVISIONS, 1)[0]
    except TLBCommunicationError as exc:
        _division = EXPECTED_DIVISION
        logEvent(
            etapa="SYSTEM", status="WARNING",
            error_code="TLB_DIVISION_READ_FAILED", error_msg=str(exc),
            additional_data={"fallback_division": EXPECTED_DIVISION},
        )
        return _division

    division_index = raw & 0xFF
    unit_index = (raw >> 8) & 0xFF

    _division = (_DIVISION_TABLE[division_index]
                 if division_index < len(_DIVISION_TABLE) else EXPECTED_DIVISION)
    _unit = _UNIT_NAMES[unit_index] if unit_index < len(_UNIT_NAMES) else "?"

    logEvent(
        etapa="SYSTEM",
        status="INFO" if _division == EXPECTED_DIVISION else "WARNING",
        additional_data={
            "event_type": "tlb_division",
            "division": _division,
            "unit": _unit,
            "expected_division": EXPECTED_DIVISION,
            "raw_register_40014": raw,
        },
    )
    return _division


def getDivision():
    """Value of one count as configured on the instrument."""
    return _load_division()


def getUnit():
    _load_division()
    return _unit


# ============================= READING ======================================

def _idle_snapshot():
    return {
        "net": 0.0, "gross": 0.0, "counts_net": 0, "counts_gross": 0,
        "stable": False, "near_zero": False, "net_mode": False,
        "faults": [], "status": 0,
        "division": _division or EXPECTED_DIVISION,
        "ok": False, "calibrating": True,
    }


def _snapshot(is_belly=False):
    """Status + gross + net in a single Modbus transaction.

    isCalibrating is checked without the lock on purpose: it is a plain bool
    read, and taking the lock here would let a calibration step stall the
    weight polling greenlet.
    """
    if isCalibrating:
        return _idle_snapshot()

    inst = _for(is_belly)
    division = _load_division()

    try:
        status, gross_h, gross_l, net_h, net_l = _read(
            inst, _BLOCK_START, _BLOCK_COUNT)
    except TLBCommunicationError as exc:
        stale = _last_good.get(inst.address)
        logEvent(
            etapa="SYSTEM", status="ERROR",
            error_code="TLB_READ_ERROR", error_msg=str(exc),
            additional_data={"slave": inst.address,
                             "served_stale": stale is not None},
        )
        if stale is None:
            raise
        degraded = dict(stale)
        degraded["ok"] = False
        degraded["stable"] = False
        return degraded

    gross = _apply_sign(gross_h, gross_l, status & ST_GROSS_NEGATIVE)
    net = _apply_sign(net_h, net_l, status & ST_NET_NEGATIVE)

    snapshot = {
        "net": round(net * division, 4),
        "gross": round(gross * division, 4),
        "counts_net": net,
        "counts_gross": gross,
        "stable": bool(status & ST_STABLE),
        "near_zero": bool(status & ST_NEAR_ZERO),
        "net_mode": bool(status & ST_NET_MODE),
        "faults": _faults(status),
        "status": status,
        "division": division,
        "ok": True,
    }
    _last_good[inst.address] = snapshot
    return snapshot


def readWeightSnapshot():
    """Full net-weight reading: value, stability and instrument faults."""
    return _snapshot(is_belly=False)


def readTensionSnapshot():
    """Full belly-tension reading."""
    return _snapshot(is_belly=True)


def readWeight():
    """Net weight in the instrument's unit (grams with the default division)."""
    return _snapshot(is_belly=False)["net"]


def readTenstion():
    """Belly test tension. Name kept for backwards compatibility."""
    return _snapshot(is_belly=True)["net"]


def readGross():
    return _snapshot(is_belly=False)["gross"]


def isStable(is_belly=False):
    """Weight stability as reported by the instrument (status bit 11)."""
    return _snapshot(is_belly)["stable"]


def readPeak(is_belly=False):
    """Peak weight held by the instrument. Useful for diagnostics."""
    division = _load_division()
    high, low = _read(_for(is_belly), REG_PEAK_H, 2)
    return round(_apply_sign(high, low, False) * division, 4)


# ============================= MODE =========================================

def isOnTensionMode():
    return READING_MODE == __TENSION_MODE


def enterToTensionTest():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __TENSION_MODE


def enterToWeightMode():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __WEIGHT_MODE


# ============================= ZERO / TARE ==================================

def setZero(is_belly=False):
    """Semi-automatic zero: corrects small drift of the gross zero."""
    print("Setting to Zero")
    _write(_for(is_belly), REG_COMMAND, CMD_ZERO)
    logEvent(etapa="CALIBRATION", status="SUCCESS",
             additional_data={"action": "set_zero", "belly": bool(is_belly)})


def setTare(is_belly=False):
    """Semi-automatic tare: whatever sits on the scale RIGHT NOW becomes 0.

    Only call this deliberately, with the scale empty.  Calling it on view
    mount was taring out fish, water and ice and looked like a decalibration.
    """
    print("Tare belly" if is_belly else "Tare")
    _write(_for(is_belly), REG_COMMAND, CMD_TARE_SEMI)
    logEvent(etapa="CALIBRATION", status="SUCCESS",
             additional_data={"action": "set_tare", "belly": bool(is_belly)})


def clearTare(is_belly=False):
    """Disable the semi-automatic tare and go back to displaying gross."""
    _write(_for(is_belly), REG_COMMAND, CMD_TARE_DISABLE)


def setCalibrating(value: bool):
    global isCalibrating
    isCalibrating = bool(value)


# ============================= CALIBRATION ==================================

def _sample_counts(sample_grams, division):
    """Sample weight expressed in divisions, per manual page 16."""
    counts = int(round(sample_grams / division))
    if counts <= 0:
        raise TLBCalibrationError(
            "sample weight {0} g is below one division ({1})".format(
                sample_grams, division))
    if counts > 0x7FFFFFFF:
        raise TLBCalibrationError("sample weight does not fit in 32 bits")
    return counts


def _write_sample_weight(inst, counts):
    _write_many(inst, REG_SAMPLE_WEIGHT,
                [(counts >> 16) & 0xFFFF, counts & 0xFFFF])


def _verify_sample_consumed(inst):
    """Manual page 16: on success the instrument zeroes 40037/40038."""
    time.sleep(0.15)
    high, low = _read(inst, REG_SAMPLE_WEIGHT, 2)
    if high or low:
        raise TLBCalibrationError(
            "instrument did not accept the sample weight "
            "(40037={0}, 40038={1} still set)".format(high, low))


def _wait_for_stability(inst, timeout=4.0):
    """Poll status bit 11 until the weight settles. Never sleeps under _lock."""
    deadline = time.time() + timeout
    last_status = 0
    while time.time() < deadline:
        last_status = _read(inst, REG_STATUS, 1)[0]
        faults = _faults(last_status)
        if faults:
            raise TLBCalibrationError("instrument reports " + ", ".join(faults))
        if last_status & ST_STABLE:
            return
        time.sleep(0.1)
    raise TLBCalibrationError(
        "weight never stabilised within {0}s (status=0x{1:04X})".format(
            timeout, last_status))


def remote_calibration(step, args):
    """Guided calibration driven by calibrateScale.vue (steps 1..4).

    1  start           - check the instrument is healthy, no write
    2  empty container - command 100, tare weight zero setting
    3  known sample    - write 40037/40038 then command 101, then verify
    4  finish          - command 99, persist to EEPROM
    """
    global isCalibrating
    is_belly = (args == "belly")
    inst = _for(is_belly)
    division = _load_division()

    if step == 1:
        status = _read(inst, REG_STATUS, 1)[0]
        faults = _faults(status)
        if faults:
            raise TLBCalibrationError(
                "cannot calibrate, instrument reports " + ", ".join(faults))
        print("Calibration start, status 0x{0:04X}".format(status))

    elif step == 2:
        print("Tare weight zero setting")
        _wait_for_stability(inst)
        _write(inst, REG_COMMAND, CMD_CALIB_TARE)

    elif step == 3:
        counts = _sample_counts(CALIB_SAMPLE_GRAMS, division)
        print("Saving calibration point: {0} g = {1} counts".format(
            CALIB_SAMPLE_GRAMS, counts))
        _wait_for_stability(inst)
        _write_sample_weight(inst, counts)
        _write(inst, REG_COMMAND, CMD_SAVE_FIRST)
        _verify_sample_consumed(inst)

    elif step == 4:
        print("Persisting calibration to EEPROM")
        _write(inst, REG_COMMAND, CMD_SAVE_EEPROM)
        isCalibrating = False

    else:
        raise TLBCalibrationError("unknown calibration step {0}".format(step))


def add_calibration_point(sample_grams, is_belly=False):
    """Add a linearisation point (command 106). Up to 8 points, manual p.16."""
    inst = _for(is_belly)
    counts = _sample_counts(sample_grams, _load_division())
    _wait_for_stability(inst)
    _write_sample_weight(inst, counts)
    _write(inst, REG_COMMAND, CMD_SAVE_NEXT)
    _verify_sample_consumed(inst)


def cancel_calibration(is_belly=False):
    """Drop the real calibration and fall back to the theoretical one."""
    _write(_for(is_belly), REG_COMMAND, CMD_CALIB_CANCEL)


def physical_calibration():
    """Interactive console calibration, for bench work over SSH."""
    division = getDivision()
    print("Division configured on the instrument: {0} ({1})".format(
        division, getUnit()))

    input("1. Empty the scale and press Enter to zero the tare weight: ")
    _wait_for_stability(instrument)
    _write(instrument, REG_COMMAND, CMD_CALIB_TARE)

    input("2. Place the {0} g calibration weight and press Enter: ".format(
        CALIB_SAMPLE_GRAMS))
    _wait_for_stability(instrument)
    _write_sample_weight(instrument, _sample_counts(CALIB_SAMPLE_GRAMS, division))
    _write(instrument, REG_COMMAND, CMD_SAVE_FIRST)
    _verify_sample_consumed(instrument)
    print("   first point saved")

    while input("Add another calibration point? (y/n): ").strip().lower() == "y":
        grams = float(input("   Sample weight in grams: "))
        input("   Place it on the scale and press Enter: ")
        add_calibration_point(grams)
        print("   point saved")

    _write(instrument, REG_COMMAND, CMD_SAVE_EEPROM)
    print("Calibration stored in EEPROM.")

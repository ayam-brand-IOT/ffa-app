"""
scale_trace.py - record weight readings to CSV for offline filter tuning.

Passive: it only writes down what the poller already read, it never talks to
the transmitter. Empty, steady readings are skipped so a shift stays small;
the last PRE_ROLL empty readings are written when a load arrives, so each
placement starts from a known zero. Files rotate at SCALE_TRACE_MAX_MB.

    SCALE_TRACE=0              disable
    SCALE_TRACE_DIR=traces     relative to the app folder (mounted on the Pi)
"""

import csv
import os
import time
from collections import deque
from datetime import datetime

ENABLED = os.getenv("SCALE_TRACE", "1") not in ("0", "false", "False", "")
TRACE_DIR = os.getenv("SCALE_TRACE_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "traces"))
MAX_BYTES = int(float(os.getenv("SCALE_TRACE_MAX_MB", "20")) * 1024 * 1024)
LOADED_GRAMS = 5.0
PRE_ROLL = 10
# A load counts as gone after this many empty readings in a row.
POST_ROLL = 10

FIELDS = ("time", "t", "net", "gross", "stable", "ok", "stale", "faults",
          "division", "ready", "ready_value")


class ScaleTrace:
    def __init__(self, directory=TRACE_DIR, max_bytes=MAX_BYTES, enabled=ENABLED):
        self.directory = directory
        self.max_bytes = max_bytes
        self.enabled = enabled
        self._pre = deque(maxlen=PRE_ROLL)
        self._empty_run = POST_ROLL
        self._file = None
        self._writer = None
        self._seq = 0

    def record(self, snapshot, ready, ready_value):
        if not self.enabled:
            return
        try:
            self._record(snapshot, ready, ready_value)
        except OSError as exc:
            # A full or read-only disk must never stop weighing.
            print(f"scale trace disabled: {exc}")
            self.enabled = False

    def _record(self, snapshot, ready, ready_value):
        row = {
            "time": datetime.now().isoformat(timespec="milliseconds"),
            "t": f"{time.monotonic():.3f}",
            "net": snapshot.get("net"),
            "gross": snapshot.get("gross"),
            "stable": int(bool(snapshot.get("stable"))),
            "ok": int(bool(snapshot.get("ok", True))),
            "stale": int(bool(snapshot.get("stale"))),
            "faults": "|".join(snapshot.get("faults") or ()),
            "division": snapshot.get("division"),
            "ready": int(bool(ready)),
            "ready_value": "" if ready_value is None else ready_value,
        }
        loaded = abs(snapshot.get("net") or 0.0) >= LOADED_GRAMS
        self._empty_run = 0 if loaded else self._empty_run + 1
        if self._empty_run > POST_ROLL:
            self._pre.append(row)
            return
        writer = self._open()
        while self._pre:
            writer.writerow(self._pre.popleft())
        writer.writerow(row)
        self._file.flush()

    def _open(self):
        if self._file is not None and self._file.tell() < self.max_bytes:
            return self._writer
        if self._file is not None:
            self._file.close()
        os.makedirs(self.directory, exist_ok=True)
        self._seq += 1
        name = datetime.now().strftime(f"scale-%Y%m%dT%H%M%S-{self._seq}.csv")
        self._file = open(os.path.join(self.directory, name), "w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDS)
        self._writer.writeheader()
        return self._writer

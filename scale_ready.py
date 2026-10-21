"""
scale_ready.py - "weight confirmed" detection for the capture screen.

The transmitter's stability bit is not a reliable signal on its own. It can
flicker on while a load is still being settled by hand (bench: stable at
764.5 g, then 790.5 g), and with FiLtEr 3 it flickers off whenever the weight
sits on the edge between two divisions (812.5 / 813.0), which used to restart
the count until HomeView gave up. So readiness is decided here: the last
READY_SAMPLES readings with a load on the scale must agree within
READY_TOLERANCE divisions, and the transmitter must have called at least one
of them stable. The value is their median, rounded to the division, so a
reading toggling between two divisions still gives one fixed weight.
HomeView captures that value and the buzzer announces it, so the beep and the
stored weight always match.
"""

import os
from statistics import median

READY_SAMPLES = int(os.getenv("SCALE_READY_SAMPLES", "5"))
# Spread allowed inside the window, in divisions.
READY_TOLERANCE = float(os.getenv("SCALE_READY_TOLERANCE_DIVISIONS", "2"))
# Below this net weight the scale counts as empty: no beep, and the next load
# is announced even if it weighs the same as the previous one.
READY_MIN_GRAMS = float(os.getenv("SCALE_READY_MIN_GRAMS", "20"))


class ReadyDetector:
    def __init__(self, samples=READY_SAMPLES, min_grams=READY_MIN_GRAMS,
                 tolerance=READY_TOLERANCE):
        self.samples = max(1, int(samples))
        self.min_grams = float(min_grams)
        self.tolerance = max(1.0, float(tolerance))
        self.reset()

    def reset(self):
        self._window = []
        self._announced = None

    def update(self, snapshot):
        """Feed one poller snapshot; return (ready, value, announce).

        announce is True once per load: when a new value becomes ready, not
        again while the same load keeps toggling between divisions.
        """
        net = snapshot.get("net") or 0.0
        division = snapshot.get("division") or 1.0
        loaded = abs(net) >= self.min_grams
        usable = (loaded and snapshot.get("ok", True)
                  and not snapshot.get("stale") and not snapshot.get("faults"))
        if not loaded:
            self._announced = None
        if not usable:
            self._window.clear()
            return False, None, False

        self._window.append((net, bool(snapshot.get("stable"))))
        del self._window[:-self.samples]
        values = [v for v, _ in self._window]
        band = self.tolerance * division
        if (len(values) < self.samples
                or max(values) - min(values) > band
                or not any(stable for _, stable in self._window)):
            return False, None, False

        value = round(median(values) / division) * division
        announce = (self._announced is None
                    or abs(value - self._announced) > band)
        if announce:
            self._announced = value
        return True, value, announce

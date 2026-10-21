"""
scale_ready.py - "weight confirmed" detection for the capture screen.

Recorded on the production station (traces/, 2026-10-21, FiLtEr 3, 1 g):

- The settled value is clean: it holds the same gram, or toggles between two
  neighbouring grams when the load sits on a division edge (221/222 g).
- The transmitter's stability bit trails the settled value by ~1.1 s, and on
  a division edge it may never come on (221/222 g: 11 s, never stable).
- After a stable weight, the first new value is frozen for ~0.8 s (6 polls,
  likely the anti-peak filter). Those frozen readings agree perfectly, so
  agreement alone would confirm a weight the load never had.

So a weight is ready when either
- the last READY_SAMPLES loaded readings agree within READY_TOLERANCE
  divisions and the transmitter marked one of them stable, or
- the last READY_UNSTABLE_SAMPLES readings agree within the same tolerance
  without the bit: longer than the frozen hold, short enough that a reading
  on a division edge is confirmed in ~1 s instead of never.

The value is the median of the agreeing readings, rounded to the division.
HomeView captures that value and the buzzer announces it, so the beep and
the stored weight always match.
"""

import os
from statistics import median

READY_SAMPLES = int(os.getenv("SCALE_READY_SAMPLES", "4"))
# Must stay longer than the transmitter's frozen hold (6 polls at 0.137 s).
READY_UNSTABLE_SAMPLES = int(os.getenv("SCALE_READY_UNSTABLE_SAMPLES", "8"))
# Spread allowed inside the window, in divisions.
READY_TOLERANCE = float(os.getenv("SCALE_READY_TOLERANCE_DIVISIONS", "1"))
# Below this net weight the scale counts as empty: no beep, and the next load
# is announced even if it weighs the same as the previous one.
READY_MIN_GRAMS = float(os.getenv("SCALE_READY_MIN_GRAMS", "20"))


class ReadyDetector:
    def __init__(self, samples=READY_SAMPLES, min_grams=READY_MIN_GRAMS,
                 tolerance=READY_TOLERANCE, unstable_samples=READY_UNSTABLE_SAMPLES):
        self.samples = max(1, int(samples))
        self.unstable_samples = max(self.samples, int(unstable_samples))
        self.min_grams = float(min_grams)
        self.tolerance = max(1.0, float(tolerance))
        self.reset()

    def reset(self):
        self._window = []
        self._announced = None

    def _agreeing(self, count, band):
        if len(self._window) < count:
            return None
        recent = self._window[-count:]
        values = [v for v, _ in recent]
        return recent if max(values) - min(values) <= band else None

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
        del self._window[:-self.unstable_samples]
        band = self.tolerance * division
        recent = self._agreeing(self.samples, band)
        if recent is None or not any(stable for _, stable in recent):
            recent = self._agreeing(self.unstable_samples, band)
        if recent is None:
            return False, None, False

        value = round(median(v for v, _ in recent) / division) * division
        announce = (self._announced is None
                    or abs(value - self._announced) > band)
        if announce:
            self._announced = value
        return True, value, announce

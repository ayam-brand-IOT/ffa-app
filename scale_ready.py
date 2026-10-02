"""
scale_ready.py - "weight confirmed" detection for the capture screen.

The transmitter's stability bit alone can flicker on while a load is still
being settled by hand (bench: stable at 764.5 g, then 790.5 g). A reading is
ready only after READY_SAMPLES consecutive stable readings agree within one
division with a load on the scale. HomeView captures that value and the
buzzer announces it, so the beep and the stored weight always match.
"""

import os

READY_SAMPLES = int(os.getenv("SCALE_READY_SAMPLES", "3"))
# Below this net weight the scale counts as empty: no beep, and the next load
# is announced even if it weighs the same as the previous one.
READY_MIN_GRAMS = float(os.getenv("SCALE_READY_MIN_GRAMS", "20"))


class ReadyDetector:
    def __init__(self, samples=READY_SAMPLES, min_grams=READY_MIN_GRAMS):
        self.samples = max(1, int(samples))
        self.min_grams = float(min_grams)
        self.reset()

    def reset(self):
        self._window = []
        self._announced = None

    def update(self, snapshot):
        """Feed one poller snapshot; return (ready, value, announce).

        announce is True once per load: when a new value becomes ready, not
        again while the same load flickers in and out of stability.
        """
        net = snapshot.get("net") or 0.0
        division = snapshot.get("division") or 1.0
        loaded = abs(net) >= self.min_grams
        usable = (loaded and snapshot.get("stable") and snapshot.get("ok", True)
                  and not snapshot.get("stale") and not snapshot.get("faults"))
        if not loaded:
            self._announced = None
        if not usable:
            self._window.clear()
            return False, None, False

        self._window.append(net)
        del self._window[:-self.samples]
        if (len(self._window) < self.samples
                or max(self._window) - min(self._window) > division):
            return False, None, False

        value = self._window[-1]
        announce = (self._announced is None
                    or abs(value - self._announced) > division)
        if announce:
            self._announced = value
        return True, value, announce

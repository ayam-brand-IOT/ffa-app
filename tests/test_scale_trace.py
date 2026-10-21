#!/usr/bin/env python3
"""Weight trace recorder: what it writes and what it skips."""
import csv
import glob
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from scale_trace import POST_ROLL, PRE_ROLL, ScaleTrace


def reading(net, stable=True):
    return {"net": net, "gross": net, "stable": stable, "division": 1.0,
            "ok": True, "stale": False, "faults": []}


class ScaleTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def rows(self):
        rows = []
        for path in sorted(glob.glob(os.path.join(self.tmp.name, "*.csv"))):
            with open(path, newline="") as f:
                rows.extend(csv.DictReader(f))
        return rows

    def test_empty_scale_writes_nothing(self):
        trace = ScaleTrace(self.tmp.name, max_bytes=10**6, enabled=True)
        for _ in range(50):
            trace.record(reading(0.0), False, None)
        self.assertEqual(self.rows(), [])

    def test_placement_keeps_pre_and_post_roll(self):
        trace = ScaleTrace(self.tmp.name, max_bytes=10**6, enabled=True)
        for _ in range(30):
            trace.record(reading(0.0), False, None)
        for _ in range(5):
            trace.record(reading(812.0), True, 812.0)
        for _ in range(30):
            trace.record(reading(0.0), False, None)
        nets = [float(r["net"]) for r in self.rows()]
        self.assertEqual(nets, [0.0] * PRE_ROLL + [812.0] * 5 + [0.0] * POST_ROLL)
        self.assertEqual(self.rows()[PRE_ROLL]["ready_value"], "812.0")

    def test_rotates_at_max_size(self):
        trace = ScaleTrace(self.tmp.name, max_bytes=500, enabled=True)
        for i in range(40):
            trace.record(reading(100.0 + i), True, None)
        self.assertGreater(len(glob.glob(os.path.join(self.tmp.name, "*.csv"))), 1)
        self.assertEqual(len(self.rows()), 40)

    def test_disk_error_disables_without_raising(self):
        blocker = os.path.join(self.tmp.name, "file")
        open(blocker, "w").close()
        trace = ScaleTrace(os.path.join(blocker, "sub"), max_bytes=10**6, enabled=True)
        trace.record(reading(500.0), True, None)
        self.assertFalse(trace.enabled)


if __name__ == "__main__":
    unittest.main()

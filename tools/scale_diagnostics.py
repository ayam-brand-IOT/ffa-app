#!/usr/bin/env python3
"""Log raw transmitter data to CSV and classify what the weight is doing.

Run it on the Pi, next to the scale, and let it sit for a shift.  It answers
the one question the UI cannot: is the weight *noisy* (jitter around a stable
value), *drifting* (the zero walking away), or *jumping* (discrete steps, the
signature of a register/overflow problem)?

    python3 tools/scale_diagnostics.py --duration 600 --interval 0.2
    python3 tools/scale_diagnostics.py --belly --duration 60

Leave the scale EMPTY for a zero-drift run.  Put a known weight on it and do
not touch it for a repeatability run.
"""

import argparse
import csv
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import TLB_MODBUS as tlb  # noqa: E402


IDENTITY_REGISTERS = (
    ("firmware_version", 0),
    ("instrument_type", 1),
    ("year_of_manufacture", 2),
    ("serial_number", 3),
    ("program_type", 4),
)


def print_identity(inst):
    print("=" * 68)
    print("INSTRUMENT (slave {0} on {1} @ {2} baud)".format(
        inst.address, tlb.PORT, tlb.BAUDRATE))
    print("=" * 68)
    for name, address in IDENTITY_REGISTERS:
        try:
            print("  {0:<22} {1}".format(name, tlb._read(inst, address, 1)[0]))
        except tlb.TLBCommunicationError as exc:
            print("  {0:<22} <unreadable: {1}>".format(name, exc))

    division = tlb.getDivision()
    print("  {0:<22} {1} {2}".format("division", division, tlb.getUnit()))
    if division != tlb.EXPECTED_DIVISION:
        print("  !! division is not {0}. Every stored sample and the /10 in the"
              " old code assumed {0}.".format(tlb.EXPECTED_DIVISION))
    print()


def decode_status(status):
    bits = []
    for bit, name in tlb._FAULT_NAMES:
        if status & bit:
            bits.append(name)
    if status & tlb.ST_STABLE:
        bits.append("STABLE")
    if status & tlb.ST_NET_MODE:
        bits.append("NET_MODE")
    if status & tlb.ST_NEAR_ZERO:
        bits.append("NEAR_ZERO")
    if status & tlb.ST_NET_NEGATIVE:
        bits.append("NET_NEG")
    if status & tlb.ST_GROSS_NEGATIVE:
        bits.append("GROSS_NEG")
    return bits


def summarise(samples, division):
    """Separate jitter, drift and discrete jumps."""
    print()
    print("=" * 68)
    print("SUMMARY  ({0} samples over {1:.1f} s)".format(
        len(samples), samples[-1]["t"] - samples[0]["t"]))
    print("=" * 68)

    if len(samples) < 3:
        print("  not enough samples")
        return

    nets = [s["net"] for s in samples]
    counts = [s["counts_net"] for s in samples]
    stable_count = sum(1 for s in samples if s["stable"])

    print("  net min / max / span   {0:.2f} / {1:.2f} / {2:.2f}".format(
        min(nets), max(nets), max(nets) - min(nets)))
    print("  net mean / stdev       {0:.3f} / {1:.3f}".format(
        statistics.fmean(nets), statistics.pstdev(nets)))
    print("  peak-to-peak in counts {0}".format(max(counts) - min(counts)))
    print("  stable samples         {0}/{1}  ({2:.0f}%)".format(
        stable_count, len(samples), 100.0 * stable_count / len(samples)))

    faults = sorted({f for s in samples for f in s["faults"]})
    print("  faults seen            {0}".format(", ".join(faults) or "none"))

    # Drift: least-squares slope of net vs time, extrapolated to one hour.
    t0 = samples[0]["t"]
    times = [s["t"] - t0 for s in samples]
    mean_t = statistics.fmean(times)
    mean_n = statistics.fmean(nets)
    denom = sum((t - mean_t) ** 2 for t in times)
    slope = (sum((t - mean_t) * (n - mean_n) for t, n in zip(times, nets)) / denom
             if denom else 0.0)
    print("  drift                  {0:+.3f} per hour".format(slope * 3600.0))

    # Discrete jumps: a step much larger than the ambient noise.
    deltas = [abs(counts[i] - counts[i - 1]) for i in range(1, len(counts))]
    noise = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
    threshold = max(10.0, noise * 8)
    jumps = [(i, counts[i] - counts[i - 1])
             for i in range(1, len(counts)) if abs(counts[i] - counts[i - 1]) > threshold]
    print("  discrete jumps         {0} (threshold {1:.0f} counts)".format(
        len(jumps), threshold))
    for i, delta in jumps[:10]:
        flag = "  <-- 65536, register/overflow signature" if abs(delta) == 65536 else ""
        print("      t={0:7.1f}s  {1:+d} counts ({2:+.2f}){3}".format(
            times[i], delta, delta * division, flag))

    print()
    print("  READING:")
    span_counts = max(counts) - min(counts)
    if any(abs(d) == 65536 for _, d in jumps):
        print("    JUMPS of exactly 65536 counts -> a 16-bit boundary is being")
        print("    crossed. Check the register addressing, not the load cell.")
    elif abs(slope * 3600.0) > 2.0:
        print("    DRIFT dominates. Look at moisture in the cell/junction box,")
        print("    temperature, and mechanical load on the platform.")
    elif span_counts > 20 and stable_count < len(samples) * 0.5:
        print("    JITTER dominates. Look at the instrument filter setting,")
        print("    vibration, cable shielding and grounding.")
    else:
        print("    Reading looks steady over this window.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=300.0,
                        help="seconds to record (default 300)")
    parser.add_argument("--interval", type=float, default=0.2,
                        help="seconds between samples (default 0.2)")
    parser.add_argument("--belly", action="store_true",
                        help="read the belly test transmitter instead")
    parser.add_argument("--csv", default=None,
                        help="output CSV path (default logs/scale_diag_<ts>.csv)")
    parser.add_argument("--quiet", action="store_true",
                        help="do not print each sample")
    args = parser.parse_args()

    inst = tlb._for(args.belly)
    print_identity(inst)

    csv_path = args.csv or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "logs", "scale_diag_{0}.csv".format(time.strftime("%Y%m%d_%H%M%S")))
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)

    division = tlb.getDivision()
    samples = []
    errors = 0
    deadline = time.time() + args.duration

    print("Recording to {0}".format(csv_path))
    print("Ctrl-C to stop early.\n")

    with open(csv_path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "elapsed_s", "net", "gross",
                         "counts_net", "counts_gross", "status_hex",
                         "stable", "faults"])
        start = time.time()
        try:
            while time.time() < deadline:
                loop_start = time.time()
                try:
                    snapshot = tlb._snapshot(is_belly=args.belly)
                except tlb.TLBCommunicationError as exc:
                    errors += 1
                    print("  read error #{0}: {1}".format(errors, exc))
                    time.sleep(args.interval)
                    continue

                elapsed = loop_start - start
                snapshot["t"] = loop_start
                samples.append(snapshot)

                writer.writerow([
                    "{0:.3f}".format(loop_start),
                    "{0:.3f}".format(elapsed),
                    snapshot["net"], snapshot["gross"],
                    snapshot["counts_net"], snapshot["counts_gross"],
                    "0x{0:04X}".format(snapshot["status"]),
                    int(snapshot["stable"]),
                    "|".join(snapshot["faults"]),
                ])
                handle.flush()

                if not args.quiet:
                    print("  {0:7.1f}s  net={1:9.2f}  gross={2:9.2f}  "
                          "0x{3:04X}  {4}".format(
                              elapsed, snapshot["net"], snapshot["gross"],
                              snapshot["status"],
                              " ".join(decode_status(snapshot["status"]))))

                remaining = args.interval - (time.time() - loop_start)
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            print("\n  stopped by user")

    if errors:
        print("\n  {0} failed reads during the run".format(errors))
    if samples:
        summarise(samples, division)
    print("\nCSV: {0}".format(csv_path))


if __name__ == "__main__":
    main()

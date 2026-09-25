# Calibration Handoff - 2026-09-25

## Current Result

Debug station only: `pi@raspberry.local`, currently `192.168.100.21`.
The backend is container `ffa-app`, HTTP port 3030. Production and
`ffa-server-ffa-server-1` were not changed during these operations.

| Observation | NET / GROSS | Samples | Result |
| --- | --- | --- | --- |
| Structure only, before transmitter restart | 0.0 / -998.0 g | 30 | Active tare under the legacy decoder; zero check failed |
| Structure only, after transmitter restart | -997.5 / -997.5 g | 20 | No active tare; zero check failed |
| Same bottle, before zero correction | 1.5 / 1.5 g | 20 | Increment from structure was 999.0 g |
| Structure only, after authorized command 100 | 0.0 / 0.0 g | 12 serial, then 5 through restored backend | Zero check passed |
| Same bottle, after zero correction | 999.5 / 999.5 g | 30 | Nominal 1000 g check passed at +/-0.5 g |
| Bottle retained during operator-reported transmitter power cycle | 998.5 / 998.5 g | 30 | Nominal 1000 g check FAILED |

The last window contained two samples with the legacy stability bit clear;
all 30 weights were 998.5 g and the last 10 had stability set. There were no
reported faults, stale samples, NET/GROSS differences, or active tare in that
window. This does not validate the firmware's complete fault interpretation.

The loaded reading changed by -1.0 g across the reported power cycle. It did
not return to the previous large offset, but the result is not an exact
retention pass. Structure-only zero after this latest power cycle remains
unmeasured. Do not assume it is still zero.

The user reported a colleague had operated tare and suspected Zero as well.
That button history is not verified by the available logs. The observations
support a zero-offset issue but do not establish its cause. The bottle's mass
is not certified: 1000 g is its assigned nominal reference, not known truth.

## Authorized Changes

- With only the lamp/frame installed, command **100** was sent **once** to slave
  1, register 40006, using Modbus function 16. The transmitter acknowledged it.
- The normal backend was stopped first; the isolated process had only the
  serial device and no network or GPIO access. The backend was restored after
  the process exited. Its post-restoration zero check passed.
- No reference command 101/106, reset 104, explicit EEPROM-save command 99,
  capacity change, or sensitivity change was sent during this zero repair.
  Do not interpret the absence of command 99 as proof that command 100 is
  volatile; persistence must be checked on the instrument.
- `DEV_MODE=false` and `TLB_STATUS_MAP_VERIFIED=false` remain in effect.
  The global calibration safety gate was not bypassed in the regular service.

## Immediate Next Steps

1. Remove the bottle and record both transmitter display and HomeView after
   settling, with only the permanent lamp/frame. Do not press Tare or Zero.
2. Read fresh diagnostics and compare NET/GROSS with 0 +/-0.5 g. If the zero
   fails, preserve the evidence rather than masking it with another tare.
3. Repeat unloaded/loaded checks without adjustments, recording both readings
   and the loaded-minus-unloaded difference. Distinguish zero drift from a
   change in response to the same reference.
4. Validate with a reliable reference mass over the intended operating range.
   Do not silently widen the +/-0.5 g software threshold or recalibrate against
   an assumed exact bottle mass to make a report pass.
5. Before enabling guided calibration, finish the installed status-map and
   keypad-settings verification for every permitted transmitter. The flag is
   currently process-wide, not restricted to the tested weighing slave.
6. Exercise the integrated UI/backend calibration workflow on the debug station
   only after those prerequisites. Current bench operations do not validate it.
7. Build a reproducible image containing the frontend fix before any promotion.
   Keep the existing production deployment unchanged until acceptance criteria
   are defined and the relevant checks pass.

## Software State

- Backend branch: `codex/calibration-diagnostics`. Diagnostic commit `8478241`;
  setup tooling and follow-up documentation remain uncommitted. No push was
  completed. The earlier push was blocked; do not retry without resolving the
  requested authorization for the exact destination.
- Frontend branch: `codex/calibration-ui-feedback`, changes uncommitted. The
  wizard now handles correlated errors, timeouts, disconnects, duplicate/late
  replies, cancellation, and confirmed save completion. Fifteen isolated tests
  and desktop/mobile browser checks passed using a simulated transport.
- The frontend's existing local configuration changes belong to the user and
  must be preserved. At this check, its development Socket.IO URL was
  `http://192.168.100.21:3030/`.
- The compiled frontend is in the running container's `/app/dist`, not in a
  rebuilt image. Recreating it from the old image loses that UI update.
- UI backup: `/home/pi/ffa-debug-backups/ui-feedback-20260925.79TmwA/` on the Pi.
  The frontend README documents rollback.

## Evidence

Controlled zero operation on the Pi:
`/home/pi/ffa-debug-backups/20260924T230925Z/zero100-restore-20260925T204548Z.jsonl`.
Its companion `zero100-restore-20260925.py` has a one-shot attempt marker.
**Do not rerun it or delete the marker.**

Read-only reports on the development machine:

- `/tmp/ffa-zero-check-20260925.nFksF3/structure-only.json`
- `/tmp/ffa-after-restart-20260925.Xvya6o/structure-only.json`
- `/tmp/ffa-bottle-check-20260925.QoNutO/bottle.json`
- `/tmp/ffa-reference-after-zero-20260925.99Dosv/bottle.json`
- `/tmp/ffa-final-power-cycle-20260925.MhbAdX/bottle-after-restart.json`

See `TLB_SETUP.md` for the diagnostic script. It uses the backend's serial
owner; do not open a second serial client while the service is running.
Opening its Socket.IO connection turns laser ON and flash OFF through the
existing handler; clear that area and acknowledge the output side effect.
The diagnostic request itself sends no tare, zero, or calibration commands.

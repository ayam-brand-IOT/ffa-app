# WTB Calibration Diagnostics

For the later September 25 zero repair and latest power-cycle result, see
[the calibration handoff](CALIBRATION_HANDOFF_2026-09-25.md). The original bench
history below is retained; it is not the latest station measurement.

## Scope

Diagnostic backend changes on top of `new_image_process_hugo_fix` (`4c0f900`).
This branch does not constitute a metrological calibration certificate or
production approval. It does not modify the frontend or other repositories.

New calibration operations are blocked by default: `TLB_STATUS_MAP_VERIFIED`
defaults to `false`. Normal weight reads still use the legacy masks. Passing
mock-based tests does not establish compatibility with a physical transmitter.

Only enable this flag after verifying the installed firmware's signs, NET
mode, stability, and near-zero behavior against the legacy decoder. The flag
does not select the WTB v1.19 table. It is process-wide; verify every slave
that will be calibrated, not just the primary scale.

## Initial Failure

Observed on the debugging station on September 24, 2026 (America/Tijuana):

| State | GROSS (g) | NET (g) |
| --- | ---: | ---: |
| Permanent lamp/frame only, after the earlier faulty calibration | 116.5 | 0.0 |
| Same structure with the bottle | 1000.0 | 883.5 |

This established a NET/GROSS offset. It did not establish a broken load cell or
prove which earlier command was ignored. Clearing tare later removed the
offset but did not calibrate the loaded response by itself. The bottle's
assigned reference was 1000 g; its actual mass is not independently certified.

Operator-provided references:

- `WTB_manual_en.pdf`, v1.16, pages 19-20: permanent-structure zero and calibration.
- `WTB_datenuebertragungsprotokolle_en.pdf`, v1.19, pages 14-19: registers,
  Modbus functions, status, divisions, and commands.
- `WTB_datenuebertragungsprotokolle_en-calib.pdf`, v1.19, page 21: command 100,
  reference registers 40037/40038, command 101, and consumed-reference checks.

The v1.19 table places NET/stable/near-zero at bits 9/10/11, while the legacy
driver uses 10/11/12. The table also duplicates a NET-sign description. Do not
infer a new decoder from that inconsistency alone.

## Supervised Bench Evidence

Tests used real hardware (`DEV_MODE=false`), slave 1, raw firmware ID `11102`,
raw instrument type `105`, and division register `263` (`0x0107`, grams,
division 0.5 g). These IDs are recorded without assigning an unverified model
or firmware-version interpretation.

Observed status transitions:

| Observation | Raw status | Evidence for the legacy interpretation |
| --- | --- | --- |
| Positive settled load, semi-automatic tare active | `0x0C00` | NET mode and stability |
| Moving load with that tare active | `0x0400` | Bit 11 clears during movement |
| Negative NET with positive GROSS, tare active | `0x0D00` | NET sign at bit 8 |
| After command 9 removes semi-automatic tare | `0x0800` | Bit 10 clears; NET equals GROSS |
| Stable calibration zero | `0x1800` | Bit 12 appears at zero |
| Stable NET/GROSS of -0.5 g | `0x0980` | Both sign bits 7 and 8 set, near-zero bit clear |

The motion test captured 130 fresh samples without communication errors:
54 at `0x0C00` and 76 at `0x0400`. This supports stability at bit 11 on this
unit, rather than bit 10 in the supplied table. The later zero and negative
readings are consistent with the remaining legacy masks, but do not validate
all fault conditions, another slave, or every firmware revision.

Controlled command sequence and observations:

1. With only the permanent structure installed, command 9 was explicitly
   authorized and sent once. NET changed from 0.5 g to GROSS at 117.0 g;
   the 116.5 g NET/GROSS difference disappeared.
2. Command 100 was sent once with only that structure. NET and GROSS both
   became 0.0 g and remained stable after the backend was restarted.
3. With the bottle installed, both channels read 886.0 g before calibration.
   The reference pair was written/read back as `[0, 10000]`, then command 101
   was sent once. Both registers became zero and both weights became 1000.0 g.
4. Removing the bottle produced -0.5 g in 20 stable samples. Replacing it
   produced 1000.0 g in 20 stable samples, with no faults or NET/GROSS mismatch.
5. With the reference still present, command 99 was sent once and acknowledged.
   Serial and restored-backend checks continued to show 1000.0 g.
6. After the operator reported physically disconnecting/reconnecting the
   transmitter, the bottle read 999.0 g in 30 stable samples. After its removal,
   the structure read 0.0 g in 30 stable samples. Both channels agreed; there
   were no read errors, stale samples, instrument faults, or active NET mode.

The 999.0 g result is **not a pass against the one-division +/-0.5 g reference
check**. It is consistent with retained calibration rather than a return to the
approximately 886 g pre-reference reading, but its one-gram deviation remains
unresolved. The subsequent zero reading does not prove the cause. Do not
declare physical accuracy, repeatability over the operating range, or the UI
workflow validated from this single reference exercise.

No tare, zero, recalibration, or save command was sent during the post-power-cycle
observations. The global verification flag remains false.

These command writes were operator-supervised diagnostic operations in an
isolated process with only the serial device available. The regular backend
was stopped before opening the port and restored afterward. They did not
exercise the UI wizard or bypass its gate globally. No command was retried
after an uncertain response. Preparatory attempts that stopped before any
write are not evidence of a hardware command failure.

### Evidence Files

JSONL evidence is retained on the debugging station under
`/home/pi/ffa-debug-backups/20260924T230925Z/` (not committed to Git). Timestamps
in these filenames are UTC; the full session took place on September 24 local
time in America/Tijuana.

| File | Purpose |
| --- | --- |
| `motion-20260924T234353Z.jsonl` | Movement/stability comparison |
| `clear-tare-20260924T235003Z.jsonl` | Explicit command 9 and NET/GROSS comparison |
| `zero100-20260924T235757Z.jsonl` | Single calibration-zero command |
| `reference101-20260925T001844Z.jsonl` | Accepted reference and post-command checks |
| `return-zero-after101-20260925T002056Z.jsonl` | Unloaded repeat check |
| `reload-reference-after101-20260925T002229Z.jsonl` | Reference reload check |
| `save99-20260925T002518Z.jsonl` | Single EEPROM-save command and response |
| `after-power-cycle-20260925T004246Z.jsonl` | Loaded reading after operator-reported power cycle |
| `zero-after-power-cycle-20260925T004538Z.jsonl` | Unloaded reading after that power cycle |

## Diagnostics Without Modbus Writes

Use the existing Socket.IO connection:

```javascript
socket.on("scale_diagnostics", snapshot => console.log(snapshot));
socket.on("scale_diagnostics_error", error => console.error(error));
socket.emit("get_scale_diagnostics", { mode: "weight" });
// For the other transmitter: { mode: "belly" }
```

The event uses the backend's existing serial connection and transaction lock.
Do not import `hardware` in another process or open a competing serial client
while the service owns the bus. Requests are rejected during an active
calibration lease. DEV_MODE returns an explicit unsupported-diagnostics error,
not invented registers.

**Connection side effect:** the existing Socket.IO connection handler turns
the laser on and the flash off. The diagnostic event itself does not change
outputs, but opening a new connection can. Clear the area before connecting.

Returned data includes raw firmware/type IDs; `registers_40001_40014` (index 5
is `null` because command register 40006 is write-only); `status_raw` and
`status_hex`; division/unit; NET, GROSS and their difference; and both candidate
status interpretations. `interpretation: legacy` and `status_map_verified`
identify the decoder and configuration, not an automatic verification result.

Reads cover 40001-40005 followed by 40007-40014. Weight, status, and scale
configuration come from the same second block and the selected slave, not the
primary scale's configuration cache. A failed bus read returns an error, never
stale weight or the synthetic zero used while ordinary polling is paused.

## Guided Workflow Checks

1. Preflight: verified status map, valid target, grams, finite positive reference,
   no faults, and no active NET mode/tare or significant NET/GROSS difference.
   Command 9 is not sent automatically.
2. Zero: record the initial state, wait for stability, send 100 once, and require
   three fresh stable readings with NET and GROSS within one division of zero.
3. Reference: require a positive load, record the initial state, write the
   reference, send 101 once, check consumed sample registers, and require three
   fresh stable readings with NET and GROSS within one division of the reference.
4. Save: with the reference still installed, verify it before sending 99 and
   again afterward. The existing 99 save step is retained; page 21 of the
   supplied calibration extract does not explicitly require it for calibration.

The one-division check is a software verification threshold, not a claim of
instrument accuracy. A unit/division change aborts the session. Steps must
follow 1-2-3-4 on the same target. Kilograms are rejected by the guided workflow
because the existing frontend/storage contract assumes grams.

`calibration_step_commited` includes `step`, `args`, `request_id` (when supplied),
and `diagnostic`. Errors include the request context; a failed verification
does not produce a success acknowledgement. Logs use `calibration_diagnostic`
for the initial, verified, or rejected snapshot at each stage.

Overlapping requests are rejected even from the same client. Tare, operational
zero, and mode changes are blocked during the session. Disconnect/cancellation
defers release until an in-flight operation returns, invalidates cached socket
snapshots, and does not announce a cancelled operation as successful.

An error after 100 or 101 does not undo the transmitter's already-applied
change. Inspect its state before starting again. Commands are not automatically
replayed; command 104 is not a rollback of the tare zero.

## Before Production Approval

- Investigate the two-division reference deviation after power cycling; repeat
  loaded/unloaded checks and verify accuracy with a reliable mass over the
  intended operating range. Do not silently loosen the software threshold.
- Verify each installed instrument's status map, including signs and faults.
  Keep the default calibration gate until that work is complete.
- Update the frontend to handle immediate errors, correlate replies, and wait
  for successful save before showing completion. This branch does not fix the
  existing wizard's ignored errors or premature completion message.
- Exercise the integrated UI/backend workflow after those frontend changes.
  Supervised command tests and mock tests are not a substitute.
- Preserve images and configuration before replacing containers. The diagnostic
  deployment backed up the previous container/image and application files;
  these backups do not contain the WTB's internal calibration parameters.
- Rebuild/recreate containers for code changes. Keep production and the separate
  `ffa-server` service untouched during diagnostic work.

## Hardware-Free Tests

Run each script in a separate process because test fixtures install mock
modules in `sys.modules`:

```sh
python3 tests/test_calibration_diagnostics.py
python3 tests/test_calibration_socket_guard.py
python3 tests/test_tlb_registers.py
python3 tests/test_tlb_safety.py
python3 tests/test_socket_availability.py
python3 tests/test_scale_controls.py
python3 tests/test_image_process_safety.py
```

The scale-controls suite needs Eventlet; image tests need OpenCV and NumPy.
No hardware-free suite validates physical precision or a firmware status map.

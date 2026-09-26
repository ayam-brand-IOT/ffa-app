# Reproducible Weighing-Station Setup

`tools/tlb_setup.py` plans and checks the primary weighing transmitter. It does
not write Modbus registers, calibrate a station, or clone another station's
zero/span. It uses Python's standard library and the running diagnostic
backend's existing serial connection, so it does not create competing bus
masters or import GPIO/camera hardware.

## What Must Match

Use the same approved units, resolution, filtering, zero behavior, serial
settings, and software measurement contract at debugging and production.
Matching these settings alone does not guarantee identical measurements.
Each assembled scale needs its own calibration with a reliable reference.

The included profile is a **target for static weighing**, not an export of all
settings from the debugging transmitter and not a profile for the belly test.

| Setting | Profile target | Verification |
| --- | --- | --- |
| Unit / division | g / 0.5 g | Read through backend, including raw register 40014 |
| Slave | 1 | Read through backend |
| Firmware/type IDs | 11102 / 105, observed on the debug unit | Compare raw IDs, review differences before production |
| `FS-tEO` | Unset: actual rated system capacity in grams | Cell datasheet and keypad |
| `SEnSib` | Unset: actual sensitivity in mV/V | Cell datasheet and keypad |
| `MASS` | Unset: reviewed maximum display value | Keypad; 0 disables this limit |
| `FiLtEr` | 3 (425 ms response), see settling test below | Keypad and application-specific settling test |
| Anti-peak | ON | Keypad; not offered after `FiLtEr` on the 11102/105 debug unit. Unsuitable as a blanket setting for transient-force tests |
| `AUTO 0` | 0, disabled | Keypad |
| `TRAC 0` | NONE, disabled for this diagnostic baseline | Keypad |
| `0 SEt` | Unset: reviewed operational zero range in grams/ | Keypad; account for decimal places |
| Preset tare | 0 g | Keypad; distinct from permanent-structure zero |
| Display coefficient | 1 | Keypad |
| Serial | Modbus-RTU, 9600, 8N2, address 1, delay 0 ms | Keypad and backend configuration |

The running driver uses two stop bits, while the supplied manual lists one as
the instrument's default. Configure the actual transmitter and backend to
match. A successful diagnostic response does not prove every serial parameter
or keypad setting was independently read back.

For a **confirmed single 10 kg cell**, the theoretical full scale is 10000 g;
use 2.00000 mV/V only if its datasheet specifies that value. Do not subtract the
approximately 5 kg permanent lamp/frame from the rated capacity. Its load still
counts toward the physical limit even when the display has been zeroed.

**Changing `FS-tEO` or `SEnSib` cancels real calibration and can reset weight
parameters. `FS-tEO=0` restores factory values.** Inspect the current debugging
station without re-entering/changing these values merely to run this tool.
On a new station, configure theoretical values before its own zero/reference
calibration. The profile validator refuses a zero theoretical capacity.

The supplied Modbus table makes register 40014 read-only and does not provide
verified write mappings for all of these keypad settings. This tool therefore
does not invent configuration register addresses. Manual targets are explicitly
reported as unverified even when the automatic reading checks pass.

## Commands

Run from the `ffa-app` repository root. With no arguments, nothing connects to
the backend and no files or hardware parameters are changed:

```sh
python3 tools/tlb_setup.py
python3 tools/tlb_setup.py init --profile /tmp/ffa-weight-profile.json
python3 tools/tlb_setup.py plan --profile /tmp/ffa-weight-profile.json
```

Keep `tools/tlb_setup.py` and `tools/tlb_setup_profile.example.json` together
when copying the tool to a station. No Python hardware packages are needed on
the machine running this client; actual serial access stays in the backend.

`init` creates a new JSON profile without overwriting an existing file. Fill
the `null` targets from the cell documentation and reviewed station settings;
the tool never substitutes guessed capacity or sensitivity. Keep an approved
profile per hardware configuration. Do not edit firmware IDs just to silence
a mismatch or copy cell-specific parameters between different hardware.

Run the following **on the station**, with the diagnostic backend already
running. The normal backend must provide `get_scale_diagnostics`; an older
backend or DEV_MODE cannot supply this raw diagnostic contract. A deployment
of the diagnostic branch is separate from running this script.

**Before connecting:** clear the laser area. The existing backend connection
handler turns the laser ON and flash OFF. The explicit acknowledgement flag
is required because even a diagnostic connection has this output side effect.
No tare, zero, sample, save, reset, or configuration command is sent.

Structure only, with the permanent lamp/frame still installed:

```sh
python3 tools/tlb_setup.py check --profile /tmp/ffa-weight-profile.json \
  --expected-g 0 --report /tmp/ffa-zero-before.json \
  --ack-connection-outputs
```

Place a reliable reference. For a known 1000 g mass:

```sh
python3 tools/tlb_setup.py check --profile /tmp/ffa-weight-profile.json \
  --expected-g 1000 --report /tmp/ffa-reference-before.json \
  --ack-connection-outputs
```

The default backend URL is `http://127.0.0.1:3030`. `--url` accepts another
explicit backend origin. Only use trusted station endpoints; opening a remote
connection also affects that station's laser/flash through the existing handler.
Use `--samples` (3-120) and `--interval` (0.2-10 seconds) to adjust the window.

Repeat unloaded/loaded checks after removing and replacing the mass and after
an operator-controlled power cycle, using new report filenames. Do not press
tare or zero between those checks. A fresh initialization of the backend is
not a transmitter power-cycle test. This tool does not switch power itself.

## Reading the Result

- Exit `0`: all requested automatic reading checks passed.
- Exit `1`: a measurement, communication, identity, freshness, stability, or
  configuration check failed. The report includes available readings and errors.
- Exit `2`: invalid arguments/profile or file/format error.
- Exit `130`: interrupted by the operator.

A check requires fresh increasing diagnostic timestamps, a consistent device
identity, matching expected IDs/unit/division, no fault or active NET mode,
legacy stability, agreement with raw display digits, and NET/GROSS within one
division of the expected load and each other. It never averages away a failed
sample or silently widens the tolerance. At 0.5 g division, 999.0 g fails a
1000.0 g check; 999.5 g is within its software threshold.

JSON reports embed the target profile, its SHA-256, raw snapshots, expected
weight, and failures. They always distinguish `automatic_check_passed` from
`keypad_settings_verified: false` and `production_ready: false`. A single
passing load window cannot establish all manual settings, calibration quality,
or absolute accuracy. Reports and profiles are never overwritten automatically.

## Settling Test (2026-09-25, debug unit 11102/105)

HomeView captures on the transmitter's stability bit, so the filter sets the
wait after the load stops moving. Read-only `get_scale_diagnostics` sampling
at ~6-10 Hz, time from the value holding within one division to the bit:

| `FiLtEr` | Stability after the value settled | Steady-load noise |
| --- | --- | --- |
| 4 (default, 850 ms) | 1.5-2.9 s (2 placements) | 0.5 g peak-to-peak |
| 3 (425 ms) | typically 0.5-0.7 s, up to ~2.8 s (15 placements) | up to 1.0 g peak-to-peak |

`FiLtEr` 3 also drops the stability bit more often during handling. Changing
the filter does not cancel calibration. Repeat this test per installation;
vibration and product handling change the result.

## Calibration and Remaining Work

Keep `DEV_MODE=false` for real hardware, the intended `TLB_PORT`/`TLB_BAUDRATE`,
and a consistent timeout (the debug test used `TLB_TIMEOUT=1`). Keep
`TLB_STATUS_MAP_VERIFIED=false` until the installed firmware map is verified;
this tool neither changes that flag nor bypasses the calibration gate.

After theoretical settings are established, each station needs permanent-
structure zero and its own sample calibration. The supplied user manual calls
for a reference of at least half the maximum quantity intended to be weighed,
not automatically half the cell's rated capacity. Use a reliable reference
appropriate to the actual product range, not a bottle with an assumed mass.

The bench's loaded reading after restart was 999.0 g against the assigned
1000 g reference, while the unloaded reading returned to 0.0 g. This remains
unresolved; identical setup targets are not evidence that this discrepancy is
fixed. See [Calibration Diagnostics](CALIBRATION_DIAGNOSTICS.md).

Sources: operator-supplied `WTB_manual_en.pdf` v1.16, printed pages 18-23 and
31-32; `WTB_datenuebertragungsprotokolle_en.pdf` v1.19, printed pages 16-19.

Hardware-free tests:

```sh
python3 tests/test_tlb_setup.py
```

# TLB Weight Transmitter — Setup and Calibration Guide

Everything needed to configure, calibrate and troubleshoot the Laumas weight
transmitters used by the FFA station, written so that someone standing in
front of the machine with the keypad can follow it start to finish.

**Sources.** All parameter names, ranges, defaults and procedures come from
two manuals, both version 1.16:

- *WTB / TLB User Manual* — keypad, menus, calibration, filters, alarms.
  This one document covers both models; TLB-specific items are flagged in it
  (e.g. the optoisolated analog output).
- *TLB Communication Protocols* — Modbus-RTU register map, command register,
  status register.

Where this guide says "the manual says", the wording is quoted so you can
find it. Nothing here is invented; where something is an FFA-specific
recommendation rather than a manual instruction, it says so.

**Display font.** The transmitter has a 6-digit 7-segment display, so
parameter names look mangled: `FS-tEO`, `SEnSib`, `diUiS`, `2Er0`, `UEiGHt`.
They are written here exactly as they appear on the display.

---

## Table of contents

1. [The two transmitters](#1-the-two-transmitters)
2. [Keypad and navigation](#2-keypad-and-navigation)
3. [Menu map](#3-menu-map)
4. [Diagnose before you configure](#4-diagnose-before-you-configure)
5. [Parameter reference](#5-parameter-reference)
6. [Calibration procedure](#6-calibration-procedure)
7. [What survives a power cycle](#7-what-survives-a-power-cycle)
8. [Keypad ↔ Modbus equivalents](#8-keypad--modbus-equivalents)
9. [Status register and alarms](#9-status-register-and-alarms)
10. [Troubleshooting](#10-troubleshooting)
11. [Installation rules](#11-installation-rules)
12. [Recommended settings summary](#12-recommended-settings-summary)

---

## 1. The two transmitters

The FFA station has two transmitters on one RS485 bus, and **they need
opposite configurations**. This is the single most commonly missed point.

| | Slave 1 — weighing station | Slave 2 — belly test |
|---|---|---|
| Job | Weigh a fish that is sitting still | Capture the force at which a belly tears |
| Wants | A reading that stops moving | To catch a fast transient |
| Filter | Heavy (4–5) | None (0) |
| Anti-peak | On | Off |
| Code reads it via | `readWeightSnapshot()` | `readTensionSnapshot()` |

Configuring both the same way is why one of them always behaves badly: a
filter that makes the weighing station calm makes the belly test miss the
peak, and a filter fast enough for the belly test makes the weighing station
jitter.

---

## 2. Keypad and navigation

Four keys. In this guide they are written as:

| Key | Function |
|---|---|
| `↵` | Enter a menu / confirm the entry |
| `▲` | Change the displayed digit or menu item |
| `◀` | Select a different digit, or move to another menu item |
| `✖` | Cancel and go back to the previous menu |

> "Into menus changes are applied right after pressing the `↵` key (no
> further confirmation is required)."

That matters: there is no "save and exit". The moment you press `↵` on a
value, it is applied.

### Shortcuts from the weight display

| Press | Goes to | What it is |
|---|---|---|
| `↵` + `✖` | `CALib` | The whole system parameter menu |
| `✖` for 3 s | `2Er0` | Tare weight zero setting (the permanent zero) |
| `▲` for 3 s | `MU-CEL` | Raw load cell signal in millivolts |
| `↵` + `◀` | `P-tArE` | Preset (subtractive) tare |

`▲` held for 3 seconds is the most useful key on the instrument and almost
nobody knows it exists. See [section 4](#4-diagnose-before-you-configure).

---

## 3. Menu map

```
weight display (000000)
│
├─ ↵ + ✖ ──> CALib ──┬── FS-tEO   theoretical full scale     default dEMO (=10000)
│                    │   SEnSib   load cell sensitivity mV/V default 2.00000
│                    │   diUiS    division (resolution)      auto = FS / 10000
│                    │   MASS     maximum capacity           default 0 (disabled)
│                    │   2Er0     TARE WEIGHT ZERO SETTING   <- permanent
│                    │   InP 0    manual zero value entry
│                    │   UEiGHt   REAL CALIBRATION           <- sample weights
│                    │   unit     unit of measure
│                    │   COEFF    display coefficient
│                    │
│                    ├── FiLtEr   weight filter 0-9  ->  AntPOn / AntPOF
│                    │
│                    ├── PArA 0 ──┬── 0 SEt    resettable weight     default 300
│                    │            │   AUt0 0   autozero at power-on  default 0
│                    │            └── trAC 0   zero tracking         default nOnE
│                    │
│                    ├── SEriAL ── rS485 ── ModbUS ──┬── bAUd    2400..115200, default 9600
│                    │                               │   Addr    1..99, default 1
│                    │                               │   dELAY   0..200 ms, default 0
│                    │                               │   PArity  none / even / odd
│                    │                               └── StOP    1 or 2, default 1
│                    │
│                    ├── Out-In ── Out 1/2/3, In 1/2
│                    ├── tESt   ── In, Out
│                    └── InFO
│
├─ ✖ 3 s ──> 2Er0        (shortcut into the calibration menu)
├─ ▲ 3 s ──> MU-CEL      (millivolt test)
└─ ↵ + ◀ ──> P-tArE      (preset tare)
```

Inside `CALib`, move between the sub-items with `◀` and `▲`.

---

## 4. Diagnose before you configure

Changing settings before knowing what is wrong wastes a day. These three
checks take about fifteen minutes and tell you which of the three possible
problems you actually have.

### 4.1 The millivolt test — `MU-CEL`

From the weight display, hold `▲` for 3 seconds. The display shows the raw
load cell response in **millivolts with four decimals**.

> "a load cell with 2.000 mV/V sensitivity provides a response signal
> between 0 and 10 mV."

Watch it for a minute, **with the line running**, not with the plant stopped.

| What you see | What it means | Where to go next |
|---|---|---|
| mV wanders or jumps | The problem is upstream of the electronics: cell, cable, grounding, moisture, vibration | [Section 4.2](#42-load-cell-electrical-test) and [section 11](#11-installation-rules) |
| mV is steady, weight is not | The problem is scaling or filtering | [Section 4.3](#43-the-over-resolution-check) and [section 5.2](#52-filter--filter) |

This single test splits the problem in two and saves you from chasing the
wrong half.

### 4.2 Load cell electrical test

With a digital multimeter. The manual's order is deliberate — the moisture
check comes first because in a fish plant it is usually the answer.

**Instrument OFF, load cells disconnected:**

1. **Check for moisture in the cell junction box** caused by condensation or
   water infiltration. "If so, drain the system or replace it if necessary."
2. Resistance between **signal +** and **signal −** must match the cell data
   sheet (output resistance).
3. Resistance between **excitation +** and **excitation −** must match the
   data sheet (input resistance).
4. Insulation between the **shield and any other wire**, and between **any
   wire and the cell body**, must be **higher than 20 MΩ**.

**Instrument ON:**

5. Excitation across the two supply wires must be **5 VDC ±3%**.
6. With the cell unloaded, signal between + and − must be between
   **0 and ±0.5 mV**.
7. Apply load and confirm the signal increases.

> "IF ONE OF THE ABOVE CONDITIONS IS NOT MET, PLEASE CONTACT THE TECHNICAL
> ASSISTANCE SERVICE."

**If your cells are 4-wire**, there must be jumpers between **EX− and REF−**
and between **EX+ and REF+**. Missing jumpers is one of the documented causes
of the `ErCEL` alarm.

### 4.3 The over-resolution check

This is arithmetic, and it explains most "the weight never sits still"
complaints that no filter setting can fix.

Read `FS-tEO` (theoretical full scale) and `diUiS` (division) from the menu,
then divide:

```
number of divisions = FS-tEO / diUiS
```

The manual sets the default relationship itself:

> "It is automatically calculated by the system according to the performed
> calibration, so that it is equal to **1/10000 of full scale**."

So the instrument's own default is **10,000 divisions**. Going far beyond
that asks the mechanics for resolution they do not have.

| Divisions | Verdict |
|---|---|
| ≤ 10,000 | Healthy — this is the design point |
| 10,000 – 20,000 | The last digit will visibly move |
| > 20,000 | The last digit **is noise**. No filter setting will fix it |

**Worked example.** A 6 kg cell displaying to 0.1 g is 60,000 divisions — six
times the design point. On a platform near a running conveyor the last digit
will never settle, and the operator sees "the weight keeps moving".

Two ways out, both real fixes rather than workarounds:

- Coarsen the division (0.1 g → 0.2 g or 0.5 g). You lose a digit you were
  never actually measuring.
- Fit a load cell sized closer to the real weighing range. The manual
  recommends using a cell "up to a maximum of 70–80% of their rated
  capacity"; a cell that is enormously oversized for the load is the
  underlying cause here.

---

## 5. Parameter reference

### 5.1 Theoretical calibration — `FS-tEO`, `SEnSib`, `diUiS`

Path: `↵`+`✖` → `CALib` → `↵` → `FS-tEO`

This tells the instrument what load cells it is connected to. It is the
foundation everything else sits on.

| Parameter | Range / default | Meaning |
|---|---|---|
| `FS-tEO` | default `dEMO` (=10000) | System full scale = one cell's capacity × number of cells. Four 1000 kg cells → 4000. Set 0 to restore factory values. |
| `SEnSib` | 0.50000 – 7.00000 mV/V, default 2.00000 | The cell's rated sensitivity, printed on the cell. With several cells, enter the average. |
| `diUiS` | 0.0001 – 100, ×1 ×2 ×5 ×10 steps | The smallest weight increment displayed. Calculated automatically as FS/10000; can be overridden. |

The manual's own averaging example: four cells at 2.00100, 2.00150, 2.00200
and 2.00250 → enter 2.00175.

> ⚠️ **Do not enter this menu just to recalibrate.** "By modifying the
> theoretical full scale or the sensitivity, **the real calibration is
> cancelled** and the theoretical calibration only is considered valid", and
> "the system's parameters containing a weight value will be set to default
> values (setpoint, hysteresis, etc.)".
>
> If the instrument is already commissioned and you only want to recalibrate
> with weights, go straight to `UEiGHt`.

**How to tell which calibration is active:** compare `FS-tEO` with the
recalculated full scale shown at the end of the real calibration. Equal means
the theoretical calibration is in use; different means the real (sample
weight) calibration is in use.

### 5.2 Filter — `FiLtEr`

Path: `CALib` → `◀`/`▲` → `FiLtEr`

> "To increase the effect (weight more stable) increase the value (from 0 to
> 9, default 4)."

| Value | Response time | Display / serial refresh |
|---|---|---|
| 0 | 12 ms | 300 Hz |
| 1 | 150 ms | 100 Hz |
| 2 | 260 ms | 50 Hz |
| 3 | 425 ms | 25 Hz |
| **4** (default) | 850 ms | 12.5 Hz |
| **5** | 1700 ms | 12.5 Hz |
| 6 | 2500 ms | 12.5 Hz |
| 7 | 4000 ms | 10 Hz |
| 8 | 6000 ms | 10 Hz |
| 9 | 7000 ms | 5 Hz |

The instrument gives you a tuning loop: confirm `FiLtEr`, change the value,
and it drops you back to the live weight so you can watch the stability. Not
satisfied — confirm again and you are back at `FiLtEr` to try another value.
**Do this with the conveyor running.**

**Weighing station: start at 4, go to 5 if jitter persists.**

Do not go past 6. The FFA capture waits for the instrument's stability bit
with a 4-second timeout, and filter 7 has a 4000 ms response time — captures
would start timing out. If you genuinely need 7 or higher, raise the timeout
in `HomeView.vue` at the same time.

**Belly test: 0.** The manual is explicit about this in the PEAK section:
"If you wish to use this input to view a sudden variation peak, set the
FILTER ON THE WEIGHT to 0."

#### Anti-peak — `AntPOn` / `AntPOF`

Confirm the filter value with `↵` and you get the anti-peak choice.

> "When the weight is stable, the anti-peak filter removes any sudden
> disturbances with a maximum duration of 1 second."

- **Weighing station: `AntPOn`** (default). Exactly what you want against
  conveyor knocks and someone bumping the platform.
- **Belly test: `AntPOF`.** A belly tearing *is* a sudden disturbance
  shorter than a second. Leaving anti-peak on deletes the event you are
  trying to measure.

### 5.3 Zero parameters — `PArA 0`

Path: `CALib` → `◀`/`▲` → `PArA 0`

| Parameter | Range / default | What it does |
|---|---|---|
| `0 SEt` | 0 to full scale, default **300** | Maximum weight that the zero command can clear — "resettable by external contact, keypad or serial protocol" |
| `AUt0 0` | 0 to 10% of full scale, default **0** | At switch-on, if the weight is below this value it is zeroed. 0 disables |
| `trAC 0` | 1 to 5, default **`nOnE`** | Zero tracking. If the weight is stable and after one second deviates from zero by this many divisions or fewer, it is zeroed. `nOnE` disables |

**`0 SEt` — read the decimals carefully.** The default is 300 but the
decimals follow your division: "considered decimals: 300 – 30.0 – 3.00 –
0.300". With a 0.1 division in grams, the default means **30.0 g**. If real
drift exceeds that, the zero command fails and raises an alarm rather than
doing nothing quietly — see [section 9](#9-status-register-and-alarms).

**`AUt0 0` — leave it at 0.** If the machine is powered on with a fish, a
tray or a box on the platform, autozero silently tares it out and the whole
shift is offset. This is an independent cause of "the scale lost its
calibration" and it is invisible from the app.

**`trAC 0` — the default is `nOnE`, meaning it is off.** Setting it to 2
gives 0.2 g of automatic drift correction with a 0.1 division, which is
negligible against a fish and quietly cleans up slow zero wander. The
manual's own example: `diUiS` = 5 and `trAC 0` = 2 → variations of 10 or less
(`diUiS` × `trAC 0`) are zeroed.

### 5.4 Maximum capacity — `MASS`

Path: `CALib` → `◀`/`▲` → `MASS`

> "maximum displayable weight (from 0 to full scale; default: 0). When the
> weight exceeds this value by 9 divisions, the display shows `------`. To
> disable this function, set 0."

Default 0 means **disabled**. Setting it to your realistic maximum turns on
the overload alarm, which maps to status register bit 2 — and the FFA app now
reads that bit and logs it. Worth enabling: it turns silent overloads into
recorded events.

### 5.5 Serial — `SEriAL` → `rS485`

Path: `CALib` → `◀`/`▲` → `SEriAL` → `rS485` → `ModbUS`

| Parameter | Options / default | Set to |
|---|---|---|
| protocol | `nOnE` (default), `ModbUS`, `ASCII`, `COntIn`, `rIP`, `HdrIP`, `HdrIPn`, `YHL` | `ModbUS` |
| `bAUd` | 2400, 4800, 9600, 19200, 38400, 115200; default 9600 | **38400** (see caution) |
| `Addr` | 1–99, default 1 | 1 (weighing), 2 (belly) |
| `dELAY` | 0–200 ms, default 0 | **0** |
| `PArity` | none (default), even, odd | none |
| `StOP` | 1 or 2, default **1** | 1 |

**Stop bits mismatch.** `TLB_MODBUS.py` currently opens the port with
`STOPBITS_TWO` while the instrument default is 1. It works — a receiver only
needs to see one stop bit — but it wastes about 9% of the throughput on a bus
that is already tight. Make them match, either way.

> ⚠️ **Termination resistors.** "If the RS485 network exceeds 100 metres in
> length **or baud-rate over 9600 are used**, two terminating resistors are
> needed at the ends of the network: close the two jumpers indicated in the
> picture on the furthest instruments."
>
> Raising the baud rate to 38400 without closing those jumpers trades one
> problem for another. Do both or neither.

Why raise it at all: at 9600 8N2 one Modbus transaction costs roughly 20 ms
of line time before the instrument even replies. At 38400 that drops to about
5 ms, which is what makes the 50 ms belly-test sampling comfortable instead of
marginal. After changing it, set `TLB_BAUDRATE=38400` in the app environment.

---

## 6. Calibration procedure

Do these in order. The manual's commissioning section defines the sequence,
and doing it out of order erases earlier work.

### Step 0 — Prerequisites

Run the checks in [section 4](#4-diagnose-before-you-configure) first. If
`MU-CEL` is unstable or the cell fails its electrical test, calibration will
not stick and you will be back next week.

Have ready:

- Certified sample weights. **At least one must be ≥ 50% of the heaviest
  thing you actually weigh** — see step 3.
- A stable, empty platform.
- Ideally the plant in its normal running state, not silent.

### Step 1 — Theoretical calibration (first commissioning only)

**Skip this step entirely if the instrument already has its plant
identification tag** — entering it cancels the existing real calibration.

`↵`+`✖` → `CALib` → `↵` → `FS-tEO`

1. `FS-tEO` — cell capacity × number of cells, in your working unit.
2. `SEnSib` — the mV/V from the cell label (average if several).
3. `diUiS` — accept the automatic value unless the over-resolution check in
   [section 4.3](#43-the-over-resolution-check) says otherwise.

### Step 2 — Tare weight zero setting — `2Er0`

**This is the permanent zero. It is not the same as the app's Tare button.**

Platform **empty**. Hold `✖` for 3 s from the weight display, or navigate
`CALib` → `◀`/`▲` → `2Er0`.

1. Confirm `2Er0` with `↵`.
2. The weight to be zeroed is displayed, **all LEDs flashing**.
3. Confirm again with `↵` — "the weight is set to zero (**the value is
   stored to the permanent memory**)".
4. Press `▲` to see the total weight zeroed so far, the sum of every previous
   zero setting.

That accumulated figure is a free diagnostic. If it has grown a lot over the
months, you have genuine mechanical drift — product residue building up,
something fouling the platform, or a cell going bad. Recalibrating without
investigating that just resets the counter.

### Step 3 — Real calibration with sample weights — `UEiGHt`

`CALib` → `◀`/`▲` → `UEiGHt`

> "Load onto the weighing system a sample weight, which must be **at least
> 50% of the maximum quantity to be weighed**."

This is the rule most often broken. Calibrating a 6 kg range with a 1 kg
weight fixes the slope using 17% of the span and extrapolates the rest — the
error grows the further you get from the calibration point, which is exactly
where your heaviest, most valuable fish are.

1. Place the sample weight on the platform. Let it settle.
2. Confirm `UEiGHt` with `↵`. The current weight appears **flashing, with all
   LEDs off**.
3. Correct the displayed value to the true value of the weight, using the
   arrow keys.
4. Confirm with `↵`. The new weight appears with **all LEDs flashing**.
5. Confirm again. `UEiGHt` comes back.
6. Press `▲` here to see the **recalculated full scale**. Sanity-check it
   against `FS-tEO` — a wildly different number means something is wrong.
7. Press `✖` repeatedly to return to the weight display.

The LED behaviour is your progress indicator: **all off** = enter the value,
**all flashing** = value accepted.

#### Multi-point linearisation (up to 8 points)

Repeat steps 1–5 with a different sample weight. Recommended for FFA: three
points spanning the real fish range — low, middle, high.

- The procedure ends when you press `✖` or after the eighth value.
- After that "it will no longer be possible to change the calibration value,
  but only to perform a new real calibration" — return to the weight display
  and re-enter the menu to start over.
- `MAH-PU` on the display means you have entered the eighth point.

### Step 4 — Verify linearity

**Do not skip this.** It is the only step that tells you whether the scale is
actually correct rather than merely calibrated at one point.

The manual's example, adapted to a fish station with a 2 kg and a 1 kg
weight:

1. Load both weights. Correct the reading to **3000 g**.
2. Remove the 1 kg weight. The display **must show 2000**.
3. Remove the 2 kg weight. The display **must show 0**.

> "If this does not happen, it means that there is a mechanical problem
> affecting the system linearity. **WARNING: identify and correct any
> mechanical problems before repeating the procedure.**"

If it does not close, stop. Do not recalibrate on top of a non-linear
system — it hides the symptom in the middle of the range and it will come
back. Look for: cables or hoses pulling on the platform, something rubbing,
a cell not seated coplanar, debris under the plate.

> ⚠️ "If the correction made changes the previous full scale for more than
> 20%, all the parameters with settable weight values are reset to default
> values." If you made a big correction, go back and re-check `0 SEt`,
> `MASS` and any setpoints.

### Step 5 — Persist and record

When calibrating over Modbus, the app sends command 99 at the final step to
write to EEPROM. When calibrating from the keypad, menu changes are applied
on `↵` as you go.

Record what you did: date, sample weights used, resulting full scale, and the
accumulated zero from step 2. The next person to touch this needs that
history to tell drift from a bad calibration.

---

## 7. What survives a power cycle

This table explains a whole class of "it decalibrated itself overnight"
reports, and it is not obvious from the app.

| Operation | Keypad / Modbus | Survives power-off? |
|---|---|---|
| Theoretical calibration | `FS-tEO`, `SEnSib`, `diUiS` | **Yes** |
| **Tare weight zero setting** | `2Er0` / command 100 | **Yes — permanent memory** |
| Real calibration with weights | `UEiGHt` / commands 101, 106 | **Yes** |
| Semi-automatic tare | `↵` key / command 7 | **No** |
| Semi-automatic zero | command 8 | **No** |
| Preset tare | `P-tArE` / command 130 | **No** |

The manual states it three separate times:

> "THE SEMI-AUTOMATIC TARE OPERATION IS LOST UPON INSTRUMENT POWER-OFF."
>
> "The zero-setting is lost upon instrument power-off."
>
> "ALL THE SEMI-AUTOMATIC TARE (NET) AND PRESET TARE FUNCTIONS WILL BE LOST
> WHEN THE INSTRUMENT IS TURNED OFF."

**What this means in practice.** The FFA app's Tare button sends command 7, a
semi-automatic tare. If someone uses it to cancel out the dead weight of a
permanently fitted tray, that correction disappears at the next power cut and
the tray's weight reappears in every reading.

**The rule:**

- Permanent dead load — the platform, a fixed tray — use **`2Er0`** once, at
  commissioning. It is stored in permanent memory.
- Transient per-batch tare — use the app's Tare button. Losing it on power-off
  is correct behaviour for something that is transient by design.

One more constraint the app does not currently check: "The semi-automatic
tare operation is not allowed if the gross weight is zero" — the instrument
answers with the `InZEr0` alarm instead.

---

## 8. Keypad ↔ Modbus equivalents

Register addresses are 0-based, i.e. the manual's number minus 40001. See
[`../WEIGHT_STABILITY.md`](../WEIGHT_STABILITY.md) for why that offset matters.

### Command register (40006 → address 5)

| Command | Keypad equivalent | Used by |
|---|---|---|
| 7 | Semi-automatic tare (`↵` key) | `setTare()` |
| 8 | Semi-automatic zero | `setZero()` |
| 9 | Tare disable, back to gross | `clearTare()` |
| 99 | Save data to EEPROM | `remote_calibration()` step 4 |
| 100 | Tare weight zero setting (`2Er0`) | `remote_calibration()` step 2 |
| 101 | Save first sample weight (`UEiGHt`) | `remote_calibration()` step 3 |
| 104 | Cancel real calibration | `cancel_calibration()` |
| 106 | Add sample weight, keeps previous | `add_calibration_point()` |

### Readable registers

| Manual | Address | Contents |
|---|---|---|
| 40007 | 6 | Status register |
| 40008 / 40009 | 7 / 8 | Gross weight H / L |
| 40010 / 40011 | 9 / 10 | Net weight H / L |
| 40012 / 40013 | 11 / 12 | Peak weight H / L |
| 40014 | 13 | Division index + unit of measure |
| 40037 / 40038 | 36 / 37 | Sample weight for calibration H / L |

Weight registers carry the **magnitude**; the sign is in the status register.

### An idea worth taking up

The instrument maintains the **peak** in hardware at full ADC rate
(40012/40013), regardless of how often the app polls. For a tear-force test
that is exactly the right measurement — you stop depending on catching the
instant with your sample timing. `readPeak()` is already implemented in
`TLB_MODBUS.py` but is not yet wired into the belly test.

---

## 9. Status register and alarms

Status register 40007 (address 6). The FFA app reads this on every poll and
surfaces it as `scale_status` over Socket.IO.

| Bit | Meaning | Display alarm |
|---|---|---|
| 0 | Load cell error | `ErCEL` |
| 1 | A/D converter malfunction | `Er Ad` |
| 2 | Max capacity exceeded by 9 divisions | `------` |
| 3 | Gross > 110% of full scale | `Er OL` |
| 4 | Gross beyond ±999999 | `Er OF` (on gross) |
| 5 | Net beyond ±999999 | `Er OF` (on net) |
| 7 | Gross weight negative sign | — |
| 8 | Net weight negative sign | — |
| 10 | Net display mode | — |
| **11** | **Weight stability** | — |
| 12 | Within ±¼ division of zero | — |

### What the display alarms mean

| Alarm | Cause |
|---|---|
| `ErCEL` | Cell not connected or wrongly connected; signal exceeds 39 mV; A/D malfunction; **4-wire cell without the EX−/REF− and EX+/REF+ jumpers**; references not connected |
| `Er OL` | Weight display exceeds 110% of full scale |
| `Er Ad` | Internal converter failure — check cell connections |
| `------` | Weight exceeds maximum capacity (`MASS`) by 9 divisions |
| `Er OF` | Value beyond ±999999 |
| `t-----` | Weight too high, zero setting not possible — exceeds `0 SEt` |
| `MAH-PU` | Eighth sample weight entered during real calibration |
| `Error` | Value out of permitted range. Includes "the weight value set in sample weight verification does not match the detected mV increase" |
| `bLOC` | Menu, keypad or display lock is active |
| `InZEr0` | Gross weight is zero, semi-automatic tare cannot be performed |
| `bUS Er` | Fieldbus device problem |

**The zero command failure is detectable.** When the weight exceeds `0 SEt`,
the manual says "the response to the zero command is a *value not valid*
error (**error code 3**)" — a Modbus exception, not silence. That means the
app can and should distinguish "the transmitter refused the zero" from "the
transmitter did not answer". Currently `setZero()` retries and then raises a
generic communication error, and the `set_zero` Socket.IO handler has no
error path back to the operator. Known gap, worth closing.

---

## 10. Troubleshooting

| Symptom | Most likely cause | What to do |
|---|---|---|
| Weight never settles, jitters constantly | Over-resolution | [Section 4.3](#43-the-over-resolution-check). If divisions > 20,000, no filter fixes it |
| Weight never settles, divisions are sane | Filter too low, or vibration | Raise `FiLtEr` to 5; confirm with `MU-CEL` whether the mV itself is moving |
| mV reading itself is unstable | Cell, cable, grounding, moisture | [Section 4.2](#42-load-cell-electrical-test) and [section 11](#11-installation-rules) |
| Zero drifts slowly over hours | Moisture, temperature, residue | Check the accumulated zero in `2Er0`; check the junction box for condensation |
| Reading offset appears after a power cut | Semi-automatic tare was lost | [Section 7](#7-what-survives-a-power-cycle) — use `2Er0` for permanent dead load |
| Reading offset appears after boot with load on platform | `AUt0 0` is not zero | Set `AUt0 0` to 0 |
| Zero button appears to do nothing | Drift exceeds `0 SEt` (default 30.0 g) | Check `0 SEt`; if you need more than that, fix the drift, don't raise the limit |
| Accurate at low weights, off at high weights | Calibrated with too small a sample weight | Recalibrate with ≥ 50% of max, multi-point |
| Removing weights doesn't return to zero | Mechanical non-linearity | Step 4 of [section 6](#6-calibration-procedure). Fix mechanics before recalibrating |
| Belly test misses the tear peak | Filter too high, anti-peak on | `FiLtEr` = 0, `AntPOF` on slave 2 |
| Communication timeouts, especially in belly test | Bus saturated at 9600 | Raise `bAUd` to 38400 **and** close the termination jumpers |
| `ErCEL` on a 4-wire cell | Missing jumpers | Jumper EX−/REF− and EX+/REF+ |

---

## 11. Installation rules

Straight from the manual's installation sections. These are the things no
amount of configuration can compensate for.

### Wiring

- **The cell cable enters the panel on its own route.** "The entry of the
  cell cable into the panel must be independent and the cable must not be
  routed with other cables in a conduit. It is usually connected directly to
  the instrument terminal board **without the interposition of additional
  terminal boards**." Intermediate terminal blocks are a leading cause of
  noise in these installations.
- **Do not put the instrument in a panel with inverters.** If unavoidable,
  the inverters need filters and separating plates.
- **RC filters on the coils** of contactors and solenoid valves driven by the
  instrument.
- **Grounding:** the instrument's ground terminals must be at the same
  potential as the weighed structure — same shaft or same grounding system.
  If unsure, run a ground wire between the instrument terminals (including
  `–SUPPLY`) and the structure. The power supply negative pole should be
  grounded.
- Parallel cells: sealed junction box, shielded extension cables in their own
  conduits, away from power lines, minimum 1 mm² for 4-wire.
- RS485 maximum length: 1000 m with AWG24 shielded twisted pair.

### Environment

- **Sealed cable sheaths and connectors** on cell cables.
- "If signs of condensation appear inside the devices, it is recommended
  **not to disconnect the devices from the power supply**." A powered
  instrument stays slightly warm and does not condense. If the line is shut
  down over a weekend in a chilled room, expect Monday drift.
- Keep away from heat sources and direct sunlight. Working temperature
  −20 °C to +60 °C, humidity 85% non-condensing.
- Do not wash with water jets unless it is the IP-rated version.

### Mechanical

- **Load cells to a maximum of 70–80% of rated capacity.**
- Cell bearing surfaces must be coplanar and rigid; use mounting accessories
  to compensate for non-parallel surfaces.
- Protect against lateral displacement, shock and vibration.
- Pipes and hoses: elastic couplings, and the pipe support at least 40× the
  pipe diameter away from the weighed structure.
- Do not weld on assembled load cells. If unavoidable, put the welder's earth
  clamp close to the weld so current does not pass through the cell body.

### Note on the flash

The FFA station fires the flash immediately before capture
(`ios.set_flash(True)`). If that puts a transient on the supply, the reading
during capture is the worst of the cycle. Gating the capture on the stability
bit covers part of this, but if you see a systematic offset between the live
weight and the captured weight, this is where to look.

---

## 12. Recommended settings summary

FFA-specific recommendations. Verify against your actual cell capacity and
weighing range before applying.

| Parameter | Slave 1 (weight) | Slave 2 (belly) | Why |
|---|---|---|---|
| `FiLtEr` | **4**, → 5 if jitter | **0** | Stability vs peak capture |
| anti-peak | **`AntPOn`** | **`AntPOF`** | A tear is a sub-second event |
| `AUt0 0` | **0** | **0** | Prevents taring out a load present at boot |
| `trAC 0` | **2** | `nOnE` | 0.2 g of drift correction; currently off by default |
| `0 SEt` | review | review | Default = 30.0 g with a 0.1 division |
| `MASS` | your real max | your real max | Enables the overload alarm the app now reads |
| `bAUd` | **38400** | **38400** | Requires termination jumpers |
| `Addr` | 1 | 2 | As wired |
| `dELAY` | **0** | **0** | Default; no reason to add latency |
| `PArity` | none | none | Matches the app |
| `StOP` | **1** | **1** | Instrument default; align the app to match |

### Related app settings

| Env var | Default | Note |
|---|---|---|
| `TLB_BAUDRATE` | 9600 | Must match `bAUd` |
| `TLB_CALIB_SAMPLE_GRAMS` | 1000.0 | **Set to ≥ 50% of your heaviest fish** |
| `TLB_TIMEOUT` | 0.2 | Response timeout |
| `WEIGHT_POLL_INTERVAL` | 0.25 | Weight sampling period |
| `TENSION_POLL_INTERVAL` | 0.05 | Tension sampling period |

---

## See also

- [`../WEIGHT_STABILITY.md`](../WEIGHT_STABILITY.md) — the register map fix,
  status register handling, and what changed in the code.
- `tools/scale_diagnostics.py` — logs raw registers to CSV and classifies the
  behaviour as jitter, drift or discrete jumps. Run it before and after any
  change to this configuration.
- `tests/test_tlb_registers.py` — verifies the register map against a fake
  transmitter built to the manual's layout.

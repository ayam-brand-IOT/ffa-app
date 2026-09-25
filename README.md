# ffa-app

Servicio Python que opera la parte local del sistema FFA: hardware, vision, video en vivo, configuracion de parametros y WebSocket hacia la interfaz.

## Responsabilidades

- leer peso desde el transmisor o desde emuladores
- controlar flash y laser via GPIO o emuladores
- capturar imagen y ejecutar analisis con OpenCV
- exponer video en vivo y la ultima imagen analizada
- servir la SPA compilada del frontend cuando existe `dist/`
- publicar datos en tiempo real por Socket.IO

`ffa-app` escucha en `http://localhost:3030`.

La conversion de peso, la codificacion de calibracion y la espera cooperativa
del puerto RS485 estan integradas en `TLB_MODBUS.py`. No requieren scripts de
parcheo. Con una division de 0.5 g, el registro 10000 representa 1000.0 g;
la calibracion con una masa de 1000 g envia 10000. Tras actualizar el codigo,
reconstruir la imagen Docker y recrear el contenedor: reiniciarlo solamente
no instala la nueva imagen. Conservar la configuracion y las muestras antes
de reemplazar un contenedor sin volumenes persistentes.

## Calibration Diagnostics Branch

`codex/calibration-diagnostics` builds on `new_image_process_hugo_fix`
(`4c0f900`). This is a **diagnostic backend branch, not a production-approved
calibration release**. It does not modify the frontend, `ffa-server`, or the
parent repository.

### Changes

- Added `get_scale_diagnostics` for fresh raw registers, firmware/type IDs,
  status bits, unit/division, NET, GROSS, and their difference. It uses the
  backend's existing serial connection and never reads the write-only command
  register or substitutes stale data for a failed diagnostic read.
- Added `TLB_STATUS_MAP_VERIFIED`, defaulting to `false`. Calibration entry
  points are blocked until the installed status map is verified; ordinary
  weight polling remains available. This flag does not select another map.
- Enforced ordered calibration steps for the same instrument, using its own
  unit/division rather than the primary scale's cached settings. The guided
  workflow accepts grams only and rejects instrument faults, active tare,
  missing reference loads, and configuration changes.
- Added fresh NET/GROSS checks after calibration zero (`100`), after the first
  reference (`101`), and before/after EEPROM save (`99`). Consumed sample
  registers alone are no longer treated as proof of successful calibration.
- Added correlated calibration replies (`step`, `args`, `request_id`, and a
  diagnostic snapshot), rejected overlapping operations, and deferred session
  release until an in-flight command finishes after disconnect/cancellation.
  Tare, operational zero, and mode changes are blocked during a session.
- Added hardware-free regressions for the original NET/GROSS mismatch, ignored
  commands, stale reads, invalid sequences, ownership/cancellation, observed
  status words, and the one-gram reference deviation.

The inherited decimal encoding and single-attempt command writes are retained.
With division `0.5 g`, register value `10000` represents `1000.0 g`, not 5000 g.
A lost command response is never automatically replayed, and an applied
hardware command is not rolled back merely because a later check fails.

### Bench Results and Remaining Limits

Supervised tests took place on the debugging station on September 24, 2026
(America/Tijuana; some evidence timestamps are September 25 UTC). The permanent
lamp/frame remained installed. The bottle was assigned a 1000 g reference;
its actual mass has not been independently certified.

| Observation | GROSS (g) | NET (g) |
| --- | ---: | ---: |
| Initial fault, bottle installed | 1000.0 | 883.5 |
| Structure only, after explicitly clearing semi-automatic tare (`9`) | 117.0 | 117.0 |
| Structure only, after calibration zero (`100`) | 0.0 | 0.0 |
| Bottle immediately before setting the reference | 886.0 | 886.0 |
| Bottle after reference (`101`), reloading, and save (`99`) | 1000.0 | 1000.0 |
| Structure only after reference, before power cycling | -0.5 | -0.5 |
| Bottle after operator-reported transmitter power cycle, 30 stable readings | 999.0 | 999.0 |
| Structure only after that power cycle, 30 stable readings | 0.0 | 0.0 |

Commands `100`, `101`, and `99` were each sent once and acknowledged. Reference
registers were read back as `[0, 10000]` before `101` and `[0, 0]` afterward.
These were supervised, isolated serial operations with the normal backend
paused and restored, **not an end-to-end validation of the UI wizard**.

Post-restart readings are consistent with retained calibration, but **999.0 g
is two divisions below the assigned reference**, outside the guided workflow's
one-division (`+/-0.5 g`) check. Its cause remains unresolved; returning to zero
does not explain or waive that deviation. No corrective tare or recalibration
was applied to hide it. Absolute accuracy and production readiness are not
established by this test.

Keep `TLB_STATUS_MAP_VERIFIED=false` on the diagnostic deployment. The current
frontend still needs correlated reply/error handling and must not announce
completion before the save step succeeds. See
[Calibration Diagnostics](docs/CALIBRATION_DIAGNOSTICS.md) for status-map
evidence, the test sequence, deployment precautions, and remaining work.

### Focused Regression Tests

Run each script in a separate process because some fixtures install mock
modules in `sys.modules`:

```bash
python3 tests/test_calibration_diagnostics.py
python3 tests/test_calibration_socket_guard.py
python3 tests/test_tlb_registers.py
python3 tests/test_tlb_safety.py
python3 tests/test_socket_availability.py
python3 tests/test_scale_controls.py
python3 tests/test_image_process_safety.py
```

The last two suites require Eventlet and OpenCV/NumPy respectively. These
hardware-free tests do not certify physical accuracy or firmware compatibility.

## Reproducible Transmitter Setup

Use `python3 tools/tlb_setup.py` for the keypad setup checklist. The tool can
create a reusable target profile and verify fresh weight readings on each
station through the running backend, without opening another serial connection
or writing transmitter parameters. Capacity/sensitivity must come from the
installed cell, and each assembled station needs its own zero and calibration.
Keypad targets are not falsely reported as measured settings. See the English
[Setup Guide](docs/TLB_SETUP.md) for commands, connection-output warnings,
exit codes, and the unresolved post-power-cycle reference deviation.

```sh
python3 tools/tlb_setup.py
python3 tools/tlb_setup.py init --profile /tmp/ffa-weight-profile.json
python3 tools/tlb_setup.py check --profile /tmp/ffa-weight-profile.json \
  --expected-g 0 --report /tmp/ffa-zero-check.json --ack-connection-outputs
python3 tests/test_tlb_setup.py
```

Clear the laser area before the online check: the existing backend connection
handler turns the laser on and the flash off. A passing automatic check does
not certify the manual keypad settings or approve production use.

## Archivos principales

```text
ffa-app/
├── main.py
├── app.py
├── routes.py
├── sockets.py
├── hardware.py
├── imageProcess.py
├── vision_config.json
├── requirements.txt
├── Dockerfile
├── dist/
├── docs/
├── tests/
├── tools/
└── services/
    └── config_service.py
```

## Modos de operacion

`hardware.py` selecciona el backend segun `DEV_MODE`:

- `DEV_MODE=true`: usa `TLB_MODBUS_dev.py` e `IOs_dev.py`
- `DEV_MODE=false`: usa `TLB_MODBUS.py` e `IOs.py`

Si no se define la variable, el valor por defecto del codigo es `true`.

## Instalacion local

```bash
cd ffa-app
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables de entorno relevantes

El codigo consulta principalmente:

- `DEV_MODE`

El `docker-compose` tambien define:

- `RS485_PORT`
- `WEBCAM_DEVICE`
- `FLASH_PIN`
- `LASER_PIN`
- `UI_PORT`

La captura sincronizada con flash acepta estos ajustes opcionales:

- `FLASH_SETTLE_SECONDS`: pausa corta despues de encender el flash. Valor por defecto: `0.03`
- `FLASH_FRAME_SKIP`: cantidad de frames nuevos que espera despues de encender el flash. Valor por defecto: `2`
- `FLASH_FRAME_TIMEOUT`: timeout maximo para esperar frames frescos. Valor por defecto: `0.35`
- `CAMERA_RETRY_INITIAL`: espera inicial para reabrir una camara desconectada. Valor por defecto: `0.5`
- `CAMERA_RETRY_MAX`: espera maxima entre intentos de reconexion. Valor por defecto: `10.0`
- `CAMERA_READ_FAILURE_LIMIT`: lecturas fallidas antes de reabrir el dispositivo. Valor por defecto: `3`
- `VIDEO_NO_FRAME_BACKOFF`: pausa del stream cuando no hay frame. Valor por defecto: `0.1`
- `VIDEO_FRAME_BACKOFF`: limite aproximado de ritmo del stream. Valor por defecto: `0.03`

El transmisor de peso (TLB, Modbus-RTU) acepta:

- `TLB_PORT`: puerto serie. Valor por defecto: `/dev/ttyUSB0`
- `TLB_BAUDRATE`: velocidad del bus RS485. Valor por defecto: `9600`
- `TLB_TIMEOUT`: timeout de respuesta en segundos. Valor por defecto: `0.2`
- `TLB_RETRIES`: reintentos por transaccion. Valor por defecto: `2`
- `TLB_RETRY_DELAY`: back-off entre reintentos. Valor por defecto: `0.02`
- `TLB_STALE_MAX_AGE_SECONDS`: antiguedad maxima de un peso reutilizable tras perder comunicacion. Valor por defecto: `2.0`
- `TLB_CALIB_SAMPLE_GRAMS`: peso patron de la calibracion guiada. Valor por defecto: `1000.0`
- `TLB_STATUS_MAP_VERIFIED`: explicit confirmation of the installed legacy status map; default `false`. Do not enable merely to bypass the calibration gate.
- `TLB_STATUS_MAP_VERIFIED_SLAVES`: comma-separated slaves whose status map was verified (e.g. `1`); only unlocks them while they report firmware/type `11102/105`. See [Calibration Diagnostics](docs/CALIBRATION_DIAGNOSTICS.md).
- `WEIGHT_POLL_INTERVAL`: periodo de muestreo de peso. Valor por defecto: `0.1`
- `TENSION_POLL_INTERVAL`: periodo de muestreo de tension. Valor por defecto: `0.05`
- `SCALE_ERROR_BACKOFF`: espera tras un error de lectura. Valor por defecto: `1.0`
- `CALIBRATION_LEASE_SECONDS`: inactividad permitida antes de liberar una calibracion abandonada. Valor por defecto: `300`

Estas variables dependen de la implementacion concreta de los modulos de hardware.

## Peso: estabilidad y calibracion

- [`docs/tlb/README.md`](docs/tlb/README.md) — guia completa del transmisor:
  navegacion del teclado, mapa de menus, diagnostico, referencia de parametros,
  procedimiento de calibracion paso a paso y troubleshooting.
- [`docs/WEIGHT_STABILITY.md`](docs/WEIGHT_STABILITY.md) — el mapa de registros
  del TLB, el uso del STATUS REGISTER y que cambio en el codigo.

Diagnostico en planta:

```bash
python3 tools/scale_diagnostics.py --duration 600 --interval 0.2
```

Verificacion del mapa de registros sin hardware:

```bash
python3 tests/test_tlb_registers.py
```

## Arranque

### Desarrollo sin hardware

```bash
DEV_MODE=true python main.py
```

### Produccion con hardware real

```bash
DEV_MODE=false python main.py
```

El servicio arranca con Eventlet y expone Flask + Socket.IO en `0.0.0.0:3030`.

## Integracion con la interfaz

- en desarrollo, normalmente la UI corre aparte con `npm run serve`
- en despliegue, `app.py` sirve archivos desde:
  - `./dist/index.html`
  - `./dist/static/`

Nota importante: el repo actual solo trae `ffa-app/dist/.gitkeep`. Para servir la UI desde `ffa-app`, primero hay que compilar `user-interface` y copiar su salida dentro de `ffa-app/dist/`.

## Endpoints HTTP

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `GET` | `/` y `/<path>` | Catch-all para servir la SPA |
| `GET` | `/video_feed` | Stream MJPEG de la camara |
| `GET` | `/analyzed_image` | Ultima imagen analizada como JPEG simple |
| `POST` | `/length_calibration` | Guarda la relacion px/mm |
| `POST` | `/calibrate_zoi` | Guarda la zona de interes |
| `GET` | `/get_config` | Regresa `vision_config.json` |
| `POST` | `/update_config` | Actualiza `tailTrigger` o parametros por especie/tipo |
| `POST` | `/update_fish_params` | Aplica a runtime los parametros de una especie/tipo |

## Eventos Socket.IO

### Eventos recibidos desde la UI

- `calibrate_load_cell`
- `resume_net_update`
- `enter_to_tension_test`
- `enter_to_weight_mode`
- `set_zero`
- `set_tare`
- `clear_tare`
- `update_net`
- `get_tension`
- `get_scale_status`
- `get_scale_diagnostics` - fresh raw-register diagnostics using the existing serial connection
- `get_analysis_data`
- `capture`
- `reset`
- `reset_defects`
- `laser`
- `set_fish_data`

### Eventos emitidos hacia la UI

- `weight_update`
- `tension_update`
- `scale_status` — valor, estabilidad (bit 11 del STATUS REGISTER) y fallas del instrumento
- `scale_error` — el poller no pudo leer el transmisor
- `scale_diagnostics` / `scale_diagnostics_error` - fresh diagnostic result or explicit failure
- `frame_ready`
- `analysis_data`
- `analysis_error` — el analisis no produjo una medicion valida; la UI **no** debe
  mostrar la medicion anterior como si fuera nueva
- `calibration_step_commited`
- `calibration_error`
- `fishParamsResponse`

## Configuracion de vision

`vision_config.json` persiste:

- `zoi`
- `species_params`
- `ppmm`
- `tailTrigger`
- `current_fish_params`

`services/config_service.py` es la capa que lee, valida y escribe ese archivo.

## Dependencias principales

- Flask 2.3
- Flask-SocketIO 5.3
- Eventlet
- OpenCV
- NumPy
- minimalmodbus
- pyserial
- gpiozero
- pigpio
- lgpio

Consulta la lista exacta en [requirements.txt](./requirements.txt).

## Docker

```bash
docker build -t ffa-app ./ffa-app
docker run -p 3030:3030 -e DEV_MODE=true ffa-app
```

El compose del repo raiz esta pensado para correrlo junto con `ffa-server`.

## Logs y documentacion adicional

- [Calibration handoff: September 25, 2026](./docs/CALIBRATION_HANDOFF_2026-09-25.md):
  latest debug-station measurements, zero repair, remaining failed power-cycle
  reference check, deployment state, and next steps. Not production approval.

Este modulo incluye documentacion especifica del subsistema de logs:

- [Logging README](./docs/logging/README.md)
- [Logging Quickstart](./docs/logging/QUICKSTART.md)
- [Logging Standard](./docs/logging/STANDARD.md)
- [Logging Implementation](./docs/logging/IMPLEMENTATION.md)
- [Logging Implementation Summary](./docs/logging/IMPLEMENTATION_SUMMARY.md)
- [Performance Optimizations](./docs/performance/OPTIMIZATIONS.md)
- [Flash Capture Tuning](./docs/FLASH_CAPTURE_TUNING.md)

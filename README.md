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

Estas variables dependen de la implementacion concreta de los modulos de hardware.

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
- `update_net`
- `get_tension`
- `get_analysis_data`
- `capture`
- `reset`
- `reset_defects`
- `laser`
- `set_fish_data`

### Eventos emitidos hacia la UI

- `weight_update`
- `tension_update`
- `frame_ready`
- `analysis_data`
- `calibration_step_commited`
- `calibration_error`

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

Este modulo incluye documentacion especifica del subsistema de logs:

- [Logging README](./docs/logging/README.md)
- [Logging Quickstart](./docs/logging/QUICKSTART.md)
- [Logging Standard](./docs/logging/STANDARD.md)
- [Logging Implementation](./docs/logging/IMPLEMENTATION.md)
- [Logging Implementation Summary](./docs/logging/IMPLEMENTATION_SUMMARY.md)
- [Performance Optimizations](./docs/performance/OPTIMIZATIONS.md)

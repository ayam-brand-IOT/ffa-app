# Sistema de Logging FFA Application

## 📋 Descripción

Sistema de logging robusto para capturar y registrar todos los eventos importantes de la aplicación FFA. Los logs se almacenan en formato JSON para facilitar el análisis y debugging.

## 📂 Ubicación de Logs

```
ffa-app/
├── logs/
│   └── ffa_app_events.log    # Archivo principal de logs
└── logger.py                  # Módulo de logging
```

## 📊 Estructura de Log Entry

Cada evento registrado contiene la siguiente información:

```json
{
  "timestamp": "2025-11-25T10:30:45.123456",
  "lote_id": "LOT-2025-001",
  "proveedor_id": "PROV-123",
  "etapa": "CAPTURE",
  "status": "SUCCESS",
  "fish_params": {
    "species": "MACK",
    "type": "HG",
    "parameters": {
      "A": 12,
      "B": null,
      "C": 24
    }
  },
  "vision_params": {
    "zoi": [...],
    "ppmm": 0.23,
    "tailTrigger": 40
  },
  "version_app": "1.0.0",
  "error_code": null,
  "error_msg": null,
  "additional_data": {
    "weight": 125.5,
    "analysis_results": {...}
  }
}
```

## 🔑 Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Momento exacto del evento |
| `lote_id` | string \| null | Identificador del lote actual |
| `proveedor_id` | string \| null | Identificador del proveedor |
| `etapa` | string | Etapa del proceso (ver sección Etapas) |
| `status` | string | Estado del evento: SUCCESS, ERROR, WARNING, INFO |
| `fish_params` | object \| null | Parámetros de pez (especie, tipo, parámetros) |
| `vision_params` | object \| null | Parámetros de visión (zoi, ppmm, tailTrigger) |
| `version_app` | string | Versión de la aplicación |
| `error_code` | string \| null | Código de error si aplica |
| `error_msg` | string \| null | Mensaje de error descriptivo |
| `additional_data` | object \| null | Datos adicionales específicos del evento |

## 🎯 Etapas (Stages)

Las etapas disponibles son:

- **CAPTURE**: Captura de imagen
- **ANALYSIS**: Análisis de imagen
- **WEIGHT**: Medición de peso
- **CONFIG_UPDATE**: Actualización de configuración
- **CALIBRATION**: Calibraciones (peso, longitud, ZOI)
- **RESET**: Reset de sistema
- **SYSTEM**: Eventos del sistema (inicio, parada, etc.)

## ✅ Estados (Status)

- **SUCCESS**: Operación exitosa
- **ERROR**: Error en la operación
- **WARNING**: Advertencia
- **INFO**: Información general

## 🚀 Uso del Logger

### Importar el logger

```python
from logger import logEvent, get_logger
```

### Uso básico con `logEvent()`

```python
# Evento simple
logEvent(
    etapa="CAPTURE",
    status="SUCCESS"
)

# Evento con información completa
logEvent(
    etapa="ANALYSIS",
    status="SUCCESS",
    lote_id="LOT-2025-001",
    proveedor_id="PROV-123",
    fish_params={
        "species": "MACK",
        "type": "HG",
        "parameters": {"A": 12, "B": None, "C": 24}
    },
    vision_params={
        "ppmm": 0.23,
        "tailTrigger": 40
    },
    additional_data={
        "length": 25.5,
        "weight": 125.3
    }
)

# Registrar un error
logEvent(
    etapa="CAPTURE",
    status="ERROR",
    lote_id="LOT-2025-001",
    error_code="CAMERA_TIMEOUT",
    error_msg="La cámara no respondió después de 5 segundos"
)
```

### Uso avanzado con métodos especializados

```python
logger = get_logger()

# Log de captura
logger.log_capture(
    status="SUCCESS",
    lote_id="LOT-2025-001"
)

# Log de análisis
logger.log_analysis(
    status="SUCCESS",
    lote_id="LOT-2025-001",
    fish_params={"species": "MACK", "type": "HG"},
    analysis_results={"length": 25.5, "defects": []}
)

# Log de peso
logger.log_weight(
    status="SUCCESS",
    weight_value=125.5,
    lote_id="LOT-2025-001"
)

# Log de actualización de configuración
logger.log_config_update(
    status="SUCCESS",
    config_type="fish_parameters",
    old_values={"A": 10, "B": 15},
    new_values={"A": 12, "B": 18}
)

# Log de calibración
logger.log_calibration(
    status="SUCCESS",
    calibration_type="length",
    calibration_data={"ratio": 0.23}
)

# Log de evento del sistema
logger.log_system_event(
    status="INFO",
    event_type="app_startup",
    description="Aplicación iniciada correctamente"
)

# Log de error genérico
logger.log_error(
    etapa="ANALYSIS",
    error_code="INVALID_IMAGE",
    error_msg="La imagen capturada está corrupta",
    lote_id="LOT-2025-001"
)
```

## 📊 Visualización de Logs

### Script de visualización

Se incluye un script `view_logs.py` para analizar los logs:

```bash
# Ver últimos 50 logs + estadísticas
python tools/logging/view_logs.py

# Ver todos los logs
python tools/logging/view_logs.py all

# Ver solo estadísticas
python tools/logging/view_logs.py stats

# Ver solo errores
python tools/logging/view_logs.py errors

# Ver solo eventos exitosos
python tools/logging/view_logs.py success

# Filtrar por etapa
python tools/logging/view_logs.py capture      # Solo capturas
python tools/logging/view_logs.py config       # Solo configuración
python tools/logging/view_logs.py calibration  # Solo calibraciones
python tools/logging/view_logs.py system       # Solo eventos del sistema
```

### Salida de ejemplo

```
✅ [2025-11-25T10:30:45.123456] CAPTURE - SUCCESS
   📦 Lote: LOT-2025-001
   📱 Version: 1.0.0

❌ [2025-11-25T10:31:12.789012] ANALYSIS - ERROR
   📦 Lote: LOT-2025-001
   🔴 Error Code: INVALID_IMAGE
   💬 Error Msg: La imagen capturada está corrupta
   📱 Version: 1.0.0
```

## 📈 Estadísticas

El script genera estadísticas automáticas:

```
📊 ESTADÍSTICAS DE LOGS
============================================================

📈 Total de eventos: 150

📊 Por Status:
   ✅ SUCCESS: 135 (90.0%)
   ❌ ERROR: 10 (6.7%)
   ⚠️ WARNING: 3 (2.0%)
   ℹ️ INFO: 2 (1.3%)

📊 Por Etapa:
   • CAPTURE: 45 (30.0%)
   • ANALYSIS: 43 (28.7%)
   • WEIGHT: 42 (28.0%)
   • CONFIG_UPDATE: 15 (10.0%)
   • CALIBRATION: 5 (3.3%)
```

## 🔍 Análisis de Logs con Herramientas Externas

### jq (Recomendado)

```bash
# Ver todos los errores
cat logs/ffa_app_events.log | jq 'select(.status == "ERROR")'

# Contar eventos por etapa
cat logs/ffa_app_events.log | jq -r '.etapa' | sort | uniq -c

# Ver eventos de un lote específico
cat logs/ffa_app_events.log | jq 'select(.lote_id == "LOT-2025-001")'

# Ver eventos del último día
cat logs/ffa_app_events.log | jq 'select(.timestamp > "2025-11-24")'
```

### Python

```python
import json

# Leer y analizar logs
with open('logs/ffa_app_events.log', 'r') as f:
    events = [json.loads(line) for line in f if line.strip()]

# Filtrar errores
errors = [e for e in events if e['status'] == 'ERROR']

# Agrupar por etapa
from collections import Counter
etapas = Counter(e['etapa'] for e in events)
print(etapas)
```

## 🛠️ Códigos de Error Comunes

| Código | Descripción |
|--------|-------------|
| `CAPTURE_ERROR` | Error durante la captura de imagen |
| `ANALYSIS_ERROR` | Error durante el análisis de imagen |
| `CAMERA_TIMEOUT` | La cámara no respondió |
| `INVALID_IMAGE` | Imagen corrupta o inválida |
| `CONFIG_READ_ERROR` | Error al leer archivo de configuración |
| `CONFIG_WRITE_ERROR` | Error al escribir archivo de configuración |
| `SPECIES_NOT_FOUND` | Especie o tipo no encontrado |
| `LOAD_CELL_CALIB_ERROR` | Error en calibración de celda de carga |
| `LENGTH_CALIB_ERROR` | Error en calibración de longitud |
| `ZOI_CALIB_ERROR` | Error en calibración de ZOI |
| `APP_CRASH` | Crash de la aplicación |

## 🔄 Rotación de Logs

Para evitar que el archivo de log crezca indefinidamente, se recomienda implementar rotación:

```bash
# Opción 1: Rotar manualmente
mv logs/ffa_app_events.log logs/ffa_app_events_$(date +%Y%m%d).log

# Opción 2: Usar logrotate (Linux)
# Crear /etc/logrotate.d/ffa-app
/path/to/ffa-app/logs/ffa_app_events.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
}
```

## 🚨 Monitoreo en Tiempo Real

```bash
# Ver logs en tiempo real
tail -f logs/ffa_app_events.log | jq .

# Ver solo errores en tiempo real
tail -f logs/ffa_app_events.log | jq 'select(.status == "ERROR")'

# Alertas de errores
tail -f logs/ffa_app_events.log | while read line; do
    echo $line | jq -e '.status == "ERROR"' > /dev/null && \
    echo "🚨 ERROR DETECTADO: $(echo $line | jq -r '.error_msg')"
done
```

## 📝 Mejores Prácticas

1. **Registrar contexto suficiente**: Incluir `lote_id`, `proveedor_id` cuando aplique
2. **Usar códigos de error descriptivos**: Facilita el debugging
3. **Incluir datos adicionales**: `additional_data` para información específica
4. **Mantener consistencia**: Usar las mismas etapas y códigos de error
5. **Log de inicio/fin**: Registrar eventos de sistema importantes
6. **No registrar información sensible**: Evitar passwords, tokens, etc.

## 🐛 Debugging

Para debugging detallado, el logger también imprime a consola (nivel WARNING y ERROR por defecto).

Para ver todos los logs en consola durante desarrollo:

```python
import logging
logging.getLogger('FFA_EventLogger').setLevel(logging.DEBUG)
```

## 📦 Backup de Logs

```bash
# Comprimir logs antiguos
gzip logs/ffa_app_events_*.log

# Backup semanal
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

## 🎓 Ejemplos de Integración

Ver `main.py` para ejemplos completos de integración del logger en:
- Captura de imágenes
- Análisis de imágenes
- Calibraciones
- Actualización de configuración
- Manejo de errores

---

**Versión**: 1.0.0  
**Última actualización**: 2025-11-25

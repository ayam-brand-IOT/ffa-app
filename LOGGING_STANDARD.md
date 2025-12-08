# 📋 Estándar de Logging - FFA Application

## Descripción General

El sistema de logging de FFA está estandarizado con vocabulario congelado (`log_constants.py`) y validación automática para garantizar consistencia y facilitar el análisis de eventos.

**Versión del Vocabulario:** `1.0.0`

---

## 🎯 Uso Básico

```python
from logger import logEvent

# Log de evento exitoso
logEvent(
    etapa="CAPTURE",
    status="SUCCESS",
    additional_data={"action": "capture_completed"}
)

# Log de error con código estándar
logEvent(
    etapa="CALIBRATION",
    status="ERROR",
    error_code="LOAD_CELL_CALIB_ERROR",  # descripción se auto-completa
    additional_data={"step": 1}
)

# Log con validación estricta (lanza excepción si vocabulario inválido)
logEvent(
    etapa="CAPTURE",
    status="SUCCESS",
    strict_validation=True  # Modo estricto
)
```

---

## 📦 Vocabulario Permitido

### 1. STATUS (4 valores)

| Status | Descripción | Cuándo usar |
|--------|-------------|-------------|
| `INFO` | Información general | Eventos informativos, inicio de procesos |
| `SUCCESS` | Operación exitosa | Operación completada sin errores |
| `WARNING` | Advertencia | Situaciones que requieren atención pero no impiden continuar |
| `ERROR` | Error | Errores que impiden completar una operación |

### 2. ETAPAS (10 valores)

| Etapa | Descripción | Contexto de uso |
|-------|-------------|-----------------|
| `SYSTEM` | Eventos de sistema | Startup, shutdown, inicialización de hardware |
| `CALIBRATION` | Calibraciones | Calibración de celda de carga, longitud, ZOI, zero, tare |
| `CONFIG_UPDATE` | Actualización de configuración | Modificación de parámetros de visión, especies, tailTrigger |
| `INICIO_LOTE` | Inicio de lote | Creación de nuevo lote de muestras |
| `MUESTRA` | Procesamiento de muestra | Eventos relacionados con muestras individuales |
| `CAPTURE` | Captura de imagen | Inicio/fin de captura, activación de flash/láser |
| `ANALISIS` | Análisis de imagen | Procesamiento de visión artificial, detección de defectos |
| `GUTS_WEIGHT` | Peso de vísceras | Lectura de peso de vísceras |
| `CIERRE_LOTE` | Cierre de lote | Finalización y guardado de lote |
| `RESET` | Reseteo | Limpieza de datos, reset de calibración |

### 3. ERROR_CODES (38 códigos estándar)

#### Errores de Sistema
- `APP_CRASH` - Crash inesperado de la aplicación
- `APP_STARTUP_ERROR` - Error al iniciar la aplicación
- `MEMORY_ERROR` - Error de memoria insuficiente
- `HARDWARE_NOT_AVAILABLE` - Hardware no disponible (modo emulado)

#### Errores de Calibración
- `LOAD_CELL_CALIB_ERROR` - Error en calibración de celda de carga
- `LENGTH_CALIB_ERROR` - Error en calibración de longitud
- `ZOI_CALIB_ERROR` - Error en calibración de zona de interés
- `CALIBRATION_TIMEOUT` - Timeout en proceso de calibración

#### Errores de Captura
- `CAPTURE_ERROR` - Error general en captura
- `CAPTURE_TIMEOUT` - Timeout esperando condiciones de captura
- `CAMERA_NOT_FOUND` - Cámara no detectada
- `IMAGE_CORRUPTED` - Imagen corrupta o inválida
- `NO_FISH_DETECTED` - No se detectó pescado en la imagen

#### Errores de Configuración
- `CONFIG_READ_ERROR` - Error al leer archivo de configuración
- `CONFIG_WRITE_ERROR` - Error al escribir archivo de configuración
- `INVALID_CONFIG_FORMAT` - Formato de configuración inválido
- `CONFIG_UNEXPECTED_ERROR` - Error inesperado en configuración
- `SPECIES_NOT_FOUND` - Especie/tipo no encontrado en configuración

#### Errores de Base de Datos
- `DB_CONNECTION_ERROR` - Error de conexión a base de datos
- `DB_READ_ERROR` - Error al leer de base de datos
- `DB_WRITE_ERROR` - Error al escribir en base de datos

#### Errores de Lote
- `LOTE_CREATION_ERROR` - Error al crear lote
- `LOTE_NOT_FOUND` - Lote no encontrado
- `LOTE_ALREADY_CLOSED` - Lote ya cerrado
- `LOTE_CLOSE_ERROR` - Error al cerrar lote

#### Errores de Muestra
- `MUESTRA_SAVE_ERROR` - Error al guardar muestra
- `MUESTRA_VALIDATION_ERROR` - Error de validación de muestra
- `DUPLICATE_MUESTRA` - Muestra duplicada
- `INVALID_MEASUREMENTS` - Mediciones inválidas

#### Errores de Hardware
- `MODBUS_CONNECTION_ERROR` - Error de conexión Modbus
- `SENSOR_ERROR` - Error de sensor
- `GPIO_ERROR` - Error de GPIO
- `WEIGHT_READ_ERROR` - Error al leer peso
- `WEIGHT_TIMEOUT` - Timeout esperando estabilización de peso
- `WEIGHT_UNSTABLE` - Peso inestable (no permite captura)

#### Errores de Procesamiento
- `VISION_PROCESSING_ERROR` - Error en procesamiento de visión
- `ANALYSIS_ERROR` - Error en análisis de imagen

#### Otros
- `RESET_ERROR` - Error en proceso de reset

> 💡 **Auto-completado:** Si proporcionas un `error_code` sin `error_msg`, la descripción se auto-completa desde el diccionario de códigos.

### 4. Tipos de Calibración

- `load_cell` - Calibración de celda de carga
- `length` - Calibración de longitud (px/mm)
- `zoi` - Calibración de zona de interés
- `zero` - Ajuste de punto cero
- `tare` - Tara de peso
- `tare_belly` - Tara para peso de vísceras
- `physical` - Calibración física
- `remote` - Calibración remota

### 5. Tipos de Configuración

- `fish_parameters` - Parámetros de especie
- `vision_parameters` - Parámetros de visión
- `tail_trigger` - Configuración de trigger de cola
- `system_settings` - Configuración de sistema

### 6. Eventos de Sistema

- `app_startup` - Inicio de aplicación
- `app_shutdown` - Cierre de aplicación
- `app_crash` - Crash de aplicación
- `camera_init` - Inicialización de cámara
- `modbus_init` - Inicialización Modbus
- `gpio_init` - Inicialización GPIO
- `enter_weight_mode` - Entrada a modo peso
- `enter_tension_mode` - Entrada a modo tensión

### 7. Acciones de Captura

- `capture_started` - Inicio de captura
- `capture_completed` - Captura completada
- `flash_triggered` - Flash activado
- `laser_on` - Láser encendido
- `laser_off` - Láser apagado

### 8. Acciones de Reset

- `reset_completed` - Reset completado
- `reset_defects` - Reset de defectos
- `reset_calibration` - Reset de calibración

---

## 🔧 Estructura de Log

### Campos Requeridos
- `timestamp` - Timestamp ISO 8601 (auto-generado)
- `etapa` - Una de las 10 etapas permitidas
- `status` - Uno de los 4 status permitidos
- `version_app` - Versión de aplicación (auto-incluido)

### Campos Opcionales
- `lote_id` - ID del lote actual
- `proveedor_id` - ID del proveedor
- `error_code` - Código de error estándar (requerido si status=ERROR)
- `error_msg` - Mensaje de error (auto-completado desde error_code)
- `fish_params` - Parámetros de especie
- `vision_params` - Parámetros de visión
- `additional_data` - Datos adicionales contextuales

### Ejemplo de Log JSON

```json
{
  "timestamp": "2025-12-08T15:47:55.869693",
  "lote_id": null,
  "proveedor_id": null,
  "etapa": "CALIBRATION",
  "status": "SUCCESS",
  "fish_params": null,
  "vision_params": null,
  "version_app": "1.0.0",
  "error_code": null,
  "error_msg": null,
  "additional_data": {
    "calibration_type": "load_cell",
    "step": 1
  }
}
```

---

## ⚙️ Validación

### Modo Normal (Default)

Por defecto, la validación es **permisiva** con advertencias:

```python
logEvent(
    etapa="INVALID_STAGE",  # ⚠️ Genera advertencia en log, pero continúa
    status="INFO"
)
```

**Salida en log:**
```
2025-12-08 15:47:55 - WARNING - VALIDACIÓN: Etapa 'INVALID_STAGE' no permitida. 
Valores permitidos: ANALISIS, CALIBRATION, CAPTURE, ...
```

### Modo Estricto

Para validación estricta que lance excepciones:

```python
try:
    logEvent(
        etapa="INVALID_STAGE",
        status="INFO",
        strict_validation=True  # 🔥 Lanza LogValidationError
    )
except LogValidationError as e:
    print(f"Error de validación: {e}")
```

### Validación Programática

```python
from log_constants import (
    validate_etapa,
    validate_status,
    validate_error_code,
    validate_log_entry
)

# Validar valores individuales
try:
    validate_etapa("CAPTURE")  # OK
    validate_status("SUCCESS")  # OK
    validate_error_code("APP_CRASH")  # OK
except LogValidationError as e:
    print(f"Error: {e}")

# Validar entrada completa
result = validate_log_entry(
    etapa="CAPTURE",
    status="SUCCESS",
    strict=False
)
# result = {
#     "valid": True,
#     "errors": [],
#     "warnings": []
# }
```

---

## 🧪 Testing

Ejecutar suite de tests:

```bash
cd ffa-app
python test_log_validation.py
```

**Tests incluidos:**
1. ✅ Validación de STATUS permitidos
2. ✅ Validación de ETAPAS permitidas
3. ✅ Validación de códigos de error
4. ✅ Validación de tipos de calibración
5. ✅ Validación completa de logs
6. ✅ Llamadas reales a logEvent
7. ✅ Verificación de constantes de vocabulario

---

## 📁 Archivos del Sistema

| Archivo | Descripción |
|---------|-------------|
| `log_constants.py` | Vocabulario congelado y funciones de validación |
| `logger.py` | Logger con validación integrada |
| `test_log_validation.py` | Suite de tests de validación |
| `logs/ffa_app_events.log` | Archivo de logs (formato JSON por línea) |

---

## 🚨 Buenas Prácticas

### ✅ DO

```python
# Usar códigos de error estándar
logEvent(
    etapa="CALIBRATION",
    status="ERROR",
    error_code="LOAD_CELL_CALIB_ERROR",  # ✅ Código estándar
    additional_data={"step": 1}
)

# Proporcionar contexto en additional_data
logEvent(
    etapa="CAPTURE",
    status="SUCCESS",
    additional_data={
        "action": "capture_completed",
        "duration_ms": 1250,
        "flash_triggered": True
    }
)

# Usar etapas específicas
logEvent(
    etapa="CONFIG_UPDATE",  # ✅ Específico
    status="SUCCESS",
    additional_data={"config_type": "fish_parameters"}
)
```

### ❌ DON'T

```python
# NO inventar nuevos códigos de error
logEvent(
    etapa="CALIBRATION",
    status="ERROR",
    error_code="MY_CUSTOM_ERROR",  # ❌ No estándar
)

# NO usar etapas incorrectas
logEvent(
    etapa="PROCESSING",  # ❌ No existe, usar ANALISIS
    status="INFO"
)

# NO omitir contexto importante
logEvent(
    etapa="ERROR",  # ❌ ERROR es un status, no una etapa
    status="SUCCESS"
)
```

---

## 🔄 Actualización del Vocabulario

Si necesitas agregar nuevo vocabulario:

1. **Editar `log_constants.py`:**
   ```python
   ALLOWED_ETAPAS = {
       # ... existentes
       "NEW_STAGE",  # Nueva etapa
   }
   
   ERROR_CODES = {
       # ... existentes
       "NEW_ERROR_CODE": "Descripción del error",
   }
   ```

2. **Incrementar versión:**
   ```python
   VOCABULARY_VERSION = "1.1.0"
   ```

3. **Ejecutar tests:**
   ```bash
   python test_log_validation.py
   ```

4. **Actualizar esta documentación**

---

## 📊 Análisis de Logs

Los logs JSON por línea facilitan el análisis:

```bash
# Contar logs por status
cat logs/ffa_app_events.log | jq -r '.status' | sort | uniq -c

# Filtrar solo errores
cat logs/ffa_app_events.log | jq 'select(.status == "ERROR")'

# Agrupar por etapa
cat logs/ffa_app_events.log | jq -r '.etapa' | sort | uniq -c

# Errores de calibración
cat logs/ffa_app_events.log | jq 'select(.etapa == "CALIBRATION" and .status == "ERROR")'
```

---

## 📞 Soporte

Para preguntas o adiciones al vocabulario, consultar con el equipo de desarrollo.

**Última actualización:** 2025-12-08  
**Versión:** 1.0.0

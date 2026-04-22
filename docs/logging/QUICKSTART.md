# 🔥 Sistema de Logging FFA - Quick Start

## ¡Listo para usar! 🚀

El sistema de logging ya está integrado en la aplicación y funcionando.

## 📍 Ubicación de logs

```
ffa-app/logs/ffa_app_events.log
```

## 🎯 Uso rápido

```bash
# Ver últimos logs + estadísticas
python tools/logging/view_logs.py

# Ver solo errores
python tools/logging/view_logs.py errors

# Ver estadísticas completas
python tools/logging/view_logs.py stats

# Ver eventos específicos
python tools/logging/view_logs.py capture      # Capturas
python tools/logging/view_logs.py config       # Configuración
python tools/logging/view_logs.py calibration  # Calibraciones
```

## 📊 Estructura del log

Cada evento registra:
- ⏰ Timestamp
- 📦 Lote ID
- 🏢 Proveedor ID
- 🎯 Etapa (CAPTURE, ANALYSIS, CONFIG_UPDATE, etc.)
- ✅ Status (SUCCESS, ERROR, WARNING, INFO)
- 🐟 Parámetros de pez
- 👁️ Parámetros de visión
- 📱 Versión de la app
- ❌ Código y mensaje de error (si aplica)
- 📊 Datos adicionales

## 💻 Uso en código

```python
from logger import logEvent

# Log simple
logEvent(
    etapa="CAPTURE",
    status="SUCCESS",
    lote_id="LOT-001"
)

# Log con error
logEvent(
    etapa="ANALYSIS",
    status="ERROR",
    lote_id="LOT-001",
    error_code="CAMERA_TIMEOUT",
    error_msg="No se pudo capturar imagen"
)

# Log con datos completos
logEvent(
    etapa="ANALYSIS",
    status="SUCCESS",
    lote_id="LOT-001",
    fish_params={"species": "MACK", "type": "HG"},
    vision_params={"ppmm": 0.23},
    additional_data={"length": 25.5}
)
```

## 🧪 Probar el sistema

```bash
# Generar logs de prueba
python tests/test_logging.py

# Ver los resultados
python tools/logging/view_logs.py
```

## 📖 Documentación completa

Ver [README.md](./README.md) para documentación detallada.

---

**¡El logging ya está funcionando en toda la aplicación!** 🎉

Eventos automáticamente registrados:
- ✅ Capturas de imagen
- ✅ Análisis de imagen
- ✅ Mediciones de peso
- ✅ Calibraciones (peso, longitud, ZOI)
- ✅ Actualizaciones de configuración
- ✅ Inicio/parada de la aplicación
- ✅ Todos los errores

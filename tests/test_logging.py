#!/usr/bin/env python3
"""
Script de prueba para el sistema de logging
Genera eventos de ejemplo para verificar que todo funciona correctamente
"""

import _bootstrap  # noqa: F401 - adds project root to sys.path

from logger import logEvent, get_logger

def test_logging():
    """Genera eventos de prueba"""
    
    print("🧪 Generando eventos de prueba...\n")
    
    # 1. Evento de inicio de sistema
    logEvent(
        etapa="SYSTEM",
        status="INFO",
        additional_data={
            "event_type": "app_startup",
            "description": "Test: Aplicación iniciada"
        }
    )
    print("✅ Log de inicio generado")
    
    # 2. Captura exitosa
    logEvent(
        etapa="CAPTURE",
        status="SUCCESS",
        lote_id="LOT-TEST-001",
        proveedor_id="PROV-001",
        additional_data={"action": "capture_completed"}
    )
    print("✅ Log de captura exitosa generado")
    
    # 3. Análisis exitoso
    logEvent(
        etapa="ANALYSIS",
        status="SUCCESS",
        lote_id="LOT-TEST-001",
        proveedor_id="PROV-001",
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
            "results": {
                "length": 25.5,
                "weight": 125.3,
                "defects": ["BB"]
            }
        }
    )
    print("✅ Log de análisis exitoso generado")
    
    # 4. Medición de peso
    logger = get_logger()
    logger.log_weight(
        status="SUCCESS",
        weight_value=125.3,
        lote_id="LOT-TEST-001"
    )
    print("✅ Log de peso generado")
    
    # 5. Error de captura
    logEvent(
        etapa="CAPTURE",
        status="ERROR",
        lote_id="LOT-TEST-002",
        error_code="CAMERA_TIMEOUT",
        error_msg="La cámara no respondió después de 5 segundos",
        additional_data={"retry_count": 3}
    )
    print("❌ Log de error de captura generado")
    
    # 6. Actualización de configuración
    logger.log_config_update(
        status="SUCCESS",
        config_type="fish_parameters",
        old_values={"species": "MACK", "type": "WR"},
        new_values={"species": "MACK", "type": "HG"}
    )
    print("✅ Log de actualización de config generado")
    
    # 7. Calibración de longitud
    logger.log_calibration(
        status="SUCCESS",
        calibration_type="length",
        calibration_data={"old_ratio": 0.20, "new_ratio": 0.23}
    )
    print("✅ Log de calibración generado")
    
    # 8. Warning
    logEvent(
        etapa="ANALYSIS",
        status="WARNING",
        lote_id="LOT-TEST-003",
        additional_data={
            "warning": "Imagen con baja iluminación",
            "brightness": 45
        }
    )
    print("⚠️  Log de warning generado")
    
    # 9. Error de configuración
    logger.log_error(
        etapa="CONFIG_UPDATE",
        error_code="SPECIES_NOT_FOUND",
        error_msg="Especie 'UNKNOWN' no encontrada en configuración",
        additional_data={"requested_species": "UNKNOWN"}
    )
    print("❌ Log de error de configuración generado")
    
    # 10. Evento de sistema
    logger.log_system_event(
        status="INFO",
        event_type="test_completed",
        description="Test de logging completado exitosamente"
    )
    print("✅ Log de evento de sistema generado")
    
    print("\n✨ ¡Test completado! Ahora puedes ver los logs con:")
    print("   python tools/logging/view_logs.py")
    print("   python tools/logging/view_logs.py stats")
    print("   python tools/logging/view_logs.py errors")


if __name__ == '__main__':
    test_logging()

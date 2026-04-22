#!/usr/bin/env python3
"""
Ejemplos avanzados de uso del sistema de logging
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from logger import logEvent, get_logger

def ejemplo_basico():
    """Ejemplo básico de logging"""
    print("=" * 60)
    print("EJEMPLO 1: Log básico")
    print("=" * 60)
    
    logEvent(
        etapa="CAPTURE",
        status="SUCCESS"
    )
    print("✅ Log básico registrado")


def ejemplo_con_lote():
    """Ejemplo con información de lote"""
    print("\n" + "=" * 60)
    print("EJEMPLO 2: Log con información de lote")
    print("=" * 60)
    
    logEvent(
        etapa="CAPTURE",
        status="SUCCESS",
        lote_id="LOT-2025-001",
        proveedor_id="PROV-ABC-123"
    )
    print("✅ Log con lote registrado")


def ejemplo_analisis_completo():
    """Ejemplo de análisis completo con todos los datos"""
    print("\n" + "=" * 60)
    print("EJEMPLO 3: Análisis completo")
    print("=" * 60)
    
    logEvent(
        etapa="ANALYSIS",
        status="SUCCESS",
        lote_id="LOT-2025-001",
        proveedor_id="PROV-ABC-123",
        fish_params={
            "species": "MACK",
            "type": "HG",
            "parameters": {
                "A": 12,
                "B": None,
                "C": 24
            }
        },
        vision_params={
            "zoi": [[124, 182], [480, 360]],
            "ppmm": 0.23,
            "tailTrigger": 40
        },
        additional_data={
            "length_mm": 255.5,
            "weight_g": 125.3,
            "defects": ["BB", "HD"],
            "processing_time_ms": 145
        }
    )
    print("✅ Log de análisis completo registrado")


def ejemplo_error():
    """Ejemplo de registro de error"""
    print("\n" + "=" * 60)
    print("EJEMPLO 4: Registro de error")
    print("=" * 60)
    
    logEvent(
        etapa="CAPTURE",
        status="ERROR",
        lote_id="LOT-2025-002",
        error_code="CAMERA_TIMEOUT",
        error_msg="La cámara no respondió después de 5 segundos",
        additional_data={
            "retry_count": 3,
            "last_attempt": "2025-11-25T22:15:30",
            "camera_id": "CAM-001"
        }
    )
    print("❌ Log de error registrado")


def ejemplo_warning():
    """Ejemplo de warning"""
    print("\n" + "=" * 60)
    print("EJEMPLO 5: Warning")
    print("=" * 60)
    
    logEvent(
        etapa="ANALYSIS",
        status="WARNING",
        lote_id="LOT-2025-003",
        additional_data={
            "warning": "Imagen con baja iluminación detectada",
            "brightness_level": 45,
            "recommended_min": 60
        }
    )
    print("⚠️  Warning registrado")


def ejemplo_metodos_especializados():
    """Ejemplo usando métodos especializados del logger"""
    print("\n" + "=" * 60)
    print("EJEMPLO 6: Métodos especializados")
    print("=" * 60)
    
    logger = get_logger()
    
    # Log de peso
    logger.log_weight(
        status="SUCCESS",
        weight_value=125.5,
        lote_id="LOT-2025-001"
    )
    print("✅ Log de peso registrado")
    
    # Log de calibración
    logger.log_calibration(
        status="SUCCESS",
        calibration_type="length",
        calibration_data={
            "old_ratio": 0.20,
            "new_ratio": 0.23,
            "calibration_points": 5,
            "variance": 0.001
        }
    )
    print("✅ Log de calibración registrado")
    
    # Log de actualización de config
    logger.log_config_update(
        status="SUCCESS",
        config_type="fish_parameters",
        old_values={
            "species": "MACK",
            "type": "WR",
            "parameters": {"A": 10, "B": 15, "C": 20}
        },
        new_values={
            "species": "MACK",
            "type": "HG",
            "parameters": {"A": 12, "B": None, "C": 24}
        }
    )
    print("✅ Log de actualización de config registrado")


def ejemplo_workflow_completo():
    """Ejemplo de workflow completo de procesamiento"""
    print("\n" + "=" * 60)
    print("EJEMPLO 7: Workflow completo")
    print("=" * 60)
    
    lote_id = "LOT-2025-WORKFLOW-001"
    proveedor_id = "PROV-XYZ-789"
    
    # 1. Inicio de captura
    logEvent(
        etapa="CAPTURE",
        status="INFO",
        lote_id=lote_id,
        proveedor_id=proveedor_id,
        additional_data={"action": "capture_started"}
    )
    
    # 2. Captura exitosa
    logEvent(
        etapa="CAPTURE",
        status="SUCCESS",
        lote_id=lote_id,
        proveedor_id=proveedor_id,
        additional_data={
            "action": "capture_completed",
            "exposure_time_ms": 100,
            "resolution": "1920x1080"
        }
    )
    
    # 3. Análisis
    logEvent(
        etapa="ANALYSIS",
        status="SUCCESS",
        lote_id=lote_id,
        proveedor_id=proveedor_id,
        fish_params={
            "species": "SAR",
            "type": "HG",
            "parameters": {"A": 6, "B": None, "C": 18}
        },
        additional_data={
            "length_mm": 198.5,
            "defects_count": 2,
            "defects": ["BB", "S"],
            "processing_time_ms": 89
        }
    )
    
    # 4. Medición de peso
    logger = get_logger()
    logger.log_weight(
        status="SUCCESS",
        weight_value=98.7,
        lote_id=lote_id
    )
    
    # 5. Guardado exitoso
    logEvent(
        etapa="SYSTEM",
        status="SUCCESS",
        lote_id=lote_id,
        proveedor_id=proveedor_id,
        additional_data={
            "action": "data_saved",
            "database": "ffa_server",
            "record_id": "REC-12345"
        }
    )
    
    print("✅ Workflow completo registrado (5 eventos)")


def ejemplo_manejo_excepciones():
    """Ejemplo de cómo integrar logging en manejo de excepciones"""
    print("\n" + "=" * 60)
    print("EJEMPLO 8: Manejo de excepciones")
    print("=" * 60)
    
    lote_id = "LOT-2025-ERROR-001"
    
    try:
        # Simular una operación que puede fallar
        # En realidad, aquí iría tu código
        raise ValueError("Simulación de error: Parámetro inválido")
        
    except ValueError as e:
        logEvent(
            etapa="CONFIG_UPDATE",
            status="ERROR",
            lote_id=lote_id,
            error_code="INVALID_PARAMETER",
            error_msg=str(e),
            additional_data={
                "exception_type": "ValueError",
                "function": "ejemplo_manejo_excepciones"
            }
        )
        print("❌ Excepción registrada en logs")
    
    except Exception as e:
        logEvent(
            etapa="SYSTEM",
            status="ERROR",
            lote_id=lote_id,
            error_code="UNEXPECTED_ERROR",
            error_msg=f"Error inesperado: {str(e)}",
            additional_data={
                "exception_type": type(e).__name__,
                "function": "ejemplo_manejo_excepciones"
            }
        )
        print("❌ Error inesperado registrado")


def ejemplo_contexto_detallado():
    """Ejemplo con contexto muy detallado para debugging"""
    print("\n" + "=" * 60)
    print("EJEMPLO 9: Contexto detallado para debugging")
    print("=" * 60)
    
    logEvent(
        etapa="ANALYSIS",
        status="ERROR",
        lote_id="LOT-2025-DEBUG-001",
        proveedor_id="PROV-DEBUG-001",
        error_code="IMAGE_PROCESSING_FAILED",
        error_msg="No se pudo procesar la imagen: contornos insuficientes",
        fish_params={
            "species": "MACK",
            "type": "HG",
            "parameters": {"A": 12, "B": None, "C": 24}
        },
        vision_params={
            "zoi": [[124, 182], [480, 360]],
            "ppmm": 0.23,
            "tailTrigger": 40
        },
        additional_data={
            "image_path": "/tmp/capture_20251125_221530.jpg",
            "image_size": [1920, 1080],
            "preprocessing": {
                "gaussian_blur": True,
                "kernel_size": [5, 5],
                "threshold_value": 127
            },
            "detection": {
                "contours_found": 2,
                "contours_required": 5,
                "largest_contour_area": 1234.5
            },
            "system_info": {
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_free_gb": 125.3
            }
        }
    )
    print("❌ Log detallado para debugging registrado")


def ejemplo_multiples_especies():
    """Ejemplo procesando múltiples especies"""
    print("\n" + "=" * 60)
    print("EJEMPLO 10: Procesamiento de múltiples especies")
    print("=" * 60)
    
    especies = [
        {"name": "MACK", "type": "HG", "params": {"A": 12, "B": None, "C": 24}},
        {"name": "MACK", "type": "WR", "params": {"A": 10, "B": 15, "C": 20}},
        {"name": "SAR", "type": "HG", "params": {"A": 6, "B": None, "C": 18}}
    ]
    
    for i, especie in enumerate(especies, 1):
        logEvent(
            etapa="ANALYSIS",
            status="SUCCESS",
            lote_id=f"LOT-2025-MULTI-{i:03d}",
            fish_params={
                "species": especie["name"],
                "type": especie["type"],
                "parameters": especie["params"]
            },
            additional_data={
                "sequence_number": i,
                "total_in_batch": len(especies)
            }
        )
    
    print(f"✅ {len(especies)} especies procesadas y registradas")


def main():
    """Ejecuta todos los ejemplos"""
    print("\n")
    print("🔥" * 30)
    print("EJEMPLOS AVANZADOS DE LOGGING FFA")
    print("🔥" * 30)
    print()
    
    ejemplo_basico()
    ejemplo_con_lote()
    ejemplo_analisis_completo()
    ejemplo_error()
    ejemplo_warning()
    ejemplo_metodos_especializados()
    ejemplo_workflow_completo()
    ejemplo_manejo_excepciones()
    ejemplo_contexto_detallado()
    ejemplo_multiples_especies()
    
    print("\n" + "=" * 60)
    print("✨ ¡Todos los ejemplos ejecutados!")
    print("=" * 60)
    print("\n📊 Ahora puedes ver los logs con:")
    print("   python tools/logging/view_logs.py")
    print("   python tools/logging/monitor_logs.py history")
    print()


if __name__ == '__main__':
    main()

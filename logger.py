"""
FFA Application Event Logger
Sistema de logging para eventos de la aplicación FFA
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Versión de la aplicación
APP_VERSION = "1.0.0"

# Configuración de directorios
BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOG_FILE = LOGS_DIR / "ffa_app_events.log"

# Crear directorio de logs si no existe
LOGS_DIR.mkdir(exist_ok=True)


class FFAEventLogger:
    """Logger personalizado para eventos de la aplicación FFA"""
    
    def __init__(self, log_file: str = str(LOG_FILE)):
        self.log_file = log_file
        self._setup_logger()
        
    def _setup_logger(self):
        """Configura el logger con formato JSON"""
        self.logger = logging.getLogger('FFA_EventLogger')
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicar handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Handler para archivo
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Handler para consola (opcional, para debugging)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        
        # Formato simple para el archivo (JSON por línea)
        file_formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Formato para consola
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_event(
        self,
        etapa: str,
        status: str,
        lote_id: Optional[str] = None,
        proveedor_id: Optional[str] = None,
        fish_params: Optional[Dict[str, Any]] = None,
        vision_params: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Registra un evento en el log
        
        Args:
            etapa: Etapa del proceso (ej: 'CAPTURE', 'ANALYSIS', 'WEIGHT', 'SAVE')
            status: Estado del evento (ej: 'SUCCESS', 'ERROR', 'WARNING', 'INFO')
            lote_id: ID del lote actual
            proveedor_id: ID del proveedor
            fish_params: Parámetros de pez actuales (species, type, params)
            vision_params: Parámetros de visión (zoi, ppmm, tailTrigger)
            error_code: Código de error si aplica
            error_msg: Mensaje de error si aplica
            additional_data: Datos adicionales a registrar
        """
        timestamp = datetime.now().isoformat()
        
        event = {
            "timestamp": timestamp,
            "lote_id": lote_id,
            "proveedor_id": proveedor_id,
            "etapa": etapa,
            "status": status,
            "fish_params": fish_params,
            "vision_params": vision_params,
            "version_app": APP_VERSION,
            "error_code": error_code,
            "error_msg": error_msg
        }
        
        # Agregar datos adicionales si existen
        if additional_data:
            event["additional_data"] = additional_data
        
        # Convertir a JSON y registrar
        log_entry = json.dumps(event, ensure_ascii=False)
        
        # Determinar nivel de log según status
        if status == "ERROR":
            self.logger.error(log_entry)
        elif status == "WARNING":
            self.logger.warning(log_entry)
        else:
            self.logger.info(log_entry)
    
    def log_capture(
        self,
        status: str,
        lote_id: Optional[str] = None,
        error_msg: Optional[str] = None
    ):
        """Log específico para captura de imagen"""
        self.log_event(
            etapa="CAPTURE",
            status=status,
            lote_id=lote_id,
            error_msg=error_msg
        )
    
    def log_analysis(
        self,
        status: str,
        lote_id: Optional[str] = None,
        fish_params: Optional[Dict[str, Any]] = None,
        vision_params: Optional[Dict[str, Any]] = None,
        analysis_results: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None
    ):
        """Log específico para análisis de imagen"""
        self.log_event(
            etapa="ANALYSIS",
            status=status,
            lote_id=lote_id,
            fish_params=fish_params,
            vision_params=vision_params,
            additional_data={"results": analysis_results} if analysis_results else None,
            error_msg=error_msg
        )
    
    def log_weight(
        self,
        status: str,
        weight_value: Optional[float] = None,
        lote_id: Optional[str] = None,
        error_msg: Optional[str] = None
    ):
        """Log específico para peso"""
        self.log_event(
            etapa="WEIGHT",
            status=status,
            lote_id=lote_id,
            additional_data={"weight": weight_value} if weight_value is not None else None,
            error_msg=error_msg
        )
    
    def log_config_update(
        self,
        status: str,
        config_type: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None
    ):
        """Log específico para actualización de configuración"""
        self.log_event(
            etapa="CONFIG_UPDATE",
            status=status,
            additional_data={
                "config_type": config_type,
                "old_values": old_values,
                "new_values": new_values
            },
            error_msg=error_msg
        )
    
    def log_calibration(
        self,
        status: str,
        calibration_type: str,
        calibration_data: Optional[Dict[str, Any]] = None,
        error_msg: Optional[str] = None
    ):
        """Log específico para calibraciones"""
        self.log_event(
            etapa="CALIBRATION",
            status=status,
            additional_data={
                "calibration_type": calibration_type,
                "calibration_data": calibration_data
            },
            error_msg=error_msg
        )
    
    def log_system_event(
        self,
        status: str,
        event_type: str,
        description: Optional[str] = None,
        error_msg: Optional[str] = None
    ):
        """Log para eventos del sistema"""
        self.log_event(
            etapa="SYSTEM",
            status=status,
            additional_data={
                "event_type": event_type,
                "description": description
            },
            error_msg=error_msg
        )
    
    def log_error(
        self,
        etapa: str,
        error_code: str,
        error_msg: str,
        lote_id: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Log específico para errores"""
        self.log_event(
            etapa=etapa,
            status="ERROR",
            lote_id=lote_id,
            error_code=error_code,
            error_msg=error_msg,
            additional_data=additional_data
        )


# Instancia global del logger
_logger_instance = None

def get_logger() -> FFAEventLogger:
    """Obtiene la instancia singleton del logger"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = FFAEventLogger()
    return _logger_instance


def logEvent(
    etapa: str,
    status: str,
    lote_id: Optional[str] = None,
    proveedor_id: Optional[str] = None,
    fish_params: Optional[Dict[str, Any]] = None,
    vision_params: Optional[Dict[str, Any]] = None,
    error_code: Optional[str] = None,
    error_msg: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
):
    """
    Función principal para registrar eventos (interfaz simple)
    
    Args:
        etapa: Etapa del proceso
        status: Estado del evento ('SUCCESS', 'ERROR', 'WARNING', 'INFO')
        lote_id: ID del lote
        proveedor_id: ID del proveedor
        fish_params: Parámetros de pez
        vision_params: Parámetros de visión
        error_code: Código de error
        error_msg: Mensaje de error
        additional_data: Datos adicionales
    """
    logger = get_logger()
    logger.log_event(
        etapa=etapa,
        status=status,
        lote_id=lote_id,
        proveedor_id=proveedor_id,
        fish_params=fish_params,
        vision_params=vision_params,
        error_code=error_code,
        error_msg=error_msg,
        additional_data=additional_data
    )
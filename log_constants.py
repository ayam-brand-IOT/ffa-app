"""
Constantes y vocabulario estandarizado para el sistema de logging FFA
=====================================================================

Este archivo define el vocabulario permitido para los logs, asegurando
consistencia y facilitando el análisis posterior de eventos.
"""

from typing import Set, Dict, Any

# ============================================================================
# ESTADOS PERMITIDOS
# ============================================================================

ALLOWED_STATUS: Set[str] = {
    "INFO",      # Evento informativo normal
    "SUCCESS",   # Operación completada exitosamente
    "WARNING",   # Advertencia, operación continuó pero con alertas
    "ERROR"      # Error, operación falló
}

# ============================================================================
# ETAPAS DEL PROCESO PERMITIDAS
# ============================================================================

ALLOWED_ETAPAS: Set[str] = {
    "SYSTEM",          # Eventos del sistema (startup, shutdown, etc.)
    "CALIBRATION",     # Calibraciones (peso, longitud, ZOI)
    "CONFIG_UPDATE",   # Actualización de configuración
    "INICIO_LOTE",     # Inicio de un nuevo lote
    "MUESTRA",         # Procesamiento de muestra individual
    "CAPTURE",         # Captura de imagen
    "ANALISIS",        # Análisis de imagen (mediciones, defectos)
    "GUTS_WEIGHT",     # Pesaje de vísceras/belly
    "CIERRE_LOTE",     # Cierre y finalización de lote
    "RESET",           # Reset de sistema o proceso
}

# ============================================================================
# CÓDIGOS DE ERROR ESTANDARIZADOS
# ============================================================================

ERROR_CODES: Dict[str, str] = {
    # Errores de sistema
    "APP_CRASH": "Crash inesperado de la aplicación",
    "APP_STARTUP_ERROR": "Error al iniciar la aplicación",
    "MEMORY_ERROR": "Error de memoria insuficiente",
    
    # Errores de calibración
    "LOAD_CELL_CALIB_ERROR": "Error en calibración de celda de carga",
    "LENGTH_CALIB_ERROR": "Error en calibración de longitud",
    "ZOI_CALIB_ERROR": "Error en calibración de zona de interés",
    "CALIBRATION_TIMEOUT": "Timeout en proceso de calibración",
    "CALIBRATION_BUSY": "Otra sesión ya controla la calibración",
    "CALIBRATION_ABANDONED": "El cliente abandonó la calibración",
    
    # Errores de configuración
    "CONFIG_READ_ERROR": "Error al leer archivo de configuración",
    "CONFIG_WRITE_ERROR": "Error al escribir archivo de configuración",
    "CONFIG_UNEXPECTED_ERROR": "Error inesperado en configuración",
    "SPECIES_NOT_FOUND": "Especie o tipo no encontrado en configuración",
    "INVALID_CONFIG_FORMAT": "Formato de configuración inválido",
    
    # Errores de captura
    "CAPTURE_ERROR": "Error en captura de imagen",
    "CAMERA_NOT_FOUND": "Cámara no encontrada o no disponible",
    "CAPTURE_TIMEOUT": "Timeout en captura de imagen",
    "IMAGE_CORRUPTED": "Imagen capturada está corrupta",
    
    # Errores de análisis
    "ANALYSIS_ERROR": "Error en análisis de imagen",
    "NO_FISH_DETECTED": "No se detectó pescado en la imagen",
    "INVALID_MEASUREMENTS": "Mediciones inválidas o fuera de rango",
    "VISION_PROCESSING_ERROR": "Error en procesamiento de visión",
    
    # Errores de peso
    "WEIGHT_READ_ERROR": "Error al leer peso de báscula",
    "WEIGHT_UNSTABLE": "Peso inestable, no se puede registrar",
    "WEIGHT_TIMEOUT": "Timeout esperando peso estable",
    "MODBUS_CONNECTION_ERROR": "Error de conexión Modbus",
    "SCALE_READ_ERROR": "Error al leer el transmisor de peso",
    "SCALE_FAULT": "El transmisor reportó una falla física",
    "SCALE_POLLER_ERROR": "El supervisor del peso reinició el polling",
    
    # Errores de lote
    "LOTE_CREATION_ERROR": "Error al crear nuevo lote",
    "LOTE_NOT_FOUND": "Lote no encontrado",
    "LOTE_ALREADY_CLOSED": "Lote ya cerrado, no se pueden agregar muestras",
    "LOTE_CLOSE_ERROR": "Error al cerrar lote",
    
    # Errores de muestra
    "MUESTRA_SAVE_ERROR": "Error al guardar muestra",
    "MUESTRA_VALIDATION_ERROR": "Error de validación en datos de muestra",
    "DUPLICATE_MUESTRA": "Muestra duplicada detectada",
    
    # Errores de hardware
    "GPIO_ERROR": "Error en control de GPIO",
    "SENSOR_ERROR": "Error en lectura de sensor",
    "HARDWARE_NOT_AVAILABLE": "Hardware no disponible o desconectado",
    
    # Errores de base de datos
    "DB_CONNECTION_ERROR": "Error de conexión a base de datos",
    "DB_WRITE_ERROR": "Error al escribir en base de datos",
    "DB_READ_ERROR": "Error al leer de base de datos",
    
    # Errores de reset
    "RESET_ERROR": "Error al resetear sistema",

    # Errores de captura y analisis de imagen
    "RAW_IMAGE_SAVE_ERROR": "No se pudo persistir la imagen cruda de muestra",
    "ANALYSIS_INVALID": "El análisis no produjo una medición válida",
    "FISH_PARAMETERS_INVALID": "Parámetros de pescado inválidos",

    # Errores del transmisor de peso
    "TLB_DIVISION_READ_FAILED": "No se pudo leer la división configurada del transmisor",
    "TLB_DIVISION_INVALID": "El transmisor devolvió una división desconocida",
    "TLB_READ_ERROR": "No se pudo leer el transmisor de peso",
}

# ============================================================================
# TIPOS DE CALIBRACIÓN PERMITIDOS
# ============================================================================

CALIBRATION_TYPES: Set[str] = {
    "load_cell",       # Calibración de celda de carga
    "length",          # Calibración de longitud (px/mm ratio)
    "zoi",             # Calibración de zona de interés
    "zero",            # Ajuste de cero
    "tare",            # Ajuste de tara
    "tare_belly",      # Ajuste de tara para belly test
    "remote",          # Calibración remota
    "physical",        # Calibración física
}

# ============================================================================
# TIPOS DE CONFIGURACIÓN PERMITIDOS
# ============================================================================

CONFIG_TYPES: Set[str] = {
    "fish_parameters",     # Parámetros de especie de pescado
    "vision_parameters",   # Parámetros de visión
    "tail_trigger",        # Umbral de detección de cola
    "system_settings",     # Configuraciones del sistema
}

# ============================================================================
# EVENTOS DE SISTEMA PERMITIDOS
# ============================================================================

SYSTEM_EVENT_TYPES: Set[str] = {
    "app_startup",         # Inicio de aplicación
    "app_shutdown",        # Cierre normal de aplicación
    "app_crash",           # Crash de aplicación
    "enter_tension_mode",  # Cambio a modo tensión
    "enter_weight_mode",   # Cambio a modo peso
    "gpio_init",           # Inicialización de GPIO
    "camera_init",         # Inicialización de cámara
    "modbus_init",         # Inicialización de Modbus
}

# ============================================================================
# ACCIONES DE CAPTURA PERMITIDAS
# ============================================================================

CAPTURE_ACTIONS: Set[str] = {
    "capture_started",     # Inicio de captura
    "capture_completed",   # Captura completada
    "flash_triggered",     # Flash activado
    "laser_on",            # Laser encendido
    "laser_off",           # Laser apagado
}

# ============================================================================
# ACCIONES DE RESET PERMITIDAS
# ============================================================================

RESET_ACTIONS: Set[str] = {
    "reset_completed",     # Reset completado
    "reset_defects",       # Reset de defectos
    "reset_calibration",   # Reset de calibración
}

# ============================================================================
# FUNCIONES DE VALIDACIÓN
# ============================================================================

class LogValidationError(ValueError):
    """Excepción para errores de validación de logs"""
    pass


def validate_status(status: str) -> None:
    """
    Valida que el status esté en la lista permitida
    
    Args:
        status: Status a validar
        
    Raises:
        LogValidationError: Si el status no es válido
    """
    if status not in ALLOWED_STATUS:
        raise LogValidationError(
            f"Status '{status}' no permitido. "
            f"Valores permitidos: {', '.join(sorted(ALLOWED_STATUS))}"
        )


def validate_etapa(etapa: str) -> None:
    """
    Valida que la etapa esté en la lista permitida
    
    Args:
        etapa: Etapa a validar
        
    Raises:
        LogValidationError: Si la etapa no es válida
    """
    if etapa not in ALLOWED_ETAPAS:
        raise LogValidationError(
            f"Etapa '{etapa}' no permitida. "
            f"Valores permitidos: {', '.join(sorted(ALLOWED_ETAPAS))}"
        )


def validate_error_code(error_code: str) -> None:
    """
    Valida que el código de error esté en la lista permitida
    
    Args:
        error_code: Código de error a validar
        
    Raises:
        LogValidationError: Si el código de error no es válido
    """
    if error_code not in ERROR_CODES:
        raise LogValidationError(
            f"Error code '{error_code}' no reconocido. "
            f"Códigos permitidos: {', '.join(sorted(ERROR_CODES.keys()))}"
        )


def validate_calibration_type(calib_type: str) -> None:
    """Valida tipo de calibración"""
    if calib_type not in CALIBRATION_TYPES:
        raise LogValidationError(
            f"Calibration type '{calib_type}' no permitido. "
            f"Valores permitidos: {', '.join(sorted(CALIBRATION_TYPES))}"
        )


def validate_config_type(config_type: str) -> None:
    """Valida tipo de configuración"""
    if config_type not in CONFIG_TYPES:
        raise LogValidationError(
            f"Config type '{config_type}' no permitido. "
            f"Valores permitidos: {', '.join(sorted(CONFIG_TYPES))}"
        )


def validate_system_event_type(event_type: str) -> None:
    """Valida tipo de evento de sistema"""
    if event_type not in SYSTEM_EVENT_TYPES:
        raise LogValidationError(
            f"System event type '{event_type}' no permitido. "
            f"Valores permitidos: {', '.join(sorted(SYSTEM_EVENT_TYPES))}"
        )


def get_error_description(error_code: str) -> str:
    """
    Obtiene la descripción de un código de error
    
    Args:
        error_code: Código de error
        
    Returns:
        Descripción del error o mensaje por defecto
    """
    return ERROR_CODES.get(error_code, "Error desconocido")


def validate_log_entry(
    etapa: str,
    status: str,
    error_code: str = None,
    strict: bool = True
) -> Dict[str, Any]:
    """
    Valida una entrada de log completa
    
    Args:
        etapa: Etapa del proceso
        status: Status del evento
        error_code: Código de error (opcional)
        strict: Si True, lanza excepciones. Si False, solo retorna warnings
        
    Returns:
        Dict con resultado de validación
        
    Raises:
        LogValidationError: Si strict=True y hay errores de validación
    """
    errors = []
    warnings = []
    
    # Validar etapa
    try:
        validate_etapa(etapa)
    except LogValidationError as e:
        errors.append(str(e))
    
    # Validar status
    try:
        validate_status(status)
    except LogValidationError as e:
        errors.append(str(e))
    
    # Validar error_code si está presente
    if error_code:
        try:
            validate_error_code(error_code)
        except LogValidationError as e:
            warnings.append(str(e))
    
    # Si hay errores y modo strict, lanzar excepción
    if errors and strict:
        raise LogValidationError("; ".join(errors))
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


# ============================================================================
# CONSTANTES ADICIONALES
# ============================================================================

# Versión del vocabulario (para tracking de cambios)
VOCABULARY_VERSION = "1.0.0"

# Campos obligatorios en un log
REQUIRED_FIELDS: Set[str] = {
    "timestamp",
    "etapa",
    "status",
    "version_app"
}

# Campos opcionales permitidos
OPTIONAL_FIELDS: Set[str] = {
    "lote_id",
    "proveedor_id",
    "fish_params",
    "vision_params",
    "error_code",
    "error_msg",
    "additional_data"
}

# Todos los campos permitidos
ALL_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

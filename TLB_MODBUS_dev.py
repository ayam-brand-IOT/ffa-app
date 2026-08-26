"""
TLB_MODBUS_dev.py - Emulador del Weight Transmitter
==================================================
Este archivo simula el comportamiento del módulo TLB_MODBUS.py sin necesidad 
de hardware físico. Útil para desarrollo, testing y debugging.

Características:
- Simula lecturas de peso con variación aleatoria realista
- Simula lecturas de tensión para belly resistance test
- Emula todos los comandos de calibración
- Soporte para modo peso y modo tensión
- Logging de todas las operaciones
- Valores configurables para testing
"""

import time
import random
from logger import logEvent

# ============================= CONFIGURACIÓN =============================

# IDs de dispositivos Modbus
SLAVE_ID = 1
BELLY_TEST_ID = 2

# Modos de operación
__WEIGHT_MODE = 0
__TENSION_MODE = 1

# Estado global
READING_MODE = __WEIGHT_MODE
isCalibrating = False

# ============================= CONFIGURACIÓN DE EMULACIÓN =============================

# Configuración de peso simulado
SIMULATED_WEIGHT_BASE = 125.5  # Peso base en gramos
WEIGHT_VARIATION = 2.0  # Variación aleatoria +/- gramos
WEIGHT_NOISE = 0.1  # Ruido fino +/- gramos

# Configuración de tensión simulada
SIMULATED_TENSION_BASE = 45.0  # Tensión base
TENSION_VARIATION = 5.0  # Variación aleatoria +/- unidades
TENSION_NOISE = 0.5  # Ruido fino +/- unidades

# Efectos de tara y zero
_tare_offset = 0.0
_zero_offset = 0.0
_belly_tare_offset = 0.0

# Estado de calibración
_calibration_points = []
_calibration_step = 0

# ============================= ESTABILIDAD DE PESO =============================
# Para que el sistema detecte peso estable, mantenemos el mismo valor por 1.2s

STABILITY_DURATION = 1.2  # Duración de estabilidad en segundos
STABILITY_TOLERANCE = 0.05  # Tolerancia de variación durante estabilidad (gramos)

# Estado de estabilidad
_current_stable_weight = None
_stability_start_time = None
_last_weight_change_time = None

# ============================= FUNCIONES DE MODO =============================

def isOnTensionMode():
    """Verifica si está en modo tensión"""
    return READING_MODE == __TENSION_MODE

def enterToTensionTest():
    """Activa el modo tensión (belly resistance test)"""
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __TENSION_MODE
    
    print("🔄 [DEV] Modo tensión activado")
    logEvent(
        etapa="SYSTEM",
        status="INFO",
        additional_data={
            "action": "enter_tension_mode",
            "emulated": True
        }
    )

def enterToWeightMode():
    """Activa el modo peso normal"""
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __WEIGHT_MODE
    
    print("⚖️  [DEV] Modo peso activado")
    logEvent(
        etapa="SYSTEM",
        status="INFO",
        additional_data={
            "action": "enter_weight_mode",
            "emulated": True
        }
    )

# ============================= FUNCIONES DE CONTROL =============================

def setZero(is_belly=False):
    """Establece el punto cero de la báscula"""
    global _zero_offset, _current_stable_weight, _stability_start_time
    
    # Simular el ajuste de cero
    current_reading = _generate_weight_reading()
    _zero_offset = -current_reading
    
    # Resetear estabilidad para generar nuevo peso estable
    _current_stable_weight = None
    _stability_start_time = None
    
    print(f"🎯 [DEV] Configurando a cero (offset: {_zero_offset:.2f}g)")
    logEvent(
        etapa="CALIBRATION",
        status="SUCCESS",
        additional_data={
            "calibration_type": "zero",
            "zero_offset": _zero_offset,
            "emulated": True
        }
    )

def setTare(is_belly=False):
    """Establece la tara de la báscula o belly"""
    global _tare_offset, _belly_tare_offset, _current_stable_weight, _stability_start_time, SIMULATED_WEIGHT_BASE
    
    if is_belly:
        current_reading = _generate_tension_reading()
        _belly_tare_offset = -current_reading
        print(f"🎯 [DEV] Tara belly establecida (offset: {_belly_tare_offset:.2f})")
        
        logEvent(
            etapa="CALIBRATION",
            status="SUCCESS",
            additional_data={
                "calibration_type": "tare_belly",
                "tare_offset": _belly_tare_offset,
                "emulated": True
            }
        )
    else:
        # Obtener el peso actual antes de aplicar la tara
        current_reading = _generate_weight_reading()
        _tare_offset = -current_reading - _zero_offset
        
        # Ajustar el peso base para que después de tara esté cerca de 0
        # Esto simula que el objeto sigue en la báscula después de tarar
        SIMULATED_WEIGHT_BASE = current_reading + _zero_offset
        
        # Resetear estabilidad para generar nuevo peso estable (que será ~0)
        _current_stable_weight = None
        _stability_start_time = None
        print(f"⚖️  [DEV] Tara establecida (offset: {_tare_offset:.2f}g)")
        
        logEvent(
            etapa="CALIBRATION",
            status="SUCCESS",
            additional_data={
                "calibration_type": "tare",
                "tare_offset": _tare_offset,
                "emulated": True
            }
        )

# ============================= FUNCIONES DE LECTURA =============================

def _generate_weight_reading():
    """
    Genera una lectura de peso realista con variación
    Mantiene estabilidad por 1.2s para permitir detección de peso estable
    """
    global _current_stable_weight, _stability_start_time, _last_weight_change_time
    
    current_time = time.time()
    
    # Inicializar en primera llamada
    if _current_stable_weight is None:
        _current_stable_weight = SIMULATED_WEIGHT_BASE
        _stability_start_time = current_time
        _last_weight_change_time = current_time
    
    # Calcular tiempo en estabilidad actual
    time_stable = current_time - _stability_start_time
    
    # Si ya pasaron 1.2s estables, generar nuevo peso y mantenerlo
    if time_stable >= STABILITY_DURATION:
        # Generar nuevo peso objetivo cada 1.2s
        slow_variation = random.uniform(-WEIGHT_VARIATION, WEIGHT_VARIATION)
        _current_stable_weight = SIMULATED_WEIGHT_BASE + slow_variation
        _stability_start_time = current_time
        _last_weight_change_time = current_time
    
    # Agregar solo ruido mínimo para simular lectura real pero estable
    noise = random.uniform(-STABILITY_TOLERANCE, STABILITY_TOLERANCE)
    
    return _current_stable_weight + noise

def _generate_tension_reading():
    """Genera una lectura de tensión realista con variación"""
    # Tensión base con variación
    slow_variation = random.uniform(-TENSION_VARIATION, TENSION_VARIATION)
    # Ruido
    noise = random.uniform(-TENSION_NOISE, TENSION_NOISE)
    
    return SIMULATED_TENSION_BASE + slow_variation + noise

def readWeight():
    """
    Lee el peso actual de la báscula
    Retorna: peso en gramos (float)
    """
    global isCalibrating
    
    if isCalibrating:
        return 0.0
    
    # Generar lectura simulada
    raw_weight = _generate_weight_reading()
    
    # Aplicar offsets de calibración
    weight = raw_weight + _zero_offset + _tare_offset
    
    # Asegurar que no sea negativo
    weight = max(0.0, weight)
    
    # Log ocasional (cada ~10 lecturas para no saturar)
    if random.random() < 0.1:
        print(f"⚖️  [DEV] Peso: {weight:.1f}g (raw: {raw_weight:.1f}g)")
    
    return weight

def readTenstion():
    """
    Lee la tensión actual (belly resistance test)
    Retorna: tensión en unidades del sensor (float)
    """
    global isCalibrating
    
    if isCalibrating:
        return 0.0
    
    # Generar lectura simulada
    raw_tension = _generate_tension_reading()
    
    # Aplicar offset de tara
    tension = raw_tension + _belly_tare_offset
    
    # Asegurar que no sea negativo
    tension = max(0.0, tension)
    
    # Log ocasional
    if random.random() < 0.1:
        print(f"🔬 [DEV] Tensión: {tension:.1f} (raw: {raw_tension:.1f})")
    
    return tension

# ============================= FUNCIONES DE CALIBRACIÓN =============================

def physical_calibration():
    """
    Emula el proceso de calibración física interactiva
    """
    print("\n" + "="*60)
    print("🔧 [DEV] CALIBRACIÓN FÍSICA - MODO EMULADO")
    print("="*60)
    
    print("\n⚠️  [DEV] No coloque nada en la báscula")
    print("Presione Enter para iniciar calibración de cero...")
    input()
    
    # Simular calibración de cero
    print("✅ [DEV] Punto cero calibrado")
    _calibration_points.clear()
    _calibration_points.append({"weight": 0, "reading": 0})
    
    logEvent(
        etapa="CALIBRATION",
        status="SUCCESS",
        additional_data={
            "calibration_type": "physical",
            "step": "zero_point",
            "emulated": True
        }
    )
    
    # Primera pesa de calibración
    print("\n📏 [DEV] Coloque el peso de calibración de 1Kg")
    input("Presione Enter para continuar...")
    
    simulated_reading = random.uniform(980, 1020)  # Simular lectura ~1000g
    _calibration_points.append({"weight": 1000, "reading": simulated_reading})
    print(f"✅ [DEV] Punto de 1Kg calibrado (lectura: {simulated_reading:.1f})")
    
    logEvent(
        etapa="CALIBRATION",
        status="SUCCESS",
        additional_data={
            "calibration_type": "physical",
            "step": "first_point",
            "weight": 1000,
            "reading": simulated_reading,
            "emulated": True
        }
    )
    
    input("Presione Enter para guardar...")
    print("💾 [DEV] Primer punto guardado")
    
    # Preguntar por más puntos
    should_continue = input("\n¿Desea agregar más puntos de calibración? (y/n): ")
    
    if should_continue.lower() == "n":
        print("\n✅ [DEV] Calibración completada")
        print(f"📊 [DEV] Puntos de calibración: {len(_calibration_points)}")
        return
    
    # Segunda pesa de calibración
    print("\n📏 [DEV] Coloque el peso de calibración de 2Kg")
    input("Presione Enter para continuar...")
    
    simulated_reading = random.uniform(1980, 2020)  # Simular lectura ~2000g
    _calibration_points.append({"weight": 2000, "reading": simulated_reading})
    print(f"✅ [DEV] Punto de 2Kg calibrado (lectura: {simulated_reading:.1f})")
    
    logEvent(
        etapa="CALIBRATION",
        status="SUCCESS",
        additional_data={
            "calibration_type": "physical",
            "step": "second_point",
            "weight": 2000,
            "reading": simulated_reading,
            "emulated": True
        }
    )
    
    print("💾 [DEV] Segundo punto guardado")
    print("\n✅ [DEV] Calibración completada exitosamente")
    print(f"📊 [DEV] Puntos de calibración: {len(_calibration_points)}")

def remote_calibration(step, args):
    """
    Emula el proceso de calibración remota (vía SocketIO)
    
    Args:
        step: Paso de calibración (1-4)
        args: Argumentos adicionales ("belly" para modo belly)
    """
    global isCalibrating, _calibration_step
    
    is_belly = (args == "belly")
    device_type = "belly" if is_belly else "weight"
    
    print(f"\n🔧 [DEV] Calibración remota - Paso {step} ({device_type})")
    
    if step == 1:
        # Paso 1: Configurar a cero
        print("🎯 [DEV] Paso 1: Configurando a cero")
        _calibration_step = 1
        
        logEvent(
            etapa="CALIBRATION",
            status="INFO",
            additional_data={
                "calibration_type": "remote",
                "step": 1,
                "action": "set_zero",
                "device": device_type,
                "emulated": True
            }
        )
        
    elif step == 2:
        # Paso 2: Tara (preparar para calibración)
        print("⚖️  [DEV] Paso 2: Ejecutando tara de calibración")
        _calibration_step = 2
        _calibration_points.clear()
        
        logEvent(
            etapa="CALIBRATION",
            status="SUCCESS",
            additional_data={
                "calibration_type": "remote",
                "step": 2,
                "action": "calibration_tare",
                "device": device_type,
                "emulated": True
            }
        )
        
    elif step == 3:
        # Paso 3: Guardar punto de calibración
        print("💾 [DEV] Paso 3: Guardando punto de calibración (1Kg simulado)")
        _calibration_step = 3
        
        # Simular guardado de punto
        simulated_reading = random.uniform(980, 1020)
        _calibration_points.append({"weight": 1000, "reading": simulated_reading})
        
        print(f"✅ [DEV] Punto calibrado: 1000g → lectura {simulated_reading:.1f}")
        
        logEvent(
            etapa="CALIBRATION",
            status="SUCCESS",
            additional_data={
                "calibration_type": "remote",
                "step": 3,
                "action": "save_point",
                "weight": 1000,
                "reading": simulated_reading,
                "device": device_type,
                "emulated": True
            }
        )
        
    elif step == 4:
        # Paso 4: Finalizar calibración
        print("✅ [DEV] Paso 4: Finalizando calibración remota")
        isCalibrating = False
        _calibration_step = 0
        
        print(f"📊 [DEV] Calibración completada con {len(_calibration_points)} puntos")
        
        logEvent(
            etapa="CALIBRATION",
            status="SUCCESS",
            additional_data={
                "calibration_type": "remote",
                "step": 4,
                "action": "finalize",
                "points_count": len(_calibration_points),
                "device": device_type,
                "emulated": True
            }
        )
    
    else:
        print(f"⚠️  [DEV] Paso de calibración desconocido: {step}")
        logEvent(
            etapa="CALIBRATION",
            status="WARNING",
            additional_data={
                "calibration_type": "remote",
                "step": step,
                "action": "unknown_step",
                "device": device_type,
                "emulated": True
            }
        )

# ============================= FUNCIONES AUXILIARES =============================

def set_simulated_weight(weight):
    """
    Configura el peso base simulado (útil para testing)
    
    Args:
        weight: Peso en gramos
    """
    global SIMULATED_WEIGHT_BASE, _current_stable_weight, _stability_start_time
    SIMULATED_WEIGHT_BASE = weight
    # Resetear estabilidad para usar nuevo peso inmediatamente
    _current_stable_weight = None
    _stability_start_time = None
    print(f"🔧 [DEV] Peso simulado configurado a {weight}g")

def set_simulated_tension(tension):
    """
    Configura la tensión base simulada (útil para testing)
    
    Args:
        tension: Tensión en unidades del sensor
    """
    global SIMULATED_TENSION_BASE
    SIMULATED_TENSION_BASE = tension
    print(f"🔧 [DEV] Tensión simulada configurada a {tension}")

def reset_offsets():
    """Resetea todos los offsets de calibración"""
    global _tare_offset, _zero_offset, _belly_tare_offset, _current_stable_weight, _stability_start_time
    _tare_offset = 0.0
    _zero_offset = 0.0
    _belly_tare_offset = 0.0
    # Resetear estabilidad también
    _current_stable_weight = None
    _stability_start_time = None
    print("🔄 [DEV] Offsets de calibración reseteados")

def force_new_stable_weight():
    """
    Fuerza la generación de un nuevo peso estable
    Útil para simular cambio de objeto en la báscula
    """
    global _current_stable_weight, _stability_start_time
    _current_stable_weight = None
    _stability_start_time = None
    print("🔄 [DEV] Forzando nuevo peso estable")

def get_stability_info():
    """
    Retorna información sobre el estado de estabilidad del peso
    
    Returns:
        dict con información de estabilidad
    """
    current_time = time.time()
    time_stable = 0.0
    is_stable = False
    
    if _stability_start_time is not None:
        time_stable = current_time - _stability_start_time
        is_stable = time_stable >= STABILITY_DURATION
    
    return {
        "is_stable": is_stable,
        "time_stable": time_stable,
        "stability_duration_required": STABILITY_DURATION,
        "current_weight": _current_stable_weight,
        "time_until_stable": max(0, STABILITY_DURATION - time_stable)
    }

def get_calibration_info():
    """
    Retorna información sobre el estado de calibración
    
    Returns:
        dict con información de calibración
    """
    return {
        "is_calibrating": isCalibrating,
        "calibration_step": _calibration_step,
        "calibration_points": len(_calibration_points),
        "zero_offset": _zero_offset,
        "tare_offset": _tare_offset,
        "belly_tare_offset": _belly_tare_offset,
        "current_mode": "TENSION" if isOnTensionMode() else "WEIGHT"
    }

# ============================= PARIDAD CON EL HARDWARE REAL =============================
# TLB_MODBUS.py expone estos nombres desde que se corrigió el mapa de registros
# y se empezó a leer el STATUS REGISTER (40007).  El emulador los replica para
# que sockets.py y la UI se comporten igual en DEV_MODE y en producción.

EXPECTED_DIVISION = 0.1


class TLBCommunicationError(RuntimeError):
    """El transmisor no respondió tras todos los reintentos."""


class TLBCalibrationError(RuntimeError):
    """El instrumento rechazó o ignoró un paso de calibración."""


def getDivision():
    """División configurada. El emulador siempre trabaja en décimas de gramo."""
    return EXPECTED_DIVISION


def getUnit():
    return "g"


def clearTare(is_belly=False):
    """Desactiva la tara semiautomática (comando 9 en el equipo real)."""
    global _tare_offset, _belly_tare_offset
    if is_belly:
        _belly_tare_offset = 0.0
    else:
        _tare_offset = 0.0
    print("↩️  [DEV] Tara desactivada")


def readGross():
    """Peso bruto: en el emulador es el neto sin el offset de tara."""
    if isCalibrating:
        return 0.0
    return max(0.0, _generate_weight_reading() + _zero_offset)


def readPeak(is_belly=False):
    """Pico registrado. El emulador no acumula pico, devuelve la lectura actual."""
    if is_belly:
        return readTenstion()
    return readWeight()


def isStable(is_belly=False):
    """Equivalente al bit 11 del STATUS REGISTER."""
    if isCalibrating:
        return False
    if is_belly:
        return True
    return get_stability_info()["is_stable"]


def _snapshot(is_belly=False):
    if isCalibrating:
        return {
            "net": 0.0, "gross": 0.0, "counts_net": 0, "counts_gross": 0,
            "stable": False, "near_zero": False, "net_mode": False,
            "faults": [], "status": 0, "division": EXPECTED_DIVISION,
            "ok": False, "calibrating": True,
        }

    net = readTenstion() if is_belly else readWeight()
    gross = net if is_belly else readGross()
    stable = isStable(is_belly)

    return {
        "net": round(net, 4),
        "gross": round(gross, 4),
        "counts_net": int(round(net / EXPECTED_DIVISION)),
        "counts_gross": int(round(gross / EXPECTED_DIVISION)),
        "stable": stable,
        "near_zero": abs(net) < EXPECTED_DIVISION / 4,
        "net_mode": True,
        "faults": [],
        "status": (1 << 11) if stable else 0,
        "division": EXPECTED_DIVISION,
        "ok": True,
    }


def readWeightSnapshot():
    """Lectura completa de peso neto: valor, estabilidad y fallas."""
    return _snapshot(is_belly=False)


def readTensionSnapshot():
    """Lectura completa de tensión."""
    return _snapshot(is_belly=True)


def add_calibration_point(sample_grams, is_belly=False):
    """Punto de linealización adicional (comando 106 en el equipo real)."""
    _calibration_points.append(float(sample_grams))
    print(f"📌 [DEV] Punto de calibración agregado: {sample_grams}g "
          f"(total: {len(_calibration_points)})")


def cancel_calibration(is_belly=False):
    """Cancela la calibración real (comando 104 en el equipo real)."""
    global _calibration_points
    _calibration_points = []
    print("🚫 [DEV] Calibración real cancelada")


# ============================= INICIALIZACIÓN =============================

print("\n" + "="*70)
print("🚀 TLB_MODBUS Emulator v1.0 - Development Mode")
print("="*70)
print("📝 Emulando weight transmitter sin hardware físico")
print(f"⚖️  Peso base: {SIMULATED_WEIGHT_BASE}g ± {WEIGHT_VARIATION}g")
print(f"🔬 Tensión base: {SIMULATED_TENSION_BASE} ± {TENSION_VARIATION}")
print(f"⏱️  Estabilidad: {STABILITY_DURATION}s (para detección de peso estable)")
print("✅ Módulo listo para testing\n")

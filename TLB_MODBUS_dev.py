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

def setZero():
    """Establece el punto cero de la báscula"""
    global _zero_offset
    
    # Simular el ajuste de cero
    current_reading = _generate_weight_reading()
    _zero_offset = -current_reading
    
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

def setTare(is_belly):
    """Establece la tara de la báscula o belly"""
    global _tare_offset, _belly_tare_offset
    
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
        current_reading = _generate_weight_reading()
        _tare_offset = -current_reading
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
    """Genera una lectura de peso realista con variación"""
    # Peso base con variación lenta (simula objeto real)
    slow_variation = random.uniform(-WEIGHT_VARIATION, WEIGHT_VARIATION)
    # Ruido rápido (simula vibraciones, aire, etc.)
    noise = random.uniform(-WEIGHT_NOISE, WEIGHT_NOISE)
    
    return SIMULATED_WEIGHT_BASE + slow_variation + noise

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
    global SIMULATED_WEIGHT_BASE
    SIMULATED_WEIGHT_BASE = weight
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
    global _tare_offset, _zero_offset, _belly_tare_offset
    _tare_offset = 0.0
    _zero_offset = 0.0
    _belly_tare_offset = 0.0
    print("🔄 [DEV] Offsets de calibración reseteados")

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

# ============================= INICIALIZACIÓN =============================

print("\n" + "="*70)
print("🚀 TLB_MODBUS Emulator v1.0 - Development Mode")
print("="*70)
print("📝 Emulando weight transmitter sin hardware físico")
print(f"⚖️  Peso base: {SIMULATED_WEIGHT_BASE}g ± {WEIGHT_VARIATION}g")
print(f"🔬 Tensión base: {SIMULATED_TENSION_BASE} ± {TENSION_VARIATION}")
print("✅ Módulo listo para testing\n")

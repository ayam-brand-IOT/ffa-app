# TLB_Modbus_emulado.py

import time

# Variables de estado (similares a las del módulo real)
SLAVE_ID = 1
BELLY_TEST_ID = 2

__WEIGHT_MODE = 0
__TENSION_MODE = 1

READING_MODE = __WEIGHT_MODE
isCalibrating = False

# Funciones de consulta de modo
def isOnTensionMode():
    return READING_MODE == __TENSION_MODE

def enterToTensionTest():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __TENSION_MODE
    print("[Emulado] Modo tensión activado.")

def enterToWeightMode():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __WEIGHT_MODE
    print("[Emulado] Modo peso activado.")

# Función para poner a cero
def setZero():
    print("[Emulado] Configurando a cero.")

# Función para tara
def setTare(is_belly):
    if is_belly:
        print("[Emulado] Ejecutando tara en belly.")
    else:
        print("[Emulado] Ejecutando tara normal.")

# Funciones para lectura de peso y tensión (retornan valores simulados)
def readWeight():
    global isCalibrating
    if isCalibrating:
        return 0
    simulated_weight = 123.4  # valor simulado
    print(f"[Emulado] Peso leído: {simulated_weight}")
    return simulated_weight

def readTenstion():
    global isCalibrating
    if isCalibrating:
        return 0
    simulated_tension = 56.7  # valor simulado
    print(f"[Emulado] Tensión leída: {simulated_tension}")
    return simulated_tension

# Funciones de calibración (simulación de interacción)
def physical_calibration():
    print("[Emulado] Calibración física iniciada: No coloque nada en la báscula.\nPresione Enter para continuar.")
    input("[Emulado] Presione Enter para simular el inicio de calibración...")
    print("[Emulado] Simulando escritura de registro de calibración...")
    input("[Emulado] Presione Enter para simular el guardado del primer punto de calibración...")
    should_continue = input("[Emulado] ¿Desea agregar más puntos de calibración? (y/n): ")
    if should_continue.lower() == "n":
        print("[Emulado] Finalizando calibración.")
        return
    input("[Emulado] Presione Enter para simular el siguiente punto de calibración...")
    print("[Emulado] Simulación de calibración completada.")

def remote_calibration(step, args):
    global isCalibrating
    if args == "belly":
        print("[Emulado] Seleccionado modo 'belly' para calibración remota.")
    if step == 1:
        print("[Emulado] Paso 1: Configurando a cero.")
    elif step == 2:
        print("[Emulado] Paso 2: Ejecutando tara remota.")
    elif step == 3:
        print("[Emulado] Paso 3: Guardando puntos de calibración.")
    elif step == 4:
        print("[Emulado] Paso 4: Finalizando calibración remota.")
        isCalibrating = False

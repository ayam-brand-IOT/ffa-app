#!/usr/bin/env python3
"""
Script de prueba para TLB_MODBUS_dev.py
Verifica que todas las funciones del emulador funcionen correctamente
"""

import sys
import time

import _bootstrap  # noqa: F401 - adds project root to sys.path

# Importar el emulador
import TLB_MODBUS_dev as net

def test_basic_functionality():
    """Prueba funcionalidad básica"""
    print("\n" + "="*70)
    print("TEST 1: Funcionalidad Básica")
    print("="*70)
    
    # Test modo inicial
    print("\n📋 Verificando modo inicial...")
    assert not net.isOnTensionMode(), "Debería iniciar en modo peso"
    print("✅ Modo peso inicial correcto")
    
    # Test lectura de peso
    print("\n📋 Probando lectura de peso...")
    weight = net.readWeight()
    print(f"   Peso leído: {weight:.2f}g")
    assert isinstance(weight, (int, float)), "readWeight debe retornar número"
    assert weight >= 0, "Peso no puede ser negativo"
    print("✅ Lectura de peso funciona")
    
    # Test cambio a modo tensión
    print("\n📋 Cambiando a modo tensión...")
    net.enterToTensionTest()
    assert net.isOnTensionMode(), "Debería estar en modo tensión"
    print("✅ Cambio a modo tensión exitoso")
    
    # Test lectura de tensión
    print("\n📋 Probando lectura de tensión...")
    tension = net.readTenstion()
    print(f"   Tensión leída: {tension:.2f}")
    assert isinstance(tension, (int, float)), "readTenstion debe retornar número"
    assert tension >= 0, "Tensión no puede ser negativa"
    print("✅ Lectura de tensión funciona")
    
    # Regresar a modo peso
    print("\n📋 Regresando a modo peso...")
    net.enterToWeightMode()
    assert not net.isOnTensionMode(), "Debería estar en modo peso"
    print("✅ Cambio a modo peso exitoso")

def test_calibration_commands():
    """Prueba comandos de calibración"""
    print("\n" + "="*70)
    print("TEST 2: Comandos de Calibración")
    print("="*70)
    
    # Test setZero
    print("\n📋 Probando setZero...")
    net.setZero()
    weight_after_zero = net.readWeight()
    print(f"   Peso después de zero: {weight_after_zero:.2f}g")
    print("✅ setZero ejecutado")
    
    # Test setTare
    print("\n📋 Probando setTare (normal)...")
    net.setTare(False)
    weight_after_tare = net.readWeight()
    print(f"   Peso después de tare: {weight_after_tare:.2f}g")
    print("✅ setTare (normal) ejecutado")
    
    # Test setTare belly
    print("\n📋 Probando setTare (belly)...")
    net.enterToTensionTest()
    net.setTare(True)
    tension_after_tare = net.readTenstion()
    print(f"   Tensión después de tare: {tension_after_tare:.2f}")
    print("✅ setTare (belly) ejecutado")
    
    net.enterToWeightMode()

def test_remote_calibration():
    """Prueba calibración remota"""
    print("\n" + "="*70)
    print("TEST 3: Calibración Remota")
    print("="*70)
    
    print("\n📋 Simulando calibración remota completa...")
    
    # Paso 1: Zero
    print("\n   Paso 1/4: Configurando cero...")
    net.remote_calibration(1, "normal")
    
    # Paso 2: Tara de calibración
    print("   Paso 2/4: Tara de calibración...")
    net.remote_calibration(2, "normal")
    
    # Paso 3: Guardar punto
    print("   Paso 3/4: Guardando punto de calibración...")
    net.remote_calibration(3, "normal")
    
    # Paso 4: Finalizar
    print("   Paso 4/4: Finalizando calibración...")
    net.remote_calibration(4, "normal")
    
    print("\n✅ Calibración remota completada")
    
    # Test calibración belly
    print("\n📋 Simulando calibración remota (belly)...")
    net.remote_calibration(1, "belly")
    net.remote_calibration(2, "belly")
    net.remote_calibration(3, "belly")
    net.remote_calibration(4, "belly")
    print("✅ Calibración remota (belly) completada")

def test_reading_variations():
    """Prueba que las lecturas varíen de forma realista"""
    print("\n" + "="*70)
    print("TEST 4: Variaciones de Lectura")
    print("="*70)

    # Previous calibration tests intentionally leave tare offsets active.
    # Isolate this test so it measures the simulated sensor variation itself.
    net.reset_offsets()
    
    print("\n📋 Tomando 10 lecturas de peso...")
    weights = []
    for i in range(10):
        w = net.readWeight()
        weights.append(w)
        print(f"   Lectura {i+1}: {w:.2f}g")
        time.sleep(0.1)
    
    # Verificar que hay variación
    min_weight = min(weights)
    max_weight = max(weights)
    variation = max_weight - min_weight
    
    print(f"\n📊 Estadísticas:")
    print(f"   Mínimo: {min_weight:.2f}g")
    print(f"   Máximo: {max_weight:.2f}g")
    print(f"   Variación: {variation:.2f}g")
    print(f"   Promedio: {sum(weights)/len(weights):.2f}g")
    
    assert variation > 0, "Las lecturas deben variar"
    assert variation < 10, "La variación no debe ser excesiva"
    print("✅ Variación realista detectada")

def test_calibrating_state():
    """Prueba que isCalibrating funcione correctamente"""
    print("\n" + "="*70)
    print("TEST 5: Estado de Calibración")
    print("="*70)
    
    print("\n📋 Verificando estado normal...")
    net.isCalibrating = False
    weight = net.readWeight()
    assert weight > 0, "Debe leer peso cuando no está calibrando"
    print(f"   Peso en modo normal: {weight:.2f}g")
    print("✅ Lectura normal funciona")
    
    print("\n📋 Activando modo calibración...")
    net.isCalibrating = True
    weight = net.readWeight()
    tension = net.readTenstion()
    assert weight == 0, "Debe retornar 0 durante calibración"
    assert tension == 0, "Debe retornar 0 durante calibración"
    print("   Peso durante calibración: 0g")
    print("   Tensión durante calibración: 0")
    print("✅ Estado de calibración funciona")
    
    # Resetear
    net.isCalibrating = False

def test_helper_functions():
    """Prueba funciones auxiliares del emulador"""
    print("\n" + "="*70)
    print("TEST 6: Funciones Auxiliares")
    print("="*70)
    
    # Test set_simulated_weight
    print("\n📋 Probando set_simulated_weight...")
    net.set_simulated_weight(500.0)
    weights = [net.readWeight() for _ in range(5)]
    avg_weight = sum(weights) / len(weights)
    assert 490 < avg_weight < 510, "Peso promedio debe estar cerca de 500g"
    print(f"   Peso promedio con base 500g: {avg_weight:.2f}g")
    print("✅ set_simulated_weight funciona")
    
    # Test set_simulated_tension
    print("\n📋 Probando set_simulated_tension...")
    net.enterToTensionTest()
    net.set_simulated_tension(100.0)
    tensions = [net.readTenstion() for _ in range(5)]
    avg_tension = sum(tensions) / len(tensions)
    assert 90 < avg_tension < 110, "Tensión promedio debe estar cerca de 100"
    print(f"   Tensión promedio con base 100: {avg_tension:.2f}")
    print("✅ set_simulated_tension funciona")
    net.enterToWeightMode()
    
    # Test reset_offsets
    print("\n📋 Probando reset_offsets...")
    net.setZero()
    net.setTare(False)
    net.reset_offsets()
    info = net.get_calibration_info()
    assert info['zero_offset'] == 0, "Zero offset debe ser 0 después de reset"
    assert info['tare_offset'] == 0, "Tare offset debe ser 0 después de reset"
    print("✅ reset_offsets funciona")
    
    # Test get_calibration_info
    print("\n📋 Probando get_calibration_info...")
    info = net.get_calibration_info()
    print(f"   Información de calibración:")
    for key, value in info.items():
        print(f"      {key}: {value}")
    assert isinstance(info, dict), "Debe retornar diccionario"
    assert 'current_mode' in info, "Debe incluir modo actual"
    print("✅ get_calibration_info funciona")

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n")
    print("🔥" * 35)
    print("SUITE DE TESTS - TLB_MODBUS_dev.py")
    print("🔥" * 35)
    
    try:
        test_basic_functionality()
        test_calibration_commands()
        test_remote_calibration()
        test_reading_variations()
        test_calibrating_state()
        test_helper_functions()
        
        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*70)
        print("\n🎉 El emulador TLB_MODBUS_dev está funcionando correctamente")
        print("✅ Listo para usar en desarrollo/testing")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FALLIDO: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

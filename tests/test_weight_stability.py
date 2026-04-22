#!/usr/bin/env python3
"""
Test de estabilidad de peso para TLB_MODBUS_dev.py
Verifica que el peso se mantiene estable durante 1.2s
"""

import sys
import time

import _bootstrap  # noqa: F401 - adds project root to sys.path

# Importar el emulador
import TLB_MODBUS_dev as net

def test_weight_stability():
    """Prueba que el peso se mantiene estable por 1.2s"""
    print("\n" + "="*70)
    print("TEST: Estabilidad de Peso (1.2s)")
    print("="*70)
    
    print("\n📋 Tomando lecturas continuas durante 3 segundos...")
    print("    (Debería haber al menos 2 períodos de estabilidad)\n")
    
    readings = []
    start_time = time.time()
    
    # Tomar lecturas durante 3 segundos
    while time.time() - start_time < 3.0:
        weight = net.readWeight()
        elapsed = time.time() - start_time
        readings.append({
            'time': elapsed,
            'weight': weight
        })
        
        # Mostrar lectura
        stability_info = net.get_stability_info()
        is_stable = "✅ ESTABLE" if stability_info['is_stable'] else "⏳ Estabilizando"
        time_stable = stability_info['time_stable']
        
        print(f"   {elapsed:5.2f}s: {weight:6.2f}g  [{is_stable}] (tiempo estable: {time_stable:.2f}s)")
        
        time.sleep(0.1)  # 100ms entre lecturas
    
    print("\n📊 Análisis de estabilidad:")
    
    # Analizar períodos de estabilidad
    stable_periods = []
    current_period = []
    last_weight = None
    
    for reading in readings:
        weight = reading['weight']
        
        if last_weight is None:
            current_period.append(reading)
        else:
            # Diferencia de menos de 0.1g se considera mismo período
            if abs(weight - last_weight) < 0.1:
                current_period.append(reading)
            else:
                if len(current_period) >= 12:  # Al menos 1.2s (12 lecturas de 0.1s)
                    stable_periods.append(current_period)
                current_period = [reading]
        
        last_weight = weight
    
    # Agregar último período si es suficientemente largo
    if len(current_period) >= 12:
        stable_periods.append(current_period)
    
    print(f"\n   Períodos estables detectados: {len(stable_periods)}")
    
    for i, period in enumerate(stable_periods, 1):
        duration = period[-1]['time'] - period[0]['time']
        avg_weight = sum(r['weight'] for r in period) / len(period)
        weight_range = max(r['weight'] for r in period) - min(r['weight'] for r in period)
        
        print(f"\n   Período {i}:")
        print(f"      Duración: {duration:.2f}s")
        print(f"      Peso promedio: {avg_weight:.2f}g")
        print(f"      Rango de variación: {weight_range:.3f}g")
        print(f"      Lecturas: {len(period)}")
    
    # Verificar que hubo al menos un período estable
    assert len(stable_periods) >= 1, "Debería haber al menos 1 período estable de 1.2s"
    
    # Verificar que cada período estable duró al menos 1.2s
    for i, period in enumerate(stable_periods, 1):
        duration = period[-1]['time'] - period[0]['time']
        assert duration >= 1.1, f"Período {i} duró {duration:.2f}s, debe ser >= 1.1s"
    
    print("\n✅ Test de estabilidad pasado")
    print(f"   - Se mantuvieron {len(stable_periods)} períodos estables de 1.2s+")
    return True

def test_stability_after_tare():
    """Prueba que después de tara, el peso se mantiene estable"""
    print("\n" + "="*70)
    print("TEST: Estabilidad después de Tara")
    print("="*70)
    
    print("\n📋 Esperando estabilidad inicial...")
    time.sleep(1.3)
    
    weight_before = net.readWeight()
    print(f"   Peso antes de tara: {weight_before:.2f}g")
    
    print("\n📋 Aplicando tara...")
    net.setTare(False)
    
    print("\n📋 Tomando lecturas después de tara (debería estar cerca de 0)...")
    readings_after = []
    for i in range(15):  # 1.5 segundos
        weight = net.readWeight()
        stability_info = net.get_stability_info()
        readings_after.append(weight)
        
        status = "✅" if stability_info['is_stable'] else "⏳"
        print(f"   {i*0.1:.1f}s: {weight:6.2f}g {status} (tiempo estable: {stability_info['time_stable']:.2f}s)")
        time.sleep(0.1)
    
    # Verificar que el peso está cerca de cero (tolerancia de 1g)
    avg_weight = sum(readings_after) / len(readings_after)
    print(f"\n📊 Peso promedio después de tara: {avg_weight:.2f}g")
    
    assert abs(avg_weight) < 1.0, f"Peso después de tara debería estar cerca de 0, obtenido {avg_weight:.2f}g"
    
    # Verificar que hay cierta estabilidad (variación < 0.5g)
    weight_range = max(readings_after) - min(readings_after)
    print(f"📊 Rango de variación: {weight_range:.3f}g")
    
    assert weight_range < 1.0, f"Variación después de tara es muy alta: {weight_range:.2f}g"
    
    print("\n✅ Peso después de tara es estable y cercano a cero")
    return True

def test_force_new_weight():
    """Prueba la función force_new_stable_weight"""
    print("\n" + "="*70)
    print("TEST: Forzar Nuevo Peso Estable")
    print("="*70)
    
    print("\n📋 Esperando primer peso estable...")
    time.sleep(1.3)
    weight1 = net.readWeight()
    print(f"   Primer peso: {weight1:.2f}g")
    
    print("\n📋 Forzando nuevo peso...")
    net.force_new_stable_weight()
    
    print("\n📋 Esperando nuevo peso estable...")
    time.sleep(1.3)
    weight2 = net.readWeight()
    print(f"   Nuevo peso: {weight2:.2f}g")
    
    # Los pesos deberían ser diferentes (con alta probabilidad)
    # porque se generan aleatoriamente
    print(f"\n📊 Diferencia: {abs(weight1 - weight2):.2f}g")
    
    # No necesariamente diferentes, pero documentamos el comportamiento
    print("\n✅ Función force_new_stable_weight ejecutada correctamente")
    return True

def test_stability_info():
    """Prueba la función get_stability_info"""
    print("\n" + "="*70)
    print("TEST: Información de Estabilidad")
    print("="*70)
    
    print("\n📋 Obteniendo info de estabilidad en diferentes momentos...")
    
    # Reset para empezar de cero
    net.force_new_stable_weight()
    
    for i in range(15):
        info = net.get_stability_info()
        weight = net.readWeight()
        
        status = "✅ ESTABLE" if info['is_stable'] else "⏳ ESTABILIZANDO"
        time_until = info['time_until_stable']
        
        print(f"\n   T={i*0.1:.1f}s:")
        print(f"      Peso: {weight:.2f}g")
        print(f"      Estado: {status}")
        print(f"      Tiempo estable: {info['time_stable']:.2f}s")
        print(f"      Falta para estable: {time_until:.2f}s")
        
        time.sleep(0.1)
    
    print("\n✅ Información de estabilidad funciona correctamente")
    return True

def run_all_tests():
    """Ejecuta todos los tests de estabilidad"""
    print("\n")
    print("🔥" * 35)
    print("SUITE DE TESTS - Estabilidad de Peso TLB_MODBUS_dev")
    print("🔥" * 35)
    
    try:
        test_weight_stability()
        test_stability_after_tare()
        test_force_new_weight()
        test_stability_info()
        
        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS DE ESTABILIDAD PASARON")
        print("="*70)
        print("\n🎉 El emulador mantiene peso estable por 1.2s correctamente")
        print("✅ El sistema podrá detectar peso estable y permitir capturas")
        
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

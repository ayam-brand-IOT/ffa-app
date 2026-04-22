#!/usr/bin/env python3
"""
Script de prueba para IOs_dev.py
Verifica que todas las funciones del emulador GPIO funcionen correctamente
"""

import sys
import time

import _bootstrap  # noqa: F401 - adds project root to sys.path

# Importar el emulador
import IOs_dev as ios

def test_basic_gpio_operations():
    """Prueba operaciones básicas de GPIO"""
    print("\n" + "="*70)
    print("TEST 1: Operaciones Básicas GPIO")
    print("="*70)
    
    # Test set_laser
    print("\n📋 Probando set_laser(1)...")
    ios.set_laser(1)
    state = ios.get_laser_state()
    assert state['is_lit'] == True, "Laser debería estar encendido"
    assert state['value'] == 1, "Valor debería ser 1"
    print("✅ Laser encendido correctamente")
    
    print("\n📋 Probando set_laser(0)...")
    ios.set_laser(0)
    state = ios.get_laser_state()
    assert state['is_lit'] == False, "Laser debería estar apagado"
    assert state['value'] == 0, "Valor debería ser 0"
    print("✅ Laser apagado correctamente")
    
    # Test set_flash
    print("\n📋 Probando set_flash(1)...")
    ios.set_flash(1)
    state = ios.get_flash_state()
    assert state['is_lit'] == True, "Flash debería estar encendido"
    print("✅ Flash encendido correctamente")
    
    print("\n📋 Probando set_flash(0)...")
    ios.set_flash(0)
    state = ios.get_flash_state()
    assert state['is_lit'] == False, "Flash debería estar apagado"
    print("✅ Flash apagado correctamente")

def test_toggle_laser():
    """Prueba la función toggle_laser"""
    print("\n" + "="*70)
    print("TEST 2: Toggle Laser")
    print("="*70)
    
    # Asegurar que empieza apagado
    ios.set_laser(0)
    
    print("\n📋 Primera llamada a toggle_laser()...")
    ios.toggle_laser()
    state = ios.get_laser_state()
    assert state['is_lit'] == True, "Laser debería encenderse"
    print("✅ Laser encendido por toggle")
    
    print("\n📋 Segunda llamada a toggle_laser()...")
    ios.toggle_laser()
    state = ios.get_laser_state()
    assert state['is_lit'] == False, "Laser debería apagarse"
    print("✅ Laser apagado por toggle")

def test_timered_flash():
    """Prueba la función timered_flash con timer"""
    print("\n" + "="*70)
    print("TEST 3: Timered Flash (con espera de 2.5s)")
    print("="*70)
    
    # Reset inicial
    ios.reset_all()
    
    print("\n📋 Llamando timered_flash()...")
    ios.timered_flash()
    
    # Verificar estado inmediato
    time.sleep(0.1)  # Pequeña pausa para que se ejecute
    flash_state = ios.get_flash_state()
    laser_state = ios.get_laser_state()
    
    print("\n📊 Estado inmediato (después de llamar):")
    print(f"   Flash: {'ON' if flash_state['is_lit'] else 'OFF'}")
    print(f"   Laser: {'ON' if laser_state['is_lit'] else 'OFF'}")
    
    assert flash_state['is_lit'] == True, "Flash debería estar ON inmediatamente"
    assert laser_state['is_lit'] == False, "Laser debería estar OFF inmediatamente"
    print("✅ Estado inicial correcto")
    
    # Esperar a que el timer complete
    print("\n⏳ Esperando 2 segundos para que complete el timer...")
    time.sleep(2.2)  # Esperar un poco más de 2 segundos
    
    # Verificar estado final
    flash_state = ios.get_flash_state()
    laser_state = ios.get_laser_state()
    
    print("\n📊 Estado después del timer (2s):")
    print(f"   Flash: {'ON' if flash_state['is_lit'] else 'OFF'}")
    print(f"   Laser: {'ON' if laser_state['is_lit'] else 'OFF'}")
    
    assert flash_state['is_lit'] == False, "Flash debería estar OFF después del timer"
    # El laser debería haberse toggled, pero como estaba OFF, ahora está ON
    assert laser_state['is_lit'] == True, "Laser debería estar ON después del toggle"
    print("✅ Estado final correcto después del timer")

def test_get_all_states():
    """Prueba la función get_all_states"""
    print("\n" + "="*70)
    print("TEST 4: Get All States")
    print("="*70)
    
    # Configurar un estado conocido
    ios.set_laser(1)
    ios.set_flash(0)
    
    print("\n📋 Obteniendo estado de todos los GPIOs...")
    states = ios.get_all_states()
    
    print("\n📊 Estados obtenidos:")
    print(f"   Laser Pin: {states['laser']['pin']}")
    print(f"   Laser State: {'ON' if states['laser']['is_lit'] else 'OFF'}")
    print(f"   Flash Pin: {states['flash']['pin']}")
    print(f"   Flash State: {'ON' if states['flash']['is_lit'] else 'OFF'}")
    
    assert states['laser']['is_lit'] == True, "Laser debería estar ON"
    assert states['flash']['is_lit'] == False, "Flash debería estar OFF"
    assert isinstance(states['laser']['pin'], int), "Pin debería ser entero"
    assert isinstance(states['flash']['pin'], int), "Pin debería ser entero"
    print("✅ get_all_states funciona correctamente")

def test_reset_all():
    """Prueba la función reset_all"""
    print("\n" + "="*70)
    print("TEST 5: Reset All")
    print("="*70)
    
    # Encender todo
    ios.set_laser(1)
    ios.set_flash(1)
    
    print("\n📋 Estado antes del reset:")
    states_before = ios.get_all_states()
    print(f"   Laser: {'ON' if states_before['laser']['is_lit'] else 'OFF'}")
    print(f"   Flash: {'ON' if states_before['flash']['is_lit'] else 'OFF'}")
    
    print("\n📋 Ejecutando reset_all()...")
    ios.reset_all()
    
    print("\n📋 Estado después del reset:")
    states_after = ios.get_all_states()
    print(f"   Laser: {'ON' if states_after['laser']['is_lit'] else 'OFF'}")
    print(f"   Flash: {'ON' if states_after['flash']['is_lit'] else 'OFF'}")
    
    assert states_after['laser']['is_lit'] == False, "Laser debería estar OFF"
    assert states_after['flash']['is_lit'] == False, "Flash debería estar OFF"
    print("✅ reset_all funciona correctamente")

def test_verbose_mode():
    """Prueba el control de modo verbose"""
    print("\n" + "="*70)
    print("TEST 6: Modo Verbose")
    print("="*70)
    
    print("\n📋 Desactivando modo verbose...")
    ios.set_verbose(False)
    
    print("📋 Operaciones sin verbose (no deberías ver mensajes detallados):")
    ios.set_laser(1)
    ios.set_laser(0)
    
    print("\n📋 Reactivando modo verbose...")
    ios.set_verbose(True)
    
    print("📋 Operaciones con verbose (deberías ver mensajes detallados):")
    ios.set_laser(1)
    ios.set_laser(0)
    
    print("✅ Modo verbose funciona correctamente")

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n")
    print("🔥" * 35)
    print("SUITE DE TESTS - IOs_dev.py (GPIO Emulator)")
    print("🔥" * 35)
    
    try:
        test_basic_gpio_operations()
        test_toggle_laser()
        test_timered_flash()
        test_get_all_states()
        test_reset_all()
        test_verbose_mode()
        
        print("\n" + "="*70)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*70)
        print("\n🎉 El emulador IOs_dev está funcionando correctamente")
        print("✅ Listo para usar en desarrollo/testing")
        print("\n💡 Tip: En main.py, usa 'import IOs_dev as ios' cuando DEV_MODE=True")
        
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

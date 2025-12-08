#!/usr/bin/env python3
"""
Test de validación de vocabulario estandarizado de logs
Verifica que las constantes y validaciones funcionen correctamente
"""

import sys
from log_constants import *
from logger import logEvent, LogValidationError

def test_allowed_status():
    """Test de STATUS permitidos"""
    print("\n" + "="*70)
    print("TEST 1: STATUS Permitidos")
    print("="*70)
    
    print(f"\nSTATUS permitidos: {sorted(ALLOWED_STATUS)}")
    
    # Test valores válidos
    for status in ALLOWED_STATUS:
        try:
            validate_status(status)
            print(f"✅ '{status}' - válido")
        except LogValidationError as e:
            print(f"❌ '{status}' - ERROR: {e}")
            return False
    
    # Test valor inválido
    try:
        validate_status("INVALID")
        print(f"❌ 'INVALID' debería fallar pero no lo hizo")
        return False
    except LogValidationError:
        print(f"✅ 'INVALID' - correctamente rechazado")
    
    print("\n✅ Test de STATUS completado")
    return True

def test_allowed_etapas():
    """Test de ETAPAS permitidas"""
    print("\n" + "="*70)
    print("TEST 2: ETAPAS Permitidas")
    print("="*70)
    
    print(f"\nETAPAS permitidas: {sorted(ALLOWED_ETAPAS)}")
    
    # Test valores válidos
    for etapa in ALLOWED_ETAPAS:
        try:
            validate_etapa(etapa)
            print(f"✅ '{etapa}' - válido")
        except LogValidationError as e:
            print(f"❌ '{etapa}' - ERROR: {e}")
            return False
    
    # Test valor inválido
    try:
        validate_etapa("INVALID_STAGE")
        print(f"❌ 'INVALID_STAGE' debería fallar pero no lo hizo")
        return False
    except LogValidationError:
        print(f"✅ 'INVALID_STAGE' - correctamente rechazado")
    
    print("\n✅ Test de ETAPAS completado")
    return True

def test_error_codes():
    """Test de códigos de error"""
    print("\n" + "="*70)
    print("TEST 3: Códigos de Error")
    print("="*70)
    
    print(f"\nTotal de códigos de error definidos: {len(ERROR_CODES)}")
    
    # Mostrar algunos ejemplos
    print("\nEjemplos de códigos de error:")
    for code in list(ERROR_CODES.keys())[:5]:
        desc = get_error_description(code)
        print(f"   {code}: {desc}")
    
    # Test validación de código válido
    try:
        validate_error_code("APP_CRASH")
        print("\n✅ 'APP_CRASH' - válido")
    except LogValidationError as e:
        print(f"\n❌ 'APP_CRASH' - ERROR: {e}")
        return False
    
    # Test validación de código inválido
    try:
        validate_error_code("INVALID_CODE")
        print(f"❌ 'INVALID_CODE' debería fallar pero no lo hizo")
        return False
    except LogValidationError:
        print(f"✅ 'INVALID_CODE' - correctamente rechazado")
    
    # Test get_error_description con código inexistente
    desc = get_error_description("UNKNOWN_CODE")
    assert desc == "Error desconocido", "Descripción por defecto incorrecta"
    print(f"✅ Descripción por defecto funciona: '{desc}'")
    
    print("\n✅ Test de códigos de error completado")
    return True

def test_calibration_types():
    """Test de tipos de calibración"""
    print("\n" + "="*70)
    print("TEST 4: Tipos de Calibración")
    print("="*70)
    
    print(f"\nTipos de calibración: {sorted(CALIBRATION_TYPES)}")
    
    # Test valores válidos
    valid_types = ["load_cell", "length", "zoi", "zero", "tare"]
    for calib_type in valid_types:
        try:
            validate_calibration_type(calib_type)
            print(f"✅ '{calib_type}' - válido")
        except LogValidationError as e:
            print(f"❌ '{calib_type}' - ERROR: {e}")
            return False
    
    # Test valor inválido
    try:
        validate_calibration_type("invalid_calib")
        print(f"❌ 'invalid_calib' debería fallar pero no lo hizo")
        return False
    except LogValidationError:
        print(f"✅ 'invalid_calib' - correctamente rechazado")
    
    print("\n✅ Test de tipos de calibración completado")
    return True

def test_log_validation():
    """Test de validación completa de logs"""
    print("\n" + "="*70)
    print("TEST 5: Validación Completa de Logs")
    print("="*70)
    
    # Test log válido
    print("\n📋 Test 1: Log completamente válido")
    result = validate_log_entry(
        etapa="CAPTURE",
        status="SUCCESS",
        error_code=None,
        strict=False
    )
    assert result["valid"], "Log válido debería pasar"
    print(f"✅ Validación: {result}")
    
    # Test log con etapa inválida
    print("\n📋 Test 2: Log con etapa inválida (strict=False)")
    result = validate_log_entry(
        etapa="INVALID_STAGE",
        status="SUCCESS",
        strict=False
    )
    assert not result["valid"], "Log inválido no debería pasar"
    assert len(result["errors"]) > 0, "Debería tener errores"
    print(f"✅ Validación: {result}")
    
    # Test log con status inválido
    print("\n📋 Test 3: Log con status inválido (strict=False)")
    result = validate_log_entry(
        etapa="CAPTURE",
        status="INVALID_STATUS",
        strict=False
    )
    assert not result["valid"], "Log inválido no debería pasar"
    print(f"✅ Validación: {result}")
    
    # Test log con error_code inválido (solo warning)
    print("\n📋 Test 4: Log con error_code desconocido")
    result = validate_log_entry(
        etapa="CAPTURE",
        status="ERROR",
        error_code="UNKNOWN_ERROR",
        strict=False
    )
    assert result["valid"], "Etapa y status son válidos"
    assert len(result["warnings"]) > 0, "Debería tener warnings"
    print(f"✅ Validación: {result}")
    
    # Test con strict=True
    print("\n📋 Test 5: Validación estricta con etapa inválida")
    try:
        validate_log_entry(
            etapa="INVALID",
            status="SUCCESS",
            strict=True
        )
        print("❌ Debería haber lanzado excepción")
        return False
    except LogValidationError as e:
        print(f"✅ Excepción correctamente lanzada: {e}")
    
    print("\n✅ Test de validación completa completado")
    return True

def test_real_log_calls():
    """Test de llamadas reales a logEvent"""
    print("\n" + "="*70)
    print("TEST 6: Llamadas Reales a logEvent")
    print("="*70)
    
    # Test 1: Log válido normal
    print("\n📋 Test 1: Log válido (non-strict)")
    try:
        logEvent(
            etapa="CAPTURE",
            status="SUCCESS",
            additional_data={"test": "data"}
        )
        print("✅ Log SUCCESS registrado")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 2: Log con warning por etapa inválida (non-strict)
    print("\n📋 Test 2: Log con etapa inválida (non-strict)")
    try:
        logEvent(
            etapa="INVALID_STAGE",
            status="INFO",
            strict_validation=False
        )
        print("✅ Log registrado con advertencia (revisar archivo de log)")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False
    
    # Test 3: Log ERROR con código de error válido
    print("\n📋 Test 3: Log ERROR con código válido")
    try:
        logEvent(
            etapa="CALIBRATION",
            status="ERROR",
            error_code="LOAD_CELL_CALIB_ERROR",
            additional_data={"step": 1}
        )
        print("✅ Log ERROR registrado con código válido")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 4: Log con código de error que obtiene descripción automática
    print("\n📋 Test 4: Log ERROR con auto-descripción")
    try:
        logEvent(
            etapa="CONFIG_UPDATE",
            status="ERROR",
            error_code="CONFIG_READ_ERROR",
            # No se proporciona error_msg, debería usar descripción del código
        )
        print("✅ Log ERROR con descripción automática registrado")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test 5: Validación estricta con etapa inválida
    print("\n📋 Test 5: Validación estricta con etapa inválida")
    try:
        logEvent(
            etapa="WRONG_STAGE",
            status="INFO",
            strict_validation=True
        )
        print("❌ Debería haber lanzado LogValidationError")
        return False
    except LogValidationError as e:
        print(f"✅ Excepción correctamente lanzada: {e}")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False
    
    print("\n✅ Test de llamadas reales completado")
    return True

def test_vocabulary_constants():
    """Test de otras constantes de vocabulario"""
    print("\n" + "="*70)
    print("TEST 7: Constantes de Vocabulario")
    print("="*70)
    
    print(f"\nVersión de vocabulario: {VOCABULARY_VERSION}")
    print(f"Campos requeridos: {sorted(REQUIRED_FIELDS)}")
    print(f"Campos opcionales: {sorted(OPTIONAL_FIELDS)}")
    
    print(f"\nTipos de config: {sorted(CONFIG_TYPES)}")
    print(f"Eventos de sistema: {sorted(SYSTEM_EVENT_TYPES)}")
    print(f"Acciones de captura: {sorted(CAPTURE_ACTIONS)}")
    print(f"Acciones de reset: {sorted(RESET_ACTIONS)}")
    
    print("\n✅ Constantes de vocabulario verificadas")
    return True

def run_all_tests():
    """Ejecuta todos los tests"""
    print("\n")
    print("🔥" * 35)
    print("SUITE DE TESTS - Vocabulario Estandarizado de Logs")
    print("🔥" * 35)
    
    tests = [
        ("STATUS Permitidos", test_allowed_status),
        ("ETAPAS Permitidas", test_allowed_etapas),
        ("Códigos de Error", test_error_codes),
        ("Tipos de Calibración", test_calibration_types),
        ("Validación Completa", test_log_validation),
        ("Llamadas Reales", test_real_log_calls),
        ("Constantes de Vocabulario", test_vocabulary_constants),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"\n❌ Test '{name}' FALLÓ")
        except Exception as e:
            failed += 1
            print(f"\n❌ Test '{name}' FALLÓ con excepción: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"RESUMEN: {passed} tests pasados, {failed} tests fallidos")
    print("="*70)
    
    if failed == 0:
        print("\n🎉 TODOS LOS TESTS PASARON")
        print("✅ Vocabulario estandarizado funcionando correctamente")
        print("\n📝 Logs generados en: logs/ffa_app_events.log")
        return True
    else:
        print(f"\n❌ {failed} tests fallaron")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

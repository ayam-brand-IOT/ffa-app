#!/usr/bin/env python3
"""
Script de verificación de DEV_MODE desde variable de entorno
"""

import os
import sys

print("\n" + "="*70)
print("🧪 TEST: Variable de entorno DEV_MODE")
print("="*70)

# Simular lectura como en main.py
dev_mode_str = os.getenv('DEV_MODE', 'true')
DEV_MODE = dev_mode_str.lower() in ('true', '1', 'yes')

print(f"\n📋 Variable de entorno DEV_MODE: '{dev_mode_str}'")
print(f"📋 Interpretado como boolean: {DEV_MODE}")

if DEV_MODE:
    print("\n✅ Modo: DESARROLLO")
    print("   - Usando TLB_MODBUS_dev (emulador)")
    print("   - Usando IOs_dev (emulador GPIO)")
else:
    print("\n✅ Modo: PRODUCCIÓN")
    print("   - Usando TLB_MODBUS (hardware real)")
    print("   - Usando IOs (hardware real)")

print("\n" + "="*70)
print("🧪 Probando diferentes valores:")
print("="*70)

test_values = ['true', 'True', 'TRUE', '1', 'yes', 'false', 'False', 'FALSE', '0', 'no', '']

for val in test_values:
    os.environ['DEV_MODE'] = val
    dev_mode_str = os.getenv('DEV_MODE', 'true')
    result = dev_mode_str.lower() in ('true', '1', 'yes')
    mode = "DEV" if result else "PROD"
    print(f"   DEV_MODE='{val}' → {mode}")

print("\n✅ Test completado")

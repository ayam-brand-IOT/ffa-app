"""
IOs_dev.py - GPIO Emulator for Development/Testing
===================================================

Este módulo emula la funcionalidad de IOs.py sin necesidad de hardware GPIO real.
Útil para desarrollo en macOS/Windows o testing sin Raspberry Pi.

Características:
- Emula laser y flash como LEDs virtuales
- Imprime estado de los pines en consola con emojis
- Mantiene la misma API que IOs.py
- Incluye timered_flash con comportamiento idéntico
- Logging de todas las operaciones GPIO

Uso:
    En main.py, cambiar:
        import IOs as ios
    Por:
        import IOs_dev as ios
"""

from threading import Timer
from datetime import datetime
import IO_map as io_map

# ============================================================================
# CONFIGURACIÓN DEL EMULADOR
# ============================================================================

VERBOSE_MODE = True  # Mostrar mensajes detallados en consola
LOG_TO_FILE = False  # Guardar log de GPIO en archivo

# ============================================================================
# CLASE LED EMULADA
# ============================================================================

class VirtualLED:
    """
    Clase que emula un LED de gpiozero sin hardware real
    """
    def __init__(self, pin_number, name="LED"):
        self.pin = pin_number
        self.name = name
        self._value = 0  # 0 = OFF, 1 = ON
        self._is_lit = False
        self._log(f"🔌 Inicializado en pin {pin_number}")
    
    @property
    def is_lit(self):
        """Retorna True si el LED está encendido"""
        return self._is_lit
    
    @property
    def value(self):
        """Retorna el valor actual del LED (0 o 1)"""
        return self._value
    
    @value.setter
    def value(self, val):
        """Establece el valor del LED (0 o 1)"""
        if val:
            self.on()
        else:
            self.off()
    
    def on(self):
        """Enciende el LED"""
        if not self._is_lit:
            self._is_lit = True
            self._value = 1
            self._log("💡 ON")
    
    def off(self):
        """Apaga el LED"""
        if self._is_lit:
            self._is_lit = False
            self._value = 0
            self._log("⚫ OFF")
    
    def toggle(self):
        """Alterna el estado del LED"""
        if self._is_lit:
            self.off()
        else:
            self.on()
    
    def _log(self, message):
        """Log interno para operaciones GPIO"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        full_message = f"[{timestamp}] GPIO {self.name} (Pin {self.pin}): {message}"
        
        if VERBOSE_MODE:
            print(full_message)
        
        if LOG_TO_FILE:
            try:
                with open("logs/gpio_emulator.log", "a") as f:
                    f.write(full_message + "\n")
            except:
                pass  # Si no existe el directorio logs, ignorar

# ============================================================================
# INICIALIZACIÓN DE PINES VIRTUALES
# ============================================================================

print("\n" + "="*70)
print("🎮 GPIO Emulator v1.0 - Development Mode")
print("="*70)
print(f"🔌 Inicializando pines virtuales...")
print(f"   Laser Pin: {io_map.__LASER_PIN}")
print(f"   Flash Pin: {io_map.__FLASH_PIN}")
print("✅ GPIO emulator listo para testing")
print("="*70 + "\n")

# Inicializar LEDs virtuales
laser = VirtualLED(io_map.__LASER_PIN, name="LASER")
flash = VirtualLED(io_map.__FLASH_PIN, name="FLASH")

# ============================================================================
# FUNCIONES PÚBLICAS (API IDÉNTICA A IOs.py)
# ============================================================================

def toggle_laser():
    """
    Alterna el estado del laser
    """
    if VERBOSE_MODE:
        print(f"🔄 toggle_laser() llamado")
    laser.toggle()

def set_laser(value):
    """
    Establece el estado del laser
    
    Args:
        value: 1/True para encender, 0/False para apagar
    """
    if VERBOSE_MODE:
        print(f"⚡ set_laser({value}) llamado")
    laser.value = value

def set_flash(value):
    """
    Establece el estado del flash
    
    Args:
        value: 1/True para encender, 0/False para apagar
    """
    if VERBOSE_MODE:
        print(f"⚡ set_flash({value}) llamado")
    flash.value = value

def timered_flash():
    """
    Enciende el flash, apaga el laser, y después de 2 segundos
    apaga el flash y alterna el laser.
    
    Esta función replica exactamente el comportamiento de IOs.py
    """
    if VERBOSE_MODE:
        print("\n" + "─"*70)
        print("⏱️  timered_flash() iniciado")
        print("─"*70)
    
    # Paso 1: Encender flash y apagar laser
    flash.on()
    laser.off()
    
    if VERBOSE_MODE:
        print("⏳ Esperando 2 segundos...")
    
    # Función que se ejecutará después del timer
    def toggle_flash_laser():
        if VERBOSE_MODE:
            print("⏰ Timer completado, ejecutando toggle_flash_laser()")
        flash.off()
        toggle_laser()
        if VERBOSE_MODE:
            print("─"*70 + "\n")
    
    # Iniciar timer de 2 segundos
    timer = Timer(2, toggle_flash_laser)
    timer.start()
    
    if VERBOSE_MODE:
        print("✅ Timer iniciado (2s)")

# ============================================================================
# FUNCIONES AUXILIARES PARA TESTING (NO EN IOs.py ORIGINAL)
# ============================================================================

def get_laser_state():
    """
    Retorna el estado actual del laser
    Returns: dict con información del laser
    """
    return {
        "pin": laser.pin,
        "is_lit": laser.is_lit,
        "value": laser.value
    }

def get_flash_state():
    """
    Retorna el estado actual del flash
    Returns: dict con información del flash
    """
    return {
        "pin": flash.pin,
        "is_lit": flash.is_lit,
        "value": flash.value
    }

def get_all_states():
    """
    Retorna el estado de todos los pines GPIO
    Returns: dict con información completa
    """
    return {
        "laser": get_laser_state(),
        "flash": get_flash_state()
    }

def reset_all():
    """
    Apaga todos los GPIOs (útil para testing)
    """
    if VERBOSE_MODE:
        print("\n🔄 Reseteando todos los GPIOs...")
    laser.off()
    flash.off()
    if VERBOSE_MODE:
        print("✅ Todos los GPIOs apagados\n")

def set_verbose(enabled):
    """
    Activa o desactiva los mensajes detallados
    Args:
        enabled: True para activar, False para desactivar
    """
    global VERBOSE_MODE
    VERBOSE_MODE = enabled
    status = "activado" if enabled else "desactivado"
    print(f"📢 Modo verbose {status}")

def test_sequence():
    """
    Ejecuta una secuencia de prueba de todos los GPIOs
    """
    print("\n" + "="*70)
    print("🧪 SECUENCIA DE PRUEBA GPIO")
    print("="*70)
    
    print("\n1️⃣  Probando Laser...")
    set_laser(1)
    Timer(0.5, lambda: set_laser(0)).start()
    
    print("\n2️⃣  Probando Flash...")
    Timer(1, lambda: set_flash(1)).start()
    Timer(1.5, lambda: set_flash(0)).start()
    
    print("\n3️⃣  Probando timered_flash()...")
    Timer(2, timered_flash).start()
    
    print("\n✅ Secuencia de prueba programada")
    print("="*70 + "\n")

# ============================================================================
# MENSAJE DE INICIALIZACIÓN
# ============================================================================

if __name__ == "__main__":
    print("\n🔥 IOs_dev.py - GPIO Emulator")
    print("\nModo de uso:")
    print("  1. En main.py, importar: import IOs_dev as ios")
    print("  2. Usar las funciones normalmente: ios.set_laser(1)")
    print("  3. Para testing: ios.test_sequence()")
    print("\nFunciones disponibles:")
    print("  - toggle_laser()")
    print("  - set_laser(value)")
    print("  - set_flash(value)")
    print("  - timered_flash()")
    print("  - get_all_states()  [solo en modo dev]")
    print("  - reset_all()       [solo en modo dev]")
    print("  - test_sequence()   [solo en modo dev]")
    
    # Ejecutar secuencia de prueba si se corre directamente
    print("\n🚀 Ejecutando secuencia de prueba...")
    test_sequence()
    
    # Mantener el script vivo para ver los timers
    import time
    time.sleep(6)

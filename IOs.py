from gpiozero import LED, Buzzer
from gpiozero.pins.lgpio import LGPIOFactory
from time import sleep
from threading import Timer
import IO_map as io_map
from logger import logEvent

pin_factory = LGPIOFactory()

# Initialize laser and flash as LEDs
laser = LED(io_map.__LASER_PIN, pin_factory=pin_factory)
flash = LED(io_map.__FLASH_PIN, pin_factory=pin_factory)
# A busy or missing buzzer must never stop weighing: on 2026-10-02 a leftover
# interactive session held GPIO 17 and the whole app failed to start.
try:
    buzzer = Buzzer(io_map.__BUZZER_PIN, pin_factory=pin_factory)
except Exception as exc:  # noqa: BLE001 - lgpio raises its own error type
    buzzer = None
    logEvent(etapa="SYSTEM", status="ERROR", error_code="BUZZER_UNAVAILABLE",
             error_msg=str(exc), additional_data={"gpio": io_map.__BUZZER_PIN})

# Function to toggle the laser state
def toggle_laser():
    if laser.is_lit:
        laser.off()
    else:
        laser.on()

def set_laser(value):
    laser.value = value

def set_flash(value):
    flash.value = value

def set_buzzer(value):
    if buzzer is not None:
        buzzer.value = value

# Function to flash the LED and then toggle the laser after a delay
def timered_flash():
    flash.on()  # Turn on flash
    laser.off()  # Turn off laser

    # Define a function that toggles the flash and the laser
    def toggle_flash_laser():
        flash.off()  # Turn off flash
        toggle_laser()  # Toggle the laser state

    # Start a timer to call the toggle_flash_laser function after 2 seconds
    timer = Timer(2, toggle_flash_laser)
    timer.start()

# Sample usage of the timered_flash function
# timered_flash()
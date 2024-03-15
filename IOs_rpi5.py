import gpiod
import time
import threading
import IO_map as io_map

chip = gpiod.Chip('gpiochip4')  # Para Raspberry Pi 5, el GPIO se encuentra en 'gpiochip4'.
laser_state = False

# Configurar pines de entrada y salida
for index in range(len(io_map.inputs)):
    input_line = chip.get_line(io_map.inputs[index])
    input_line.request(consumer='script', type=gpiod.LINE_REQ_DIR_IN)

    output_line = chip.get_line(io_map.outputs[index])
    output_line.request(consumer='script', type=gpiod.LINE_REQ_DIR_OUT)

def laser(value):
    global laser_state
    laser_state = not laser_state
    laser_line = chip.get_line(io_map.__LASER_PIN)
    laser_line.set_value(value)

def flash(value):
    flash_line = chip.get_line(io_map.__FLASH_PIN)
    flash_line.set_value(value)

def timeredFlash():
    flash(1)   # Encender flash
    laser(0)   # Apagar láser

    def toggle_flash_laser():
        flash(0)  # Apagar flash
        laser(1)   # Encender láser

    temporizer = threading.Timer(2, toggle_flash_laser)
    temporizer.start()

# Descomenta el siguiente bloque para leer de entradas y escribir en salidas continuamente
# while True:
#     for index in range(len(io_map.inputs)):
#         input_line = chip.get_line(io_map.inputs[index])
#         output_line = chip.get_line(io_map.outputs[index])
#         output_line.set_value(input_line.get_value())

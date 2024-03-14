import pigpio
import time
import threading
import IO_map as io_map
 
pi = pigpio.pi()
laser_state = False
 
for index in range(len(io_map.inputs)):
    pi.set_mode(io_map.inputs[index], pigpio.INPUT)
    pi.set_mode(io_map.outputs[index], pigpio.OUTPUT)

def laser(value):
    global laser_state

    laser_state = not laser_state
    pi.write(io_map.__LASER_PIN, value)

def flash(value):
    pi.write(io_map.__FLASH_PIN, value)

def timeredFlash():
    flash(True)   # Encender flash
    laser(False)  # Apagar láser

    # Define una función que apaga el flash y enciende el láser
    def toggle_flash_laser():
        flash(False)  # Apagar flash
        laser(True)   # Encender láser

    # Iniciar un temporizador que llama a la función toggle_flash_laser después de 0.5 segundos
    temporizer = threading.Timer(2, toggle_flash_laser)
    temporizer.start()
 
# while True:
#     for index in range(len(inputs)):
#         pi.write(outputs[index], pi.read(inputs[index]))
# pi.stop()

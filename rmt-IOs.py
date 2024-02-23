import pigpio
import time
import IO_map as io_map
 
pi = pigpio.pi()
laser_state = False
 
for index in range(len(io_map.inputs)):
    pi.set_mode(io_map.inputs[index], pigpio.INPUT)
    pi.set_mode(io_map.outputs[index], pigpio.OUTPUT)

def laser():
    global laser_state

    laser_state = not laser_state
    pi.write(io_map.__LASER_PIN, laser_state)

def flash(value):
    pi.write(io_map.__FLASH_PIN, value)
 
# while True:
#     for index in range(len(inputs)):
#         pi.write(outputs[index], pi.read(inputs[index]))
# pi.stop()


__DEBUGING__ = False

if not __DEBUGING__: 
    from smbus2 import SMBus
    bus = SMBus(1)

import time
import threading
import random

# Open i2c bus 1 and read one byte from address 80, offset 0

time.sleep(2)


local_callback = None

keys = [ '1', '2', '3', 'A', '4', '5', '6', 'B', '7', '8', '9', 'C', '*', '0', '#', 'D' ]
states = [False] * len(keys)

def set_callback(callback):
    global local_callback

    # print("setting callback")
    local_callback = callback

def reset_keys():
    global states

    states = [False] * len(keys)


def get_keys():
    global states

    # print("wheres the keys")
    return states


def async_key_check():
    global states

    while True:
        if __DEBUGING__:
            theres_a_change = check_simulation_keys()
        else:
            theres_a_change = check_keys()
        if theres_a_change:
            local_callback(states)
        
        if __DEBUGING__:
            time.sleep(1)
        else:
            time.sleep(0.1)


def check_keys():
    global states

    try:
        b = bus.read_byte_data(0x2a, 0)
        if b != 0:
            char = chr(b)
            index = keys.index(char)
            states[index] = not states[index]
            # print(char, states[index])
            return True
        else:
            return False
    except:
        sad = "No mames Hugo"
        return False
    

def reset_key(index):
    global states

    states[index] = False


def check_simulation_keys():
    global states
    # print("checking keys")

    theres_a_change = random.randint(0, 1)

    if theres_a_change:
        index = random.randint(0, len(states) - 1)
        char = keys[index]
        states[index] = not states[index]
        # print(char, states[index])
        return True
    else:
        return False

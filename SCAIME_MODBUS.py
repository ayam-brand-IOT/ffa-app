import serial
import time
import minimalmodbus

# Modbus slave ID
SLAVE_ID = 1

isCalibrating = False

# Modbus address 
REG_CMD = 0x90
REG_ANSW = 0x91
NET_ADDRESS = 0x82
TARE_ADDRESS = 0x80 
ZERO_ADDRESS = 0x18
NB_CALIB_SEG = 0x0E
SEG1 = 0x0F
SEG2 = 0x11
SEG3 = 0x13

# Serial port settings
PORT = '/dev/ttyUSB0'
# PORT = '/dev/ttyAMA0'
BAUDRATE = 9600
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_TWO

# Open the serial port
instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)

instrument.serial.parity = PARITY
instrument.serial.baudrate = BAUDRATE
instrument.serial.bytesize = BYTESIZE
instrument.serial.stopbits = STOPBITS
instrument.byteorder = minimalmodbus.BYTEORDER_LITTLE

def answerStatus():
    status = instrument.read_register(REG_ANSW)
    if status == 0: print("Ready")
    if status == 1: print("Executing...")
    if status == 2: print("Success")
    if status == 3: print("Error !!!")
    

def reset():
    instrument.write_register(REG_CMD, 0)
    answerStatus()
    
def setZero():
    reset()
    print("Setting to Zero")
    instrument.write_register(REG_CMD, 0xD8)
    answerStatus()
    
def setDefault():
    reset()
    print("Set Default Parameters")
    instrument.write_register(REG_CMD, 0xD2)
    answerStatus()   
    
def setTare():
    reset()
    print("Tare")
    instrument.write_register(REG_CMD, 0xD4)
    answerStatus()
    
def readWeight():
    global isCalibrating
    if isCalibrating:
        return 0
    weight_modbus = instrument.read_long(NET_ADDRESS, byteorder=3)
    if weight_modbus > 600000:
        weight = 0
    else:
        weight = round(weight_modbus/500)

    return weight

def physical_calibration():
    reset()
    input("Press Enter to start")
    instrument.write_register(REG_CMD, 0xD9)
    answerStatus()
    reset()

    print("Zero calibrating : Don't put anything on the checkweigher")
    input("Press Enter to go to Next Step")
    instrument.write_register(REG_CMD, 0xDA)
    answerStatus()
    reset()

    weight_seg1 = input("1. Place the object of calibration \n2. Write the weight of the object (0-500000) and press Enter to continue : ")
    instrument.write_long(SEG1, int(weight_seg1), byteorder=3)
    instrument.write_register(REG_CMD, 0xDB)
    answerStatus()
    reset()

    input("Save : Press enter to ok")
    instrument.write_register(REG_CMD, 0xDE)
    answerStatus()
    reset()

def remote_calibration(step, args):
       # print variable type
    print(type(step) , type(args))


    if(step == 1):
        reset()
        # input("Press Enter to start")
        instrument.write_register(REG_CMD, 0xD9)
        answerStatus()
        reset()

    elif(step == 2):
        print("Zero calibrating : Don't put anything on the checkweigher")
        # input("Press Enter to go to Next Step")
        instrument.write_register(REG_CMD, 0xDA)
        answerStatus()
        reset()
    
    elif(step == 3):
        weight_seg1 = args

        # weight_seg1 = input("1. Place the object of calibration \n2. Write the weight of the object (0-500000) and press Enter to continue : ")
        instrument.write_long(SEG1, int(weight_seg1), byteorder=3)
        instrument.write_register(REG_CMD, 0xDB)
        answerStatus()
        reset()
    
    elif(step == 4):
        # input("Save : Press enter to ok")
        instrument.write_register(REG_CMD, 0xDE)
        answerStatus()
        reset() 
        
    
    
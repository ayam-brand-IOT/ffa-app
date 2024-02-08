import serial
import time
import minimalmodbus

# Modbus slave ID
SLAVE_ID = 1
BELLY_TEST_ID = 2

__WEIGHT_MODE = 0
__TENSION_MODE = 1

READING_MODE = __WEIGHT_MODE

isCalibrating = False

# Modbus address 
__CMDREG = 0x05 # 5
__NETCALREG = 0x24 # 36
__NETREG = 0x0A # 8
__GROSSREG = 0x08 # 9

# Command register
__CMD_CALIB_TARE = 0x64 # 100
__CMD_TARE_SEMI = 0x07 
__CMD_ZERO = 0x08
__CMD_SAVEFIRST = 0x65 # 101
__CMD_SAVENEXT = 0x6A # 106
__CMD_TARE = 0x48 # 72

# Serial port settings
PORT = '/dev/ttyUSB0'
# PORT = '/dev/ttyS0'
BAUDRATE = 9600
BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_TWO

# Open the serial port
instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
instrument2 = minimalmodbus.Instrument(PORT, BELLY_TEST_ID)

instrument.serial.parity = PARITY
instrument.serial.baudrate = BAUDRATE
instrument.serial.bytesize = BYTESIZE
instrument.serial.stopbits = STOPBITS
instrument.byteorder = minimalmodbus.BYTEORDER_LITTLE

instrument2.serial.parity = PARITY
instrument2.serial.baudrate = BAUDRATE
instrument2.serial.bytesize = BYTESIZE
instrument2.serial.stopbits = STOPBITS
instrument2.byteorder = minimalmodbus.BYTEORDER_LITTLE

# def answerStatus():
#     status = instrument.read_register(REG_ANSW)
#     if status == 0: print("Ready")
#     if status == 1: print("Executing...")
#     if status == 2: print("Success")
#     if status == 3: print("Error !!!")

    
def isOnTensionMode():
    return READING_MODE == __TENSION_MODE

def enterToTensionTest():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __TENSION_MODE

def enterToWeightMode():
    global READING_MODE, isCalibrating
    isCalibrating = False
    READING_MODE = __WEIGHT_MODE

def setZero():
    print("Setting to Zero")
    instrument.write_register(__CMDREG, __CMD_ZERO)
    # answerStatus()
    
def setTare(is_belly):
    if is_belly:
        print("Tare belly")
    else:
        print("Tare")

    calibrating_instrument = (instrument2 if is_belly else instrument)
    calibrating_instrument.write_register(__CMDREG, __CMD_TARE_SEMI)
    # answerStatus()
    
def readWeight():
    global isCalibrating
    if isCalibrating:
        return 0
    weight_modbus = instrument.read_long(__NETREG, byteorder=3)
    # print("Weight: ", weight_modbus)
    return weight_modbus/10

def readTenstion():
    global isCalibrating
    if isCalibrating:
        return 0
    belly_tention = instrument2.read_long(__NETREG, byteorder=3)
    # print("Tension: ", belly_tention)
    return belly_tention/10

def physical_calibration():
    print("Zero calibrating : Don't put anything on the checkweigher \n Press Enter to start")

    instrument.write_register(__CMDREG, __CMD_CALIB_TARE)

    input("1. Place the 1Kg calibration object \nand press Enter to continue : ") 
      
    sample_weight_h = 0x0000  # High register value (0x0000)
    sample_weight_l = 0x2710  # Low register value (0x2710)
    instrument.write_registers(__NETCALREG, [sample_weight_h, sample_weight_l])

    # Save the first sample weight value and remove previously saved values
    input("Save : Press enter to ok")

    instrument.write_register(__CMDREG, __CMD_SAVEFIRST)

    should_continue = input("Do you want to add more calibration points? (y/n) : ")
    if should_continue == "n":
        exit()

    input("1. Place the 2Kg calibration object \nand press Enter to continue : ")

    # Store a sample weight value and keep previously saved values
    instrument.write_register(__CMDREG, __CMD_SAVENEXT)

def remote_calibration(step, args):
    global isCalibrating
       # print variable type
    # print(type(step) , type(args))
    calibrating_instrument = instrument

    if(args == "belly"):
        calibrating_instrument = instrument2

    if(step == 1):
        print("Setting to Zero")
        # instrument.write_register

    elif(step == 2):
        print("Tare")
        calibrating_instrument.write_register(__CMDREG, __CMD_CALIB_TARE)
        # answerStatus()
    
    elif(step == 3):
        print("saving calibration points")
        sample_weight_h = 0x0000  # High register value (0x0000)
        sample_weight_l = 0x2710  # Low register value (0x2710)
        calibrating_instrument.write_registers(__NETCALREG, [sample_weight_h, sample_weight_l])
        calibrating_instrument.write_register(__CMDREG, __CMD_SAVEFIRST)
        # answerStatus()

    elif(step == 4):
        print("bye")
        isCalibrating = False

        # answerStatus()
 
        
    
    

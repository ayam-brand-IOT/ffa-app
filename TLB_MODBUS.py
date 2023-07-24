import serial
import time
import minimalmodbus

# Modbus slave ID
SLAVE_ID = 1
BELLY_TEST_ID = 2

isCalibrating = False

# Modbus address 
__CMDREG = 0x05
__NETCALREG = 0x24
__NETREG = 0x08

# Command register
__CMD_CALIB_TARE = 0x64
__CMD_SAVEFIRST = 0x65
__CMD_SAVENEXT = 0x6A
__CMD_TARE = 0x48 # 72

# Serial port settings
PORT = '/dev/ttyUSB0'
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

    
def setZero():
    print("Setting to Zero")
    raw_weight = readWeight()
    print("raw weight: ", raw_weight)
    sample_weight_h = raw_weight // 65536  # High register value (0x0000)
    sample_weight_l = raw_weight % 65536  # Low register value (0x2710)
    instrument.write_registers(__NETCALREG, [sample_weight_h, sample_weight_l])
    # instrument.write_register(REG_CMD, 0xD3)
    # answerStatus()
    
def setTare():
    print("Tare")
    instrument.write_register(__CMDREG, __CMD_TARE)
    # answerStatus()
    
def readWeight():
    global isCalibrating
    if isCalibrating:
        return 0
    weight_modbus = instrument.read_long(__NETREG, byteorder=3)
    belly_tention = instrument2.read_long(__NETREG, byteorder=3)
    print("Weight: ", weight_modbus)
    print("Belly: ", belly_tention)
    return weight_modbus

def physical_calibration():
    print("Zero calibrating : Don't put anything on the checkweigher \n Press Enter to start")

    setTare()

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
       # print variable type
    # print(type(step) , type(args))
    calibrating_instrument = instrument

    if(args == "belly"):
        calibrating_instrument = instrument2

    if(step == 1):
        print("Setting to Zero")
        # instrument.write_register

    elif(step == 2):
       calibrating_instrument.write_register(__CMDREG, __CMD_CALIB_TARE)
        # answerStatus()
    
    elif(step == 3):
        sample_weight_h = 0x0000  # High register value (0x0000)
        sample_weight_l = 0x2710  # Low register value (0x2710)
        calibrating_instrument.write_registers(__NETCALREG, [sample_weight_h, sample_weight_l])
        # answerStatus()

    elif(step == 4):
        calibrating_instrument.write_register(__CMDREG, __CMD_SAVEFIRST)
        # answerStatus()
 
        
    
    
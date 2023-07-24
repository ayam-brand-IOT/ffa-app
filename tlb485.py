import minimalmodbus
import serial

__CMDREG = 0x05
__NETCALREG = 0x24

__CMD_TARE = 0x64
__CMD_SAVEFIRST = 0x65
__CMD_SAVENEXT = 0x6A

# Configure the Modbus instrument
instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1)  # Replace '/dev/ttyUSB0' with the appropriate serial port and set slave address to 1
instrument.serial = serial.Serial('/dev/ttyUSB0', baudrate=9600, bytesize=8, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO)
instrument.serial.timeout = 1  # Set the timeout

input("Press Enter to start")

# Send the command 100 to the command register (40006) for TARE WEIGHT ZERO SETTING
instrument.write_register(__CMDREG, __CMD_TARE)

input("1. Place the 1Kg calibration object \nand press Enter to continue : ")

# Load the net value as the sample weight on the system and send it to registers 37-38
sample_weight_h = 0x0000  # High register value (0x0000)
sample_weight_l = 0x2710  # Low register value (0x2710)
instrument.write_registers(__NETCALREG, [sample_weight_h, sample_weight_l])

# Save the first sample weight value and remove previously saved values
instrument.write_register(__CMDREG, __CMD_SAVEFIRST)

should_continue = input("Do you want to add more calibration points? (y/n) : ")

if should_continue == "n":
    exit()

input("1. Place the 2Kg calibration object \nand press Enter to continue : ")

# Store a sample weight value and keep previously saved values
instrument.write_register(__CMDREG, __CMD_SAVENEXT)

# Cancel the real calibration and return to theoretical calibration
# instrument.write_register(__CMDREG, 104)
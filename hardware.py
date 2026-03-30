import os

DEV_MODE = os.getenv('DEV_MODE', 'true').lower() in ('true', '1', 'yes')

if DEV_MODE:
    import TLB_MODBUS_dev as net
    import IOs_dev as ios
    print("\n🔧 Modo Desarrollo Activado - Usando emuladores")
else:
    import TLB_MODBUS as net
    import IOs as ios
    print("\n Modo Producción Activado - Usando hardware real")

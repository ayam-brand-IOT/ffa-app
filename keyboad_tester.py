import keyboard

def update_indicator_status(keys):
    print(keys)

keyboard.set_callback(update_indicator_status)
keyboard.start_async_key_check()

while True:
    pass


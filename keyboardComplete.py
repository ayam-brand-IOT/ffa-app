import keyboard

released_keys = []

__DEFFECT_KEYS = {
    'ctrl': 'SC',
    'shift': 'GR',
    'caps lock': 'T',
    'tab': 'ST',
    'esc': 'GC',
    '1': 'BB',
    '2': 'SBB',
    '3': 'HD',
    '4': 'M',
    '5': 'S',
    '6': 'LD',
    '7': 'OS',
    '8': 'OS2',
    '9': 'O2',
    '0': 'FB',
    '-': 'OSM',
}

__ACTION_KEYS = {
    'space': 'CAPTURE',
    'c': 'CANCEL',
    'shift': 'TOGGLE',
}


def on_key_release(event):
    key = event.name
    if key not in released_keys:
        released_keys.append(key)
    else:
        released_keys.remove(key)
    print('Released Keys:', released_keys)

# Register the key release event handler
keyboard.on_release(on_key_release)

# Keep the program running until you press 'q' to quit
while True:
    if keyboard.is_pressed('q'):
        break

# Unregister the event handler
keyboard.unhook_all()

import IOs as ios
import time

while True:
    ios.flash(True)
    time.sleep(.001)
    ios.flash(False)
    time.sleep(.001)
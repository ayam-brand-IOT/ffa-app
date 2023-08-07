from picamera2 import Picamera2
import time
import IOs as ios

__PATH = "./captureTimeTest/"
__TIME_CSV = "./captureTimeTest/captureTime.csv"

# Create a VideoCapture object to access the USB camera
csv = open(__TIME_CSV, "w")
camera = Picamera2()

config = camera.create_preview_configuration(main={"size": (640, 480)})
camera.configure(config)

def take_picture():
    # Capture the image and measure the time it takes
    ios.flash(True)

    start_time = time.time()
    camera.capture_file(__PATH + str(time.time()) + ".jpg")
    end_time = time.time()

    ios.flash(False)

    # Release the camera
    capture_time = end_time - start_time

    # Write the time to the csv file
    csv.write(str(capture_time) + "\n")

    return capture_time

if __name__ == "__main__":    
    # Allow the camera to adjust to lighting conditions
    camera.start()
    time.sleep(2)

    for i in range(100):
        time_taken = take_picture()
        print(f"Time taken to capture the picture: {time_taken:.2f} seconds")
        # time.sleep(1)  # Adjust the delay as needed
    
    camera.close()

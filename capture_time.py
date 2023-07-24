import cv2
import time
import IOs as ios

__PATH = "./captureTimeTest/"
__TIME_CSV = "./captureTimeTest/captureTime.csv"

# Create a VideoCapture object to access the USB camera
camera = cv2.VideoCapture(0)

csv = open(__TIME_CSV, "w")

def take_picture():
    # Capture the image and measure the time it takes
    ios.flash(True)

    start_time = time.time()
    ret, image = camera.read()
    end_time = time.time()

    ios.flash(False)

    # Release the camera

    if not ret:
        raise Exception("Failed to capture the image from the camera.")

    # Save the image in the path with time stamp name
    cv2.imwrite(__PATH + str(time.time()) + ".jpg", image)

    capture_time = end_time - start_time

    # Write the time to the csv file
    csv.write(str(capture_time) + "\n")

    return capture_time

if __name__ == "__main__":
    # take the same test for a 100 times
    if not camera.isOpened():
        raise Exception("Failed to open the camera. Make sure it is connected and recognized.")
    

    # Allow the camera to adjust to lighting conditions
    time.sleep(2)

    for i in range(100):
        time_taken = take_picture()
        print(f"Time taken to capture the picture: {time_taken:.2f} seconds")
        # time.sleep(1)  # Adjust the delay as needed
    
    camera.release()

import cv2
import numpy as np
import time
import math
import requests
import json


cap = cv2.VideoCapture(0)



__URL__ = 'http://example.com/api/data'

__RATIO__ = 16/9
__CAMERA_WIDTH__ = 550
__CAMERA_HEIGTH__ = math.floor(__CAMERA_WIDTH__/__RATIO__)
__FRAMESIZE__ = (__CAMERA_WIDTH__, __CAMERA_HEIGTH__)
__MAIN_PATH__ ="./muestras/opencv_frame_" # path to save images

last_frame = None
captured_data = None
frameReadyCallback = None

zoi_x1 = 150
zoi_y1 = 40
zoi_x2 = 1000
zoi_y2 = 469
captured = False
# pause_image = False
ZOI_start = [zoi_x1, zoi_y1]
ZOI_end = [zoi_x2, zoi_y2]
Z1 = 40  # Size of the tail we want
lytho = 1.2  # user threshold
img_counter = 0

def handle_capture(callback):
    global captured, frameReadyCallback
    print("capture")
    captured = True
    frameReadyCallback = callback

def getAnalyzedImage():
    return last_frame
    
def get_analysis_data():
    global captured_data
    return captured_data

def handle_reset():
    global captured, captured_data
    captured = False
    # pause_image = False
    captured_data = None
    print("reset")

def updateImage():
    global captured, img_counter, cap, last_frame, x1, captured_data, frameReadyCallback
    ret, frame = cap.read()
    #  cap.release()
    # if captured and not pause_image:
    if captured:
        img_name = __MAIN_PATH__+"{}.png".format(img_counter)
        cv2.imwrite(img_name, frame)
        print("{} written!".format(img_name))
        # im = cv2.imread( __MAIN_PATH__+ str(img_counter) + ".png")
        im = frame
        img_counter += 1

        img = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(img, (13, 13), 0)
        ret3, th3 = cv2.threshold(blur, 0, 1, cv2.THRESH_OTSU)  # cv.THRESH_BINARY
        ret4, BW = cv2.threshold(blur, ret3 * lytho, 1, cv2.THRESH_BINARY)

        # Task 1b : Determine when to start ZOI
        # 1st one for fish with head
        diameter_full_image = []
        for j in range(BW.shape[1]):  # shape[0] = on the height (y-axis) and shape[1] on the width (x-axis)
            d = np.sum(1 - BW[:, j])  # sum all the '0' pixel on the Y (ROIBW[x,y])
            diameter_full_image.append(d) # the tab diameter have all the diameter of the fish for each x0...xn
        Df = np.max(diameter_full_image) # search what is the max on the tab diameter

            # 2nd one for fish without head with a block
        Dfindex = diameter_full_image.index(Df)
        for j in range(Dfindex,len(diameter_full_image)-Dfindex): # We start from the biggest black line until the end of thet tab
            if diameter_full_image[j] < Df: # Once we have something less than the biggest one it means that it's finished
                break
        zoi = j

        ###Task 2 : Region of Interest (ROI)
        y1 = 60
        x2 = 1000
        if zoi > x2:
            x1 = 50
        else:
            x1 = zoi+4
        y2 = 500
        ROIBW = BW[y1:y2, x1:x2]  # source_image[ start_row : end_row, start_col : end_col] row = y, column = x
        cv2.rectangle(im, (x1, y1), (x2, y2), (0, 255, 0), 1)
        cv2.putText(im,"Zone Of Interest",(x2-150, y2+30),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,200,0),1)

        ###Task 3 : Size of the fish from ROI to tail
        diameter = []
        for j in range(ROIBW.shape[1]):  # shape[0] = on the height (y-axis) and shape[1] on the width (x-axis)
            w = np.sum(1 - ROIBW[:, j])  # sum all the '0' pixel on the Y (ROIBW[x,y])
            diameter.append(w) # the tab diameter have all the diameter of the fish for each x0...xn

            if w <= Z1: # stop the loop when the size of the diameter of the tail is reached
                break
        X1 = j
        print('X1 is: ' + str(X1))

        cv2.line(im,(X1+x1, y1),(X1+x1, y2),(255,0,0),1)
        cv2.arrowedLine(im,(x1, y1+20),(X1+x1, y1+20),(0,0,255),2,1,0,0.03)
        cv2.arrowedLine(im,(X1+x1, y1+20),(x1, y1+20),(0,0,255),2,1,0,0.03)
        cv2.putText(im,"X1 : " +str(X1),(X1+x1+20, y1+30),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)

        ####Task 4 : Surface of the fish
        S1 = np.sum(np.sum(1 - ROIBW[:, 1:X1]))
        print('Black area is: ' + str(S1))

        ###Task 5 : Biggest diameter of the fish
        D1 = np.max(diameter) # search what is the max on the tab diameter
        D1index = diameter.index(D1)
        c = (1 - ROIBW[:, D1index])  # c is all the points on y-axis at the D1index point on the x-axis

        for i in range(len(c)):
            if c[i] == 1:
                cv2.circle(im, (x1 + D1index, i+y1), 1, (200, 0, 255), 1) # we add circle each time there is a 1 so we can display the diameter

        print('D1 is: ' + str(D1))

        cv2.putText(im,"D1 : " +str(D1),(D1index+x1+20, y1+250),cv2.FONT_HERSHEY_SIMPLEX,1,(200,0,255),3)

        ###Task 6 : Size of the head
        for j in range(BW.shape[1]):
            w2 = np.sum(1 - BW[:, j])
            if w2 > 2:
                break
        X2 = j - x1
        print('X2 is: ' + str(X2))

        cv2.line(im,(X2+x1, y1),(X2+x1, y2),(255,0,0),1)
        cv2.arrowedLine(im,(x1, y2),(X2+x1, y2),(0,0,255),2,1,0,0.04)
        cv2.arrowedLine(im,(X2+x1, y2),(x1, y2),(0,0,255),2,1,0,0.04)
        # cv2.putText(im,"X2 : " +str(abs(X2)),(X2+x1+20, y2+40),cv2.FONT_HERSHEY_SIMPLEX,1,(0,0,255),3)
        # self.updateImage(im)
        last_frame = im
        if captured_data == None:
            captured_data = '{ "length": '+str(X1)+', "height": '+str(D1)+', "head": '+str(X2)+', "tail_trigger": '+str(Z1)+' }'
        
        captured = False
        frameReadyCallback()
        # return im 
        return frame
        
    elif not captured:
        # self.updateImage(frame)
        return frame
    
    # else:
    #     # self.updateImage(last_frame)
    #     return last_frame
import cv2
import numpy as np
import time
from simple_pid import PID
from config import *

cap = cv2.VideoCapture(0)
algo = cv2.bgsegm.createBackgroundSubtractorMOG()

pid = PID(5,3,3,setpoint=Setpoint)
pid.output_limits = (200, 1000)
pid.set_auto_mode(True, last_output=500)

def center_handle(x, y, w, h):  # determine center of the rectangle
    x1 = int(w / 2)
    y1 = int(h / 2)
    cx = x + x1
    cy = y + y1
    return cx, cy

def moy(tab):
    global somme
    somme = 0
    for i in range (len(tab)):
        somme = somme + tab[i]
    return (somme/len(tab))

def drawing(frame, frame1):
    cv2.line(frame1, (1, count_line_position), (1500, count_line_position), (255, 127, 0),
             3)  # draw the line (without fish)
    cv2.line(frame1, (1, count_line_position - offset1), (1500, count_line_position - offset1), (255, 0, 255),
             3)  # draw the line (without fish)
    cv2.line(frame1, (1, count_line_position + offset2), (1500, count_line_position + offset2), (255, 255, 0),
             3)  # draw the line (without fish)
    cv2.rectangle(frame,(zoi_x1,zoi_y1),(zoi_x2,zoi_y2),(0,255,0),1) # Draw ZOI
    cv2.putText(frame, "Nb Fish : " + str(counter), (1050, 40+20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(frame, "FPM : " + str(round(fpm,2)), (1050, 80+20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(frame, "Motor Speed : " +str(round(motorpid,2)), (1050, 120+20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
    cv2.putText(frame, "FPM Target : " + str(Setpoint), (1050, 160+20), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

def img_processing(frame1):
    grey = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)  # create a B&W image
    blur = cv2.GaussianBlur(grey, (5, 5), 0)  # 9,9,12 # Create a Gaussian Blur
    img_sub = algo.apply(blur)  # Apply blur
    dilat = cv2.dilate(img_sub, np.ones((1, 1)))  # round the edges
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))  # create more rectangle shape
    dilatada = cv2.morphologyEx(dilat, cv2.MORPH_CLOSE, kernel)  # apply dilatation and morphology
    _,counterShape, h = cv2.findContours(dilatada, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)  # make a net image
    return counterShape, grey, dilat, dilatada

def reset_cond(timecond): # if the elapsed time is more than timecond >> everything is reset
    global bufreset, stop, resetime, buf2, fpm, motorpid, motor
    resetime = time.time()-stop
    if resetime > timecond:
        for i in range (len(buf2)):
            buf2.pop()
        # print("BUF2 RESET !!! ")
        fpm = 0
        bufreset = 0
        motorpid = 0
        motor = 0

def fpm_avg():
    global bufreset, avg, timepassed, fpm, buf1, buf2, stop
    bufreset += 1 
    stop = time.time()
    buf1.insert(0,time.time())

    if bufreset > 2: # to be sure that we have more than 2 value
        buf1.pop() # pop the last value
        timepassed = buf1[0] - buf1[1] # put in a variable the elapsed time
        buf2.insert(0, timepassed) # put in second tab all the elapsed time
        avg = moy(buf2) # make the average of all elapsed time
        fpm = 60 / avg # calculate fpm
    if bufreset > 10: # wait that the size of the buf2 reach 10 so the size of the buffer can vary
        buf2.pop()

def counting():
    global counter, motorpid

    ret, frame = cap.read()  # read the image
    frame = cv2.resize(frame, (1440, 900))
    frame1 = frame[zoi_y1:zoi_y2, zoi_x1:zoi_x2]

    drawing(frame, frame1)
    img_processing(frame1)
    counterShape, grey, dilat, dilatada = img_processing(frame1)

    ########## Optional ##############
    # treated_img = cv2.cvtColor(dilat, cv2.COLOR_GRAY2RGB) # Put back treated image on original image
    # frame[zoi_y1:zoi_y2, zoi_x1:zoi_x2] = treated_img
    ##################################

    for (i, c) in enumerate(counterShape):
        (x, y, w, h) = cv2.boundingRect(c)
        validate_counter = (w >= min_width_rect) and (h >= min_height_rect)
        if not validate_counter:
            continue
        cv2.rectangle(frame1, (x, y), (x + w, y + h), (0, 0, 255), 2) # Rectangle for each fish detected
        center = center_handle(x, y, w, h) # put the center of the rectangle
        detect.append(center)
        cv2.circle(frame1, center, 4, (0, 0, 255), -1) # small point on the center of the fish

    
    reset_cond(time_before_reset) # if 10 seconds passed reset all buffers and fpm

    for (x, y) in detect:
        if y > (count_line_position - offset1) and y < (count_line_position + offset2):
            counter += 1

            fpm_avg() # see function

            cv2.line(frame1, (1, count_line_position), (1500, count_line_position), (255, 190, 0),3)  # draw the line with fish
            detect.remove((x, y))

    motorpid = pid(fpm)
    
    
    return frame
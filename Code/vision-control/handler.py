from datetime import datetime
import numpy as np
import handdetector as htm
import time
import cv2
import serial

ser = serial.Serial("/dev/ttyS0", baudrate = 9600, parity=serial.PARITY_NONE,
stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)

wCam, hCam = 320, 240 # hatam webcam resuloution
frameR = 50
smoothening = 7

pTime = 0
plocX, plocY = 0, 0
clocX, clocY = 0, 0
mouseDown = False
clicked = False
rclicked = False
dclicked = False
last_pos_scroll = -1

last_ss = time.time_ns()

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
detector = htm.HandDetector(max_hands=1)

while True:
    # 1. Find hand Landmarks
    fingers=[0,0,0,0,0]
    success, img = cap.read()
    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img)
    # 2. Get the tip of the index and middle fingers
    if len(lmList) != 0:
        ser.write(b"b*%d*%d*%d*%d\n"%(bbox[0],bbox[1],bbox[2],bbox[3]))
        x1, y1 = lmList[8][1:3]
        x2, y2 = lmList[12][1:3]
        # print(x1, y1, x2, y2)

    # 3. Check which fingers are up
        fingers = detector.fingersUp()

    # 4. Only Index Finger : Moving Mode
    if fingers[1] == 1 and fingers[2] == 0:
        # 7. Move Mouse
        ser.write (b"v*%d*%d\n"%(x1,y1))

    # 8. Both Index and middle fingers are up : Clicking Mode
    if fingers == [0,1,1,0,0]:
        print('dclick-mode')
        # 9. Find distance between fingers
        length, img, lineInfo = detector.findDistance(8, 12, img)
        # 10. Click mouse if distance short
        if length < 15:
            if not dclicked:
                ser.write(b"d\n")
                dclicked = True
        else:
            dclicked = False

    # single click mode
    if fingers == [0,1,1,1,0]:
        length, img, lineinfo = detector.findDistance(8, 12, img)
        if length < 15:
            if not clicked:
                ser.write(b"c\n")
                clicked=True
        else:
            clicked = False

    if fingers == [1,1,0,0,0]:
        length, img, lineInfo = detector.findDistance(4, 8, img)
        # 10. pinch
        if length < 15 and not mouseDown:
            ser.write(b"md\n")
            mouseDown = True

        if length > 15 and mouseDown:
            ser.write(b"mu\n")
            mouseDown = False

    if fingers == [1,1,1,0,0]:
        # Right click mode
        length, img, lineInfo = detector.findDistance(8, 12, img)
        # 10. Click mouse if distance short
        if length < 15:
            if not rclicked:
                ser.write(b"r\n")
                rclicked = True
        else:
            rclicked = False

    if fingers == [0,1,1,1,1]:
        # scroll mode
        pos = y1
        if last_pos_scroll == -1:
            last_pos_scroll = pos
        else:
            if abs(last_pos_scroll - pos) > 10:
                clicks = int((last_pos_scroll - pos))
                ser.write (b"s*%d\n"%(clicks))
                last_pos_scroll = pos
    else:
        last_pos_scroll = -1

    if fingers == [1,0,0,0,1]:
        if time.time_ns() - last_ss > 1_000_000_000:
            last_ss = time.time_ns()
            ser.write (b"p\n")

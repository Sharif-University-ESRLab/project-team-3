from datetime import datetime
import numpy as np
import handdetector as htm
import time
import pyautogui
import cv2

 
wCam, hCam = 640, 480 # hatam webcam resuloution
frameR = 120
smoothening = 7

pyautogui.PAUSE = 0.02
 
pTime = 0
plocX, plocY = 0, 0
clocX, clocY = 0, 0
mouseDown = False
clicked = False
rclicked = False
last_pos_scroll = -1

last_ss = time.time_ns()
 
cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
detector = htm.HandDetector(max_hands=1)
wScr, hScr = pyautogui.size()
print(wScr, hScr)
 
while True:
    # 1. Find hand Landmarks
    fingers=[0,0,0,0,0]
    success, img = cap.read()
    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img)
    # 2. Get the tip of the index and middle fingers
    if len(lmList) != 0:
        x1, y1 = lmList[8][1:3]
        x2, y2 = lmList[12][1:3]
        # print(x1, y1, x2, y2)
    
    # 3. Check which fingers are up
        fingers = detector.fingersUp()
    # print(fingers)
    cv2.rectangle(img, (frameR, frameR), (wCam - frameR, hCam - frameR),
    (255, 0, 255), 2)
    # 4. Only Index Finger : Moving Mode
    if fingers[1] == 1 and fingers[2] == 0:
        # 5. Convert Coordinates
        x3 = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
        y3 = np.interp(y1, (frameR, hCam - frameR), (0, hScr))
        # 6. Smoothen Values
        clocX = plocX + (x3 - plocX) / smoothening
        clocY = plocY + (y3 - plocY) / smoothening
    
        # 7. Move Mouse
        pyautogui.moveTo(wScr - clocX, clocY)
        cv2.circle(img, (x1, y1), 15, (255, 0, 255), cv2.FILLED)
        plocX, plocY = clocX, clocY
        
    # 8. Both Index and middle fingers are up : Clicking Mode
    if fingers == [0,1,1,0,0]:
        # 9. Find distance between fingers
        length, img, lineInfo = detector.findDistance(8, 12, img)
        print(length)
        # 10. Click mouse if distance short
        if length < 30:
            cv2.circle(img, (lineInfo[4], lineInfo[5]),
            15, (0, 255, 0), cv2.FILLED)
            if not clicked:
                pyautogui.click()
                clicked = True
        else:
            clicked = False
    
    if fingers == [1,1,0,0,0]:
        length, img, lineInfo = detector.findDistance(4, 8, img)
        print(length)
        # 10. pinch
        if length < 30 and not mouseDown:
            cv2.circle(img, (lineInfo[4], lineInfo[5]),
            15, (255, 0, 0), cv2.FILLED)
            pyautogui.mouseDown()
            mouseDown = True

        if length > 35 and mouseDown:
            pyautogui.mouseUp()
            mouseDown = False

    if fingers == [1,1,1,0,0]:
        # Right click mode
        length, img, lineInfo = detector.findDistance(8, 12, img)
        print(length)
        # 10. Click mouse if distance short
        if length < 30:
            cv2.circle(img, (lineInfo[4], lineInfo[5]),
            15, (0, 0, 255), cv2.FILLED)
            if not rclicked:
                pyautogui.rightClick()
                rclicked = True
        else:
            rclicked = False
        
    if fingers == [0,1,1,1,0]:
        # scroll mode
        pos = np.interp(y1, (frameR, hCam - frameR), (0, hScr))
        if last_pos_scroll == -1:
            last_pos_scroll = pos
        else:
            if abs(last_pos_scroll - pos) > 10:
                clicks = int((last_pos_scroll - pos))
                print(clicks)
                pyautogui.scroll(-clicks)
                last_pos_scroll = pos
    else:
        last_pos_scroll = -1

    if fingers == [1,0,0,0,1]:
        if time.time_ns() - last_ss > 1_000_000_000:
            last_ss = time.time_ns()
            pyautogui.press("prtsc")

    # 11. Frame Rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, str(int(fps)), (20, 50), cv2.FONT_HERSHEY_PLAIN, 3,
    (255, 0, 0), 3)
    # 12. Display
    cv2.imshow("Image", cv2.flip(img, 1))
    cv2.waitKey(1)
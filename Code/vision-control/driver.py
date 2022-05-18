# wScr, hScr (screen size)
# given x1, y1 
# commands: move, click, rclick, scroll, move up(), print_screen 
# 


import pyautogui
import numpy as np
import socket
import threading
import time

plocX, plocY = 0, 0
clocX, clocY = 0, 0
wCam, hCam = 640, 480  # hatam webcam resuloution
wScr, hScr = pyautogui.size()
frameR = 120
smoothening = 7

pyautogui.PAUSE = 0.02

receive_buffer = ''

host = '127.0.0.1'
port = 8550

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
print('waiting')
server.listen(1)
client, address = server.accept()
print('connected')


while True:
    # print('receive_buffer: ', receive_buffer)
    ### command format : command_name*arg1*arg2*arg3*...
    
    command_string = client.recv(1024).decode('ascii')
    # print('command_string: ', command_string)

    command_arr = command_string.split('*')
    if 'move' == command_arr[0]:
        # print(command_arr)
        x1 = float(command_arr[1])
        y1 = float(command_arr[2])

        x3 = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
        y3 = np.interp(y1, (frameR, hCam - frameR), (0, hScr))

        clocX = plocX + (x3 - plocX) / smoothening
        clocY = plocY + (y3 - plocY) / smoothening
        pyautogui.moveTo(wScr - clocX, clocY)
        plocX, plocY = clocX, clocY

    elif 'click' == command_arr[0]:
        pyautogui.click()
    elif 'rclick' == command_arr[0]:
        pyautogui.rightClick()
    elif 'scroll' == command_arr[0]:
        x = int(command_arr[1])
        pyautogui.scroll(-1 * x)
    elif 'mouseUp' == command_arr[0]:
        pyautogui.mouseUp()
    elif 'mouseDown' == command_arr[0]:
        pyautogui.mouseDown()
    elif 'print_screen' == command_arr[0]:
        pyautogui.press("prtsc")


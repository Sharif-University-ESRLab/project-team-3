from asyncio.log import logger
import pyautogui
import numpy as np
import time
import serial
import serial.tools.list_ports as lp
from tkinter import Canvas, messagebox as mb
import re
import tkinter as tk
from threading import Thread
import signal
from serial.serialutil import SerialException
import setproctitle
import os

# change process name so it can be distinguished in the task manager
setproctitle.setproctitle('Motion Capture Driver')

wCam, hCam = 320, 240 
wScr, hScr = pyautogui.size()
# middle of the screen for smoother experience
plocX, plocY = wScr//2, hScr//2
clocX, clocY = 0,0
frameR = 50
smoothening = 7

pyautogui.PAUSE = 0.02

# patterns send from RPi
patterns = [
    "^(b)[*]([-]?\d+)[*]([-]?\d+)[*]([-]?\d+)[*]([-]?\d+)$", # box
    "^(v)[*]([-]?\d+)[*]([-]?\d+)$",                         # move
    "^(d)$",                                                 # double click
    "^(md)$",                                                # mouse down
    "^(mu)$",                                                # mouse up
    "^(c)$",                                                 # single click
    "^(r)$",                                                 # right click
    "^(s)[*]([-]?\d+)$",                                     # scroll
    "^(p)$"                                                    # print screen
]

def do_b(params):
    # draw the box boundary of the hand which is taken by the camera
    coords = list(map(int, params))
    assert len(coords) == 4
    global visualizer
    visualizer.canvas.delete(visualizer.hand_rect)
    # coords = x1,y1 x2, y2
    visualizer.hand_rect = visualizer.canvas.create_rectangle(
        320 - coords[0],
        coords[1],
        320 - coords[2],
        coords[3]
    )

def do_md(_):
    # pinch - Mouse Down - for drag and drop
    pyautogui.mouseDown()


def do_mu(_):
    # pinch - Mouse Up
    pyautogui.mouseUp()


def do_v(params):
    # moVe the cursor. 
    global plocX, plocY, clocX, clocY
    
    # move the pointer to the position
    # interpolate camera dimentions to the screen
    x1, y1 = map(int, params)
    x3 = np.interp(x1, (frameR, wCam - frameR), (0, wScr))
    y3 = np.interp(y1, (frameR, hCam - frameR), (0, hScr))
    
    # Smoothen Values
    # move the cursor without glitching
    clocX = plocX + (x3 - plocX) / smoothening
    clocY = plocY + (y3 - plocY) / smoothening

    # Move Mouse
    pyautogui.moveTo(wScr - clocX, clocY)

    # visualize the move
    global visualizer
    visualizer.canvas.delete(visualizer.pointer)
    visualizer.pointer = create_circle(320 - x1, y1, 3, visualizer.canvas, fill='blue')
    plocX, plocY = clocX, clocY


def do_d(_):
    # double clicks
    pyautogui.doubleClick()


def do_c(_):
    # click
    pyautogui.click()


def do_r(_):
    # right click
    print(pyautogui.rightClick())


def do_s(params):
    # scroll in the opposite direction
    pyautogui.scroll(-int(params[0])*10)


def do_p(_):
    # take print screen
    mb.showinfo("Screen Shot", "Screenshot is available in your clipboard")
    pyautogui.press("prtsc")


def get_serial_line() -> str:
    try:
        global ser
        if ser.isOpen():
            # if the serial port is open
            try:
                # read a line from it
                cm = str(ser.readline(), 'utf-8')
                logger.log(0, cm)
                print(cm)
                return cm.strip()
            except:
                return None
        else:
            # else port is closed. reset ports
            global visualizer
            visualizer.reset_ports()
            return None
    except NameError:
        # serial connection is not defined
        return None

def get_command():
    # wait till a new command is received
    command = get_serial_line()
    if command:
        for pattern in patterns:
            # search in the patterns if the command exists or not
            x = re.search(pattern, command)
            if x:
                # seperate command and its parameters
                x = list(x.groups())
                return x[0], x[1:]
        return None, None
    else:
        # sleep to prevent busy waiting until a serial is connected
        time.sleep(0.5)
        return None, None


def interpret(command: str, params: list):
    # finds corresponding handler of the command and do the command
    globals()["do_"+command](params)


def create_circle(x, y, r, canvasName: tk.Canvas, **kwargs): 
    #center coordinates, radius
    #easier way to create circle in tkinter
    x0 = x - r
    y0 = y - r
    x1 = x + r
    y1 = y + r
    return canvasName.create_oval(x0, y0, x1, y1, **kwargs)


class Visualizer(Thread):
    def run(self) -> None:
        setproctitle.setproctitle('Motion Capture Driver')
        
        root = tk.Tk()
        self.root = root

        # create pane and move to upper-right corner
        w = wCam + 20
        h = hCam + 40
        root.geometry(f"{w}x{h}+{wScr-w-40}+{50}")

        # set minimum window size value
        root.minsize(w + 10, h + 20)

        # set maximum window size value
        root.maxsize(w + 10, h + 20)

        # no titlebar
        root.overrideredirect(True)

        # transparent
        root.attributes('-alpha',0.7)

        # always on top
        root.attributes('-topmost', True)

        # bind moving
        root.bind("<B1-Motion>", dragging)
        root.bind("<Button-1>", save_last_click_pos)

        # add com port selector
        port = tk.StringVar(root)
        port.set("None")
        self.port = port
        
        w = tk.OptionMenu(root, port, ["None"])
        self.port_list = w

        # on open update the port lists
        w.bind("<Button-1>", self.update_ports)
        w.pack()

        # context menu on exit
        m = tk.Menu(root, tearoff=0)
        m.add_command(label="Exit", command=lambda: os._exit(0))
        
        def do_popup(event):
            try:
                m.tk_popup(event.x_root, event.y_root)
            finally:
                m.grab_release()
        
        root.bind('<Button-3>', do_popup)
        
        # Canvas for visualization
        self.canvas = tk.Canvas(root, height= 240 + 20, width= 320 + 20 )
        self.canvas.create_rectangle(10,10,10+320,240 + 10, outline='red')
        self.hand_rect = self.canvas.create_rectangle(10,10,11,11)
        self.pointer = create_circle(10,10,3, self.canvas, fill='blue')
        self.canvas.pack()
        # Execute tkinter
        root.mainloop()
    
    def update_ports(self, e:tk.Event):
        # update serial port list
        ports = [port.name for port in lp.comports()]
        ports.insert(0, "None")
        menu = self.port_list["menu"]
        menu.delete(0, "end")
        for port in ports:
            menu.add_command(label=port, command= lambda value=port: self.handle_port_change(value))

    def handle_port_change(self, new_port):
        if new_port != "None":
            try:
                global ser
                ser = serial.Serial(new_port, baudrate = 9600, parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
                if ser.isOpen():
                    mb.showinfo("Serial Connected", "Serial Connected Successfully")
                    self.port.set(new_port)
                    return
                    
            except SerialException as _:
                # Permission Error - Busy Port
                mb.showerror("Permission Error", "Port is busy and/or your user does not access to the port.")
            
            except Exception as _:
                mb.showerror("Error", "An unknown error happened. Please report the bug to a.hatam@sharif.edu.")
        
        self.reset_ports()
    
    def reset_ports(self):
        try:
            global ser
            if ser:
                ser.close()
        except:
            pass
        self.port.set("None")
        menu = self.port_list["menu"]
        menu.delete(0, "end")
        menu.add_command(label="None", command= lambda x: self.port.set("None"))


lastClickX = 0
lastClickY = 0

def save_last_click_pos(event:tk.Event):
    global lastClickX, lastClickY
    lastClickX = event.x
    lastClickY = event.y


def dragging(event:tk.Event):
    global visualizer
    root = visualizer.root
    x, y = event.x - lastClickX + root.winfo_x(), event.y - lastClickY + root.winfo_y()
    root.geometry("+%s+%s"%(x , y))


def sigint_handler(sig, frame):
    # debugging purpose
    # exit the application on exit
    global visualizer
    visualizer.root.quit()
    visualizer.root.update()


def start():
    global visualizer
    visualizer = Visualizer()
    visualizer.start()
    while True:
        try:
            # get command from serial
            command, params = get_command()
            if command:
                # interprate command
                interpret(command, params)
        except Exception as e:
            # log bad habits
            logger.log(3, str(e))


if __name__ == "__main__":
    """
    main script is here
    """
    signal.signal(signal.SIGINT, sigint_handler)
    start()

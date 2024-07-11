# This GUI allows a user to control the DeepSee Sampler System with button presses
#DeepSEE GUI3 (firmware v0.95) + threading, logging, graphing

from posixpath import split
import tkinter as tk
from tkinter import Frame, ttk
import tkinter
from tkinter import *
from pyparsing import col
import serial
import time
import threading
import queue
import csv
import numpy as np
import matplotlib.pyplot as plt
from numpy import genfromtxt

#VARIABLES
#File paths for logs (if these are left as file names, they will appear in the current working dir.)
volumes_feed = "volumes_feed_A.csv" #only vols from the HBs
command_hist = "command_hist_testing.csv" #all commands sent + ACKs from sampler. May include some serial line errors from startup.
sampler_feed = "sampler_Feed_testing.csv" #everything received from sampler (HB's and ACK's)

#Serial port
com_port = 'COM43'
#LOGGING
def log(data, log_path):
    with open(log_path, 'a', newline='') as f:
        writer = csv.writer(f)
        # write the data
        now = int(time.time()) #if you need millisecond precsision, cast as int
        data.insert(0, now)
        writer.writerow(data)

#SERIAL SETUP
ser = serial.Serial(com_port, 38400, timeout=5) # make sure the 'COM#' is correct by checking which USB port your sampeler is connected to
time.sleep(1)

class SerialThread(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self.queue = queue
    def run(self):
        time.sleep(0.2)
        while True:
            if ser.inWaiting():
                text = ser.readline() #read from serial
                self.queue.put(text) #put the serial content in the queue

#GRAPHING
def graph():
    #grab data
    my_data = genfromtxt(volumes_feed, delimiter=',')
    my_data = my_data[:, 1:] #exclude column with time

    #generate figure
    fig, ax = plt.subplots()
    ax.plot(my_data)

    #set axis labels
    ax.set(xlabel='time (s)', ylabel='volume (cL)',
        title='Sampler Status')
    ax.grid()

    #generate plot
    plt.show()

# TKINTER CLASSES
# Pumps
class PumpFrame(ttk.Frame):
    def __init__(self, container, pumpInd):
        super().__init__(container)

        # Initialize frame
        self.columnconfigure(0, weight=1)

        #font size
        font_size = 12;

        #creating variables from inputs
        self.pumpInd = pumpInd
        self.onCmd = b"MP Start_Pump " + str(self.pumpInd).encode() + b"\r"
        self.offCmd = b"MP Stop_Pump " + str(self.pumpInd).encode() + b"\r"

        # Frame Label
        self.label = ttk.Label(self, text='Pump '+ self.pumpInd, font=("Arial", font_size))
        self.label.grid(row=0, column=0)

        # State Label
        self.statLabel1 = tkinter.Label(self, text = "State:", font=("Arial", font_size))
        self.statLabel1.grid(row=0, column=4, sticky=S)

        self.varLabel1 = tkinter.IntVar()
        self.varLabel1.set("Off") #initialize as pump off
        self.tkLabel1 = tkinter.Label(self, textvariable=self.varLabel1, font=("Arial", font_size)) #state
        self.tkLabel1.grid(row=0,column=5, sticky=S)
        
        # volume Label
        self.statLabel2 = tkinter.Label(self, text = "Volume:", font=("Arial", font_size))
        self.statLabel2.grid(row=1, column=4)

        self.varLabel2 = tkinter.IntVar()
        self.tkLabel2 = tkinter.Label(self, textvariable=self.varLabel2, font=("Arial", font_size)) #Volume
        self.tkLabel2.grid(row=1, column=5)

        # Start button command
        def start_pump():
            self.varLabel1.set("On")
            ser.write(self.onCmd)
            print("Pump " + pumpInd + " is on")
            log(["Pump " + pumpInd + " is on"], command_hist)

        # stop button command
        def stop_pump():
            self.varLabel1.set("Off")
            ser.write(self.offCmd)
            print("Pump " + pumpInd + " is off")
            log(["Pump " + pumpInd + " is off"], command_hist)

        # Start Button Definition
        self.button1 = tkinter.IntVar()
        self.button1_state=tkinter.Button(
                                        self, 
                                        text="Start", 
                                        command=start_pump, 
                                        background= "green", 
                                        borderwidth=3,
                                        height=3,
                                        width=5,
                                        font=("Arial", font_size))
        self.button1_state.grid(row=1,column=0)

        # Stop Button Definition
        self.button2 = tkinter.IntVar()
        self.button2_state=tkinter.Button(
                                        self,
                                        text="Stop", 
                                        command=stop_pump, 
                                        background= "red", 
                                        borderwidth=3,
                                        height = 3,
                                        width = 5,
                                        font=("Arial", font_size))
        self.button2_state.grid(row=1,column=1) #stop button

# buttons not in the pump class
class OtherButtons(ttk.Frame):
    def __init__(self, container):
        super().__init__(container)

        # Initialize frame
        self.columnconfigure(0, weight=1)

        # ping sampler
        def ping():
            ser.write(b"MP Wake\r") 
            print("MP Wake")
            log(["MP Wake"], command_hist)

        pingSampler = tkinter.IntVar()
        pingSampler_state=tkinter.Button(self, text="Wake", command=ping, borderwidth=6)
        pingSampler_state.grid(row=0,column=1)

        # lights off
        def lights_off():
            ser.write(b"MP Lights_Off\r")
            print("Lights Off")
            log(["MP Lights_Off"], command_hist)

        lightsOff = tkinter.IntVar()
        lightsOff_state=tkinter.Button(self, text="Lights Off", command=lights_off, borderwidth=6)
        lightsOff_state.grid(row=0,column=2)        
        
        # Create stop all pumps
        def stop_all():
            ser.write(b"MP Stop_All_Pumps\r")
            print("Stop all pumps")
            log(["MP Stop_All_Pumps"], command_hist)

        stopAll = tkinter.IntVar()
        stopAll_state=tkinter.Button(self, text="Stop All", command=stop_all, borderwidth=6)
        stopAll_state.grid(row=0,column=4)

        # graph it
        my_button = Button(self, text="Graph it!", command=graph, borderwidth=6)
        my_button.grid(row=0, column=6)

        # Calibrate pumps
        def calibrate():
            ser.write(b"MP Cal_Pump_All to 0.33\r") 
            print("Calibrate Pumps")
            log(["MP Cal_Pump_All to 0.33"], command_hist)

        calibrateSampler = tkinter.IntVar()
        calibrateSampler_state=tkinter.Button(self, text="Calibrate", command=calibrate, borderwidth=6)
        calibrateSampler_state.grid(row=0,column=7)

        # Begin Test
        def begin_test():
            ser.write(b"MP __Begin_Test for 10 S\r") 
            print("Test Pumps")
            log(["MP __Begin_Test for 10 S"], command_hist)

        calibrateSampler = tkinter.IntVar()
        calibrateSampler_state=tkinter.Button(self, text="Begin Test", command=begin_test, borderwidth=6)
        calibrateSampler_state.grid(row=0,column=8)
        
        # End Test
        def end_test():
            ser.write(b"MP __End_Test\r") 
            print("Test Pumps")
            log(["MP __End_Test"], command_hist)

        calibrateSampler = tkinter.IntVar()
        calibrateSampler_state=tkinter.Button(self, text="End Test", command=end_test, borderwidth=6)
        calibrateSampler_state.grid(row=0,column=9)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # configure the root window
        self.title('Deep Sea Sampler GUI')
        self.geometry('1000x600')
        for l in range(0,25):
            self.columnconfigure(l, weight=1)
            self.rowconfigure(l, weight=1)

        # Threading code
        self.queue = queue.Queue()
        thread = SerialThread(self.queue)
        thread.start()
        self.process_serial()

    def process_serial(self):
        # value=True
        while self.queue.qsize():
            try:
                new=self.queue.get()

                # #print to GUI
                # if value:
                #  OtherButtons.text.delete(1.0, 'end')
                # value=False
                # OtherButtons.text.insert('end',new)

                buffer = new.decode('UTF-8', "strict")
                
                buffer_list = [buffer[:]]
                log(buffer_list, sampler_feed) #this will log everything, including heart beats and serial comming back from sampler

                hb_chars = buffer[11:13]

                if hb_chars == "HB":
                    #Extract volumes from serial message
                    splitBuffer = buffer.split("ml_Pumped")

                    volumes = splitBuffer[1].split()
                    print(volumes)
                    
                    volumes_log = volumes[:]
                    log(volumes_log, volumes_feed) #log only the volume updates
                    
                    if volumes:
                        for k in range(0,16):
                            Frames[k].varLabel2.set(volumes[k])                    
                
                else: #when this trips, it's because the serial message is something other than a heartbeat, log to command hist
                    print(buffer)
                    print(hb_chars)
                    log([buffer[:]], command_hist)

                
            except queue.Empty:
                pass
        self.after(100, self.process_serial)

# Main Loop
if __name__ == "__main__":
    app = App()
    
    # Create Frames for all pumps
    PumpInd = 0
    Frames = [0]*16

    for i in range(0,4):
        for j in range(0,4):
            Frames[PumpInd] = PumpFrame(app, str(PumpInd))
            Frames[PumpInd].grid(row=i, column=j, padx=8, pady=5)
            PumpInd += 1

    # Add buttons for Stop and Power Down
    big_buttons = OtherButtons(app)
    big_buttons.grid(row=25, column = 0, columnspan=3, sticky=W)       

    # Continuously check the heartbeat updates for pump volumes
    while True:
        app.update_idletasks()
        app.update()
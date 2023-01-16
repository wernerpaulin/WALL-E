#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/walle.py

from evdev import InputDevice, categorize, ecodes
import subprocess
import asyncio
import threading
import datetime, time

import helper.xycurvelin as xycurvelin

'''
Global variables: public access to key map as async_read_loop() is blocking
'''
global keyMap
keyMap = dict()     

global deviceHandle
deviceHandle = None

global connectThreadHandle  
connectThreadHandle = None


SCRIPT_FILE_BT_AUTOCONNECT = "~/wall-e/helper/bt_autoconnect"
GAMEPAD_DEVICE_PATH = "/dev/input/event1"


def connect():
    global connectThreadHandle 
    
    #start thread for handling key events
    try:
        if (connectThreadHandle.isAlive() == False):        #avoid starting thread multiple times
            connectThreadHandle = threading.Thread(target=connectThread)
            connectThreadHandle.start()
    except Exception as e:
        print("Starting connect thread failed: {0}".format(e))
        

def connectThread():
    global deviceHandle
    
    #initiate connect
    subprocess.call(SCRIPT_FILE_BT_AUTOCONNECT, shell=True)
    
    #wait for connection
    while True:
        try:
            deviceHandle = InputDevice(GAMEPAD_DEVICE_PATH)
            if (deviceHandle != None):
                print ("Gamepad connected: {0}".format(deviceHandle))
                break
        except Exception as e:
            pass    #ignore errors: it needs some time until the device is accessible after the connection has been established

    return    

async def processKeyEvents():
    global deviceHandle
    global keyMap
    
    if (deviceHandle == None):
        return
    
    try: 
        #evdev takes care of polling the controller in a loop
        async for event in deviceHandle.async_read_loop():
            #filters by event type
            if (event.type == ecodes.EV_KEY) or (event.type == ecodes.EV_ABS) or (event.type != ecodes.EV_SYN):
                if (event.code != 4):     #for some strange reason all push buttons cause an event with code 4 beside the corret code
                    #print("Key code <{0}> received: value <{1}>".format(event.code, event.value))
                    #build up key map
                    keyMap[str(event.code)] = int(event.value)
                    
    except Exception as e:
        print("Processing gamepad key events failed: {0}".format(e))
        #try to connect which will block this task until reconnected
        deviceHandle = None
        connect()

#initial connect
connectThreadHandle = threading.Thread(target=connectThread)
connect()


class keyInterpreter:
    global keyMap
    
    "interpretation of key for a certain command"
    #init
    def __init__(self, inMin, inMax, outMin, outMax, keyCode, selectorKeyCode, selectorKeyValue, newValueThreshold):
        self.inMin = inMin
        self.inMax = inMax
        self.outMin = outMin
        self.outMax = outMax
        self.keyCode = keyCode
        self.selectorKeyCode = selectorKeyCode
        self.selectorKeyValue = selectorKeyValue
        self.newValueThreshold = newValueThreshold
        
        self.inOutScale = xycurvelin.chartLin()
        self.scaledValue = 0
        self.oldScaledValue = None
        self.scaledValueChanged = False

        self.inOutScale.addPointPair(float(self.inMin), float(self.outMin))
        self.inOutScale.addPointPair(float(self.inMax), float(self.outMax))
        
        keyMap[keyCode] = 0
        keyMap[selectorKeyCode] = 0
        
        
    def update(self):
        keySelected = False
        
        try: 
            #do nothing if key is not in keymap
            if (self.keyCode in keyMap):
                #check if a selector is configured
                if (self.selectorKeyCode != None) and (self.selectorKeyValue != None):
                    if (self.selectorKeyCode in keyMap):
                        if (keyMap[self.selectorKeyCode] == self.selectorKeyValue):
                            keySelected = True
                        else:
                            keySelected = False
                    else:
                        #selector not yet pressed
                        keySelected = False
                        pass
                else:
                    #selector not configured: ignore it
                    keySelected = True
                    pass
                
                #evaluate key value if selected
                if (keySelected == True):
                    newScaledValue = self.inOutScale.calcYfromX(keyMap[self.keyCode])
                    #check if changed and indicate it with a flag
                    #if (self.scaledValue != self.oldScaledValue):
                    if (abs(newScaledValue - self.scaledValue) >= self.newValueThreshold):
                        self.scaledValue = newScaledValue
                        self.oldScaledValue = self.scaledValue
                        self.scaledValueChanged = True
                
            else:
                #no change
                return
            
        except Exception as e:
            print("Interpreting key <{0}> failed: {1}".format(self.keyCode, e))
            self.scaledValueChanged = False


        

        
        

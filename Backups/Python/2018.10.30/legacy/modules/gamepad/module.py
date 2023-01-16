#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.rest
import threading
import core.helper.xycurvelin

import json

from flask import request
from flask_restful import Resource

from evdev import InputDevice, categorize, ecodes
import subprocess
from pathlib import Path


MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./gamepads"
CFG_ROOT_ELEMENT_NAME = "/gamepad"


def init():
    global Gamepads
    global RestClient               #contains all REST clients which have channels to other servers 
    global WebSocketClient
    
    RestClient = dict()
    Gamepads = dict()
    attrList = [] 
    gamepadID = None

    #read module configuration and initialize each gamepad
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()

        #read configuration
        for gamepadCfg in cfgRoot.findall(CFG_ROOT_NAME + CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a switch manager for each switch found in the configuration
                gamepadID = gamepadCfg.get('id')
                Gamepads[gamepadID] = gamepadManager(gamepadID)
                
                #initialize gamepad parameters
                parameterNameList = getClassAttributes(Gamepads[gamepadID].param)      #['testValue', ...]
                #try to find the corresponding entry in the configuration file 
                for parameterName in parameterNameList:
                    #get access to input configuration: <parameter name="testValue">
                    parameterCfg = gamepadCfg.find('.//parameters/parameter[@name="' + parameterName + '"]')
                    #continue only if configuration exists
                    if (parameterCfg != None) and (parameterCfg.text != None):
                        #convert to float or leave text
                        if is_number(parameterCfg.text):          
                            setattr(Gamepads[gamepadID].param, parameterName, float(parameterCfg.text))
                        else:
                            #text can be either true, false or any arbitrary text
                            if (parameterCfg.text.lower() == "true"):
                                setattr(Gamepads[gamepadID].param, parameterName, True)
                            elif (parameterCfg.text.lower() == "false"):
                                setattr(Gamepads[gamepadID].param, parameterName, False)
                            else:
                                setattr(Gamepads[gamepadID].param, parameterName, parameterCfg.text)


                #initialize gamepad key configuration
                for keyCfg in gamepadCfg.findall('.//keys/key'):
                    keyID = keyCfg.get('id')
                    Gamepads[gamepadID].inputKeyMap[keyID] = inputKeyMap(keyID)

                    #reverse mapping to save time later in processing finding the key id to a received key code
                    Gamepads[gamepadID].inputKeyCodeToID[keyCfg.get('code')] = keyID


                #initialize action configuration
                for actionCfg in gamepadCfg.findall('.//actions/action'):
                    actionID = actionCfg.get('id')
                    Gamepads[gamepadID].keyActions[actionID] = actionParameters(actionID)
                    
                    #initialize key parameters
                    triggerKeyCfg = actionCfg.find('.//triggerKey')
                    keyParameterList = getClassAttributes(Gamepads[gamepadID].keyActions[actionID].triggerKey)      #['testValue', ...]
                    #try to find the corresponding entry in the configuration file 
                    for keyParameter in keyParameterList:
                        parameterValue = triggerKeyCfg.get(keyParameter)
                        #continue only if configuration exists
                        if (parameterValue != None):
                            #convert to float or leave text
                            if is_number(parameterValue):          
                                setattr(Gamepads[gamepadID].keyActions[actionID].triggerKey, keyParameter, float(parameterValue))
                            else:
                                #text can be either true, false or any arbitrary text
                                if (parameterValue.lower() == "true"):
                                    setattr(Gamepads[gamepadID].keyActions[actionID].triggerKey, keyParameter, True)
                                elif (parameterValue.lower() == "false"):
                                    setattr(Gamepads[gamepadID].keyActions[actionID].triggerKey, keyParameter, False)
                                else:
                                    setattr(Gamepads[gamepadID].keyActions[actionID].triggerKey, keyParameter, parameterValue)

                    #initialize scaling
                    Gamepads[gamepadID].keyActions[actionID].triggerKey.inOutScale.addPointPair(float(Gamepads[gamepadID].keyActions[actionID].triggerKey.inMin), float(Gamepads[gamepadID].keyActions[actionID].triggerKey.outMin))
                    Gamepads[gamepadID].keyActions[actionID].triggerKey.inOutScale.addPointPair(float(Gamepads[gamepadID].keyActions[actionID].triggerKey.inMax), float(Gamepads[gamepadID].keyActions[actionID].triggerKey.outMax))
                    
                    
                    #initialize REST parameters
                    restCfg = actionCfg.find('.//restCfg')
                    restParameterList = getClassAttributes(Gamepads[gamepadID].keyActions[actionID].restCfg)      #['testValue', ...]
                    #try to find the corresponding entry in the configuration file 
                    for restParameter in restParameterList:
                        parameterValue = restCfg.get(restParameter)
                        #continue only if configuration exists
                        if (parameterValue != None):
                            #convert to float or leave text
                            if is_number(parameterValue):          
                                setattr(Gamepads[gamepadID].keyActions[actionID].restCfg, restParameter, float(parameterValue))
                            else:
                                #text can be either true, false or any arbitrary text
                                if (parameterValue.lower() == "true"):
                                    setattr(Gamepads[gamepadID].keyActions[actionID].restCfg, restParameter, True)
                                elif (parameterValue.lower() == "false"):
                                    setattr(Gamepads[gamepadID].keyActions[actionID].restCfg, restParameter, False)
                                else:
                                    setattr(Gamepads[gamepadID].keyActions[actionID].restCfg, restParameter, parameterValue)

                    #initalize data items sent with REST communication
                    for dataItemCfg in restCfg.findall('.//dataItems/dataItem'):
                        Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems.append(actionRestDataItem())     #add new data item to data items array
                        
                        dataItemParameterList = getClassAttributes(Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems[-1])      #access previously created item
                        #try to find the corresponding entry in the configuration file 
                        for dataItemParameter in dataItemParameterList:
                            parameterValue = dataItemCfg.get(dataItemParameter)
                            #continue only if configuration exists
                            if (parameterValue != None):
                                #convert to float or leave text
                                if is_number(parameterValue):          
                                    setattr(Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems[-1], dataItemParameter, float(parameterValue))
                                else:
                                    #text can be either true, false or any arbitrary text
                                    if (parameterValue.lower() == "true"):
                                        setattr(Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems[-1], dataItemParameter, True)
                                    elif (parameterValue.lower() == "false"):
                                        setattr(Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems[-1], dataItemParameter, False)
                                    else:
                                        setattr(Gamepads[gamepadID].keyActions[actionID].restCfg.dataItems[-1], dataItemParameter, parameterValue)
                    
            except Exception as e:
                print("Loading configuration for gamepad <{0}> failed: {1}".format(gamepadID, e))
                return    

    except Exception as e:
        print("Loading gamepad module configuration <{0}> failed: {1}".format(gamepadID, e))
        return    


def update():
    global Gamepads
    for gamepad in Gamepads:
        Gamepads[gamepad].update()
        
class gamepadManager:
    "Control of gamepad"
    #init
    def __init__(self, gamepadID):
        self.gamepadID = gamepadID
        self.param = gamepadParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sCONNECT": self.sCONNECT,
                             "sWAIT_CONNECTED": self.sWAIT_CONNECTED,
                             "sPROCESS_KEY_EVENTS": self.sPROCESS_KEY_EVENTS
                            }

        self.connectThread = None
        self.processKeyEventsThread = None
        self.interpretActionsThread = None
        
        self.inputDevice = None
        self.inputDevicePath = None
        
        self.inputKeyMap = dict()
        self.inputKeyCodeToID = dict()
        self.keyActions = dict()

        
    #cyclic logic    
    def update(self):
        #cycle time calculation
        self.samplingTime = max(time.time() - self.lastCallTime, 0)
        self.lastCallTime = time.time()

        #execute state machine
        self.statemachine[self.activeState]()
        if (self.activeStateOld != self.activeState):
           self.activeStateOld = self.activeState
           print("Gamepad state: " + self.activeState)
           

    def sIDLE(self):
        self.activeState = "sCONNECT"

    def sCONNECT(self):
        self.connectThread = threading.Thread(target=self.connect)
        self.connectThread.start()          
        self.activeState = "sWAIT_CONNECTED"

    def sWAIT_CONNECTED(self):
        try:
            self.inputDevicePath = Path(self.param.inputDevicePath)
            if self.inputDevicePath.exists() == True:
                self.inputDevice = InputDevice(self.param.inputDevicePath)
                self.activeState = "sPROCESS_KEY_EVENTS"
        except Exception as e:
            pass    #ignore errors: it needs some time until the device is accessible after the connection has been established
        

    def sPROCESS_KEY_EVENTS(self):
        try:
            if self.inputDevicePath.exists() == False:
                self.activeState = "sCONNECT"
                return
        except Exception as e:
            print("Check if gamepad <{0}> still exists failed: {1}".format(self.gamepadID, e))
        
        #start thread for handling key events
        if (self.processKeyEventsThread == None):
            self.processKeyEventsThread = threading.Thread(target=self.processKeyEvents)
            self.processKeyEventsThread.start()          
        else:
            #restart thread if finished
            if (self.processKeyEventsThread.isAlive() == False):
                self.processKeyEventsThread = threading.Thread(target=self.processKeyEvents)
                self.processKeyEventsThread.start()          

        #start threat for initiating actions such as REST messages
        if (self.interpretActionsThread == None):
            self.interpretActionsThread = threading.Thread(target=self.interpretActions)
            self.interpretActionsThread.start()          
        else:
            #restart thread if finished
            if (self.interpretActionsThread.isAlive() == False):
                self.interpretActionsThread = threading.Thread(target=self.interpretActions)
                self.interpretActionsThread.start()
            
            
        self.activeState = "sPROCESS_KEY_EVENTS"    #stay here until connections breaks
        

        
    def connect(self):
        subprocess.call(self.param.bluetoothConnectScript, shell=True)
        
    def processKeyEvents(self):
        try:
            #evdev takes care of polling the controller in a loop
            for event in self.inputDevice.read_loop():
                #filters by event type
                if (event.type == ecodes.EV_KEY) or (event.type == ecodes.EV_ABS) or (event.type != ecodes.EV_SYN):
                    #print(event)
                    if (str(event.code) in self.inputKeyCodeToID):
                        keyID = self.inputKeyCodeToID[str(event.code)]
                        self.inputKeyMap[keyID].value = event.value     #update newly received value in key mapping
                        self.inputKeyMap[keyID].newValue = True
                        #print("Key with code <{0}> from gamepad <{1}> received: value <{2}>".format(event.code, self.gamepadID, event.value))
                        
                    elif (event.code != 4):     #for some strange reason all push buttons cause an event with code 4 beside the corret code
                        #print("Key with code <{0}> / value <{1}> from gamepad <{2}> is unknown".format(event.code, event.value, self.gamepadID))
                        pass

        except Exception as e:
            print("Read inputs of gamepad <{0}> failed: {1}".format(self.gamepadID, e))
        
    def interpretActions(self):
        try:
            for action in Gamepads[self.gamepadID].keyActions:
                #1. check if trigger key has a new value and
                if (self.inputKeyMap[Gamepads[self.gamepadID].keyActions[action].triggerKey.id].newValue == True):
                    #scale input value and see whether it is 
                    #    1. out of dead band and equal
                    newScaledValue = Gamepads[self.gamepadID].keyActions[action].triggerKey.inOutScale.calcYfromX(self.inputKeyMap[Gamepads[self.gamepadID].keyActions[action].triggerKey.id].value)
                    
                    #print("action: <{0}> - {1}: raw:<{2}>, scaled:<{3}>".format(Gamepads[self.gamepadID].keyActions[action].id, Gamepads[self.gamepadID].keyActions[action].triggerKey.id, self.inputKeyMap[Gamepads[self.gamepadID].keyActions[action].triggerKey.id].value, newScaledValue))
                    
                    if abs(newScaledValue - Gamepads[self.gamepadID].keyActions[action].triggerKey.scaledValue) >= Gamepads[self.gamepadID].keyActions[action].triggerKey.outputDeadBandWindow:
                        Gamepads[self.gamepadID].keyActions[action].triggerKey.scaledValue = newScaledValue

                        #2. greater to trigger threshold (if configured)
                        if (Gamepads[self.gamepadID].keyActions[action].triggerKey.outputTriggerThreshold != None) and (Gamepads[self.gamepadID].keyActions[action].triggerKey.outputTriggerThreshold != ""):
                           if (Gamepads[self.gamepadID].keyActions[action].triggerKey.scaledValue < Gamepads[self.gamepadID].keyActions[action].triggerKey.outputTriggerThreshold):
                               continue
                            
                        #3. selector is active (if configured)
                        if (Gamepads[self.gamepadID].keyActions[action].triggerKey.selectorKeyId != None) and (Gamepads[self.gamepadID].keyActions[action].triggerKey.selectorKeyId != ""):
                            if (self.inputKeyMap[Gamepads[self.gamepadID].keyActions[action].triggerKey.selectorKeyId].value != Gamepads[self.gamepadID].keyActions[action].triggerKey.selectorKeyValue):
                                continue
        
                        #all good: action need to be executed
                        #print("Action <{0}> for key <{1}> will be executed: route={2}".format(Gamepads[self.gamepadID].keyActions[action].id, Gamepads[self.gamepadID].keyActions[action].triggerKey.id, Gamepads[self.gamepadID].keyActions[action].restCfg.route))

                        rest_data = dict()
                        for dataItem in Gamepads[self.gamepadID].keyActions[action].restCfg.dataItems:
                            try:
                                dataValue = ""
                                
                                #use value from a given key if exists
                                if (dataItem.valueFromKey != ""):
                                    dataValue = Gamepads[self.gamepadID].keyActions[action].triggerKey.scaledValue
                                #use fixed value form configuration
                                elif (dataItem.valueFix != ""):
                                    dataValue = dataItem.valueFix
                                    
                                                                        
                                #convert to float or leave text
                                if is_number(dataValue):
                                    rest_data[dataItem.name] = float(dataValue)
                                else:
                                    #text can be either true, false or any arbitrary text
                                    if (dataValue.lower() == "true"):
                                        rest_data[dataItem.name] = True
                                    elif (dataValue.lower() == "false"):
                                        rest_data[dataItem.name] = False
                                    else:
                                        rest_data[dataItem.name] = dataValue
                                    
                            except Exception as e:
                                print(e)
                        
                        #print("action: {0}, rest data: {1}".format(Gamepads[self.gamepadID].keyActions[action].id, rest_data))

                        #prepare REST communication
                        ipAdr = Gamepads[self.gamepadID].keyActions[action].restCfg.ipAdr
                        ipPort = str(int(Gamepads[self.gamepadID].keyActions[action].restCfg.ipPort))
                        routeOrigin = Gamepads[self.gamepadID].keyActions[action].restCfg.routeOrigin
                        route = Gamepads[self.gamepadID].keyActions[action].restCfg.route

                        #setup REST channel to servo server
                        RestClient[routeOrigin] = core.helper.rest.client(server_ip = ipAdr, server_port = ipPort, route_origin = routeOrigin)
                        RestClient[routeOrigin].post(rest_data, route)
            
            
            #reset all newValue flags 
            for keyID in self.inputKeyMap:
                self.inputKeyMap[keyID].newValue = False

        except Exception as e:
            print("Interpret action <{0}> of gamepad <{1}> failed: {2}".format(Gamepads[self.gamepadID].keyActions[action].id, self.gamepadID, e))




class gamepadParameters:
    #init
    def __init__(self):
        self.inputDevicePath = ""
        self.bluetoothConnectScript = ""

class inputKeyMap:
    #init
    def __init__(self, keyID):
        self.id = keyID
        self.code = None
        self.value = 0
        self.newValue = False

class actionParameters:
    #init
    def __init__(self, actionID):
        self.id = actionID
        self.triggerKey = actionTriggerKeyCfg()
        self.restCfg = actionRestCfg()
        

class actionTriggerKeyCfg:
    #init
    def __init__(self):
        self.id = None
        self.inMin = None
        self.inMax = None
        self.outMin = None
        self.outMax = None
        self.outputDeadBandWindow = None
        self.outputTriggerThreshold = None
        self.selectorKeyId = None
        self.selectorKeyValue = 0
        self.inOutScale = core.helper.xycurvelin.chartLin()
        self.scaledValue= 0


class actionRestCfg:
    #init
    def __init__(self):
        self.ipAdr = ""
        self.ipPort = ""
        self.routeOrigin = ""
        self.route = ""
        self.dataItems = []

class actionRestDataItem:
    #init
    def __init__(self):
        self.name = None
        self.valueFromKey = None
        self.valueFix = None


#get all properties of a class: dir() returns also dynamically added ones but also internal methods (filtered with __)
def getClassAttributes(c):
    return [p for p in dir(c) if not callable(getattr(c,p)) and not p.startswith("__")]

def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except:
        return False

    return True

#python3 /home/pi/wall-e/main.py

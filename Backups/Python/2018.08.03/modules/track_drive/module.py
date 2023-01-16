#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys


MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./trackdrives"
CFG_ROOT_ELEMENT_NAME = "/trackdrive"

def init():
    global TrackDrives
    TrackDrives = dict()
    attrList = [] 
    trackDriveID = None

    #read module configuration and initialize each track drive
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()

        #read configuration of switches
        for trackDriveCfg in cfgRoot.findall(CFG_ROOT_NAME + CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a switch manager for each switch found in the configuration
                trackDriveID = trackDriveCfg.get('id')
                TrackDrives[trackDriveID] = trackDriveManager()
                
                #initialize track drive parameters
                parameterNameList = getClassAttributes(TrackDrives[trackDriveID].param)      #['testValue', ...]
                #try to find the corresponding entry in the configuration file 
                for parameterName in parameterNameList:
                    #get access to input configuration: <parameter name="testValue">
                    parameterCfg = trackDriveCfg.find('.//parameters/parameter[@name="' + parameterName + '"]')
                    #continue only if configuration exists
                    if parameterCfg != None:
                        #convert to float or leave text
                        if is_number(parameterCfg.text):              
                            setattr(TrackDrives[trackDriveID].param, parameterName, float(parameterCfg.text))
                        else:
                            setattr(TrackDrives[trackDriveID].param, parameterName, parameterCfg.text)

            except Exception as e:
                print("Loading configuration for track drive <{0}> failed: {1}".format(trackDriveID, e))
                return    

    except Exception as e:
        print("Loading track drives module configuration <{0}> failed: {1}".format(trackDriveID, e))
        return    


def update():
    global TrackDrives
    '''
    Although WALL-E has only one track drive it is built like all other programs to have future flexibility 
    '''
    for trackDrive in TrackDrives:
        TrackDrives[trackDrive].update()
        
class trackDriveManager:
    "Control of track drive system"
    #init
    def __init__(self):
        self.param = trackDriveParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sOPERATIONAL": self.sOPERATIONAL
                            }


    #cyclic logic    
    def update(self):
        #cycle time calculation
        self.samplingTime = max(time.time() - self.lastCallTime, 0)
        self.lastCallTime = time.time()
        
        #execute state machine
        self.statemachine[self.activeState]()
        if (self.activeStateOld != self.activeState):
           self.activeStateOld = self.activeState
           print("Track drive state: " + self.activeState)


    def sIDLE(self):
        self.activeState = "sOPERATIONAL"
        
    def sOPERATIONAL(self):
        return



class trackDriveParameters:
    #init
    def __init__(self):
        self.testValue = 0.0

#get all properties of a class: dir() returns also dynamically added ones but also internal methods (filtered with __)
def getClassAttributes(c):
    return [p for p in dir(c) if not callable(getattr(c,p)) and not p.startswith("__")]

def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except ValueError:
        return False

    return True

#python3 /home/pi/wall-e/main.py

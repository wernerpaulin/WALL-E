#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.xycurvelin

# Import the PCA9685 module.
import Adafruit_PCA9685

MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_ELEMENT_NAME = "./servos/servo"

PWM_PERIODE_TICKS = 4096


def init():
    global Servos
    global ServoDriveBoard
    Servos = dict()
    attrList = [] 
    servoID = None
        
    #read module configuration and initialize each servo
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()

        #read configuration of switches
        for servoCfg in cfgRoot.findall(CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a switch manager for each switch found in the configuration
                servoID = servoCfg.get('id')
                Servos[servoID] = servoManager()
                
                #initialize servo parameters
                parameterNameList = getClassAttributes(Servos[servoID].param)      #['testValue', ...]
                #try to find the corresponding entry in the configuration file 
                for parameterName in parameterNameList:
                    #get access to input configuration: <parameter name="testValue">
                    parameterCfg = servoCfg.find('.//parameters/parameter[@name="' + parameterName + '"]')
                    #continue only if configuration exists
                    if parameterCfg != None:
                        #convert to float or leave text
                        if is_number(parameterCfg.text):              
                            setattr(Servos[servoID].param, parameterName, float(parameterCfg.text))
                        else:
                            setattr(Servos[servoID].param, parameterName, parameterCfg.text)

                #set up work space conversion: degrees into pwm duty cycle times
                Servos[servoID].workSpaceLin.addPointPair(float(Servos[servoID].param.angleMin), float(Servos[servoID].param.pwmDutyCycleMin))
                Servos[servoID].workSpaceLin.addPointPair(float(Servos[servoID].param.angleMax), float(Servos[servoID].param.pwmDutyCycleMax))

            except Exception as e:
                print("Loading configuration for servo channel <{0}> failed: {1}".format(servoID, e))
                return    

        # Initialize the PCA9685 using the i2c address and frequency of the first servo assuming all are the same (default: 0x40).
        i2cAdr = int(next(iter(Servos.values())).param.i2cAdr, 0)
        pwmFrequency = float(1.0 / next(iter(Servos.values())).param.pwmPeriode)
        ServoDriveBoard = Adafruit_PCA9685.PCA9685(address=i2cAdr)
        ServoDriveBoard.set_pwm_freq(pwmFrequency)        #set period of 20ms = 50Hz    

    except Exception as e:
        print("Loading servo module configuration <{0}> failed: {1}".format(servoID, e))
        return    


def update():
    global Servos
    
    '''
    Loop over all configured servos
    '''
    for servo in Servos:
        Servos[servo].update()
        
class servoManager:
    "Control of one servo"
    #init
    def __init__(self):
        self.param = servoParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sWAIT_FOR_COMMAND": self.sWAIT_FOR_COMMAND
                            }
        self.workSpaceLin = core.helper.xycurvelin.chartLin()       #this x/y chart linearization translates a given angle into pulse width


    #cyclic logic    
    def update(self):
        #cycle time calculation
        self.samplingTime = max(time.time() - self.lastCallTime, 0)
        self.lastCallTime = time.time()

        #execute state machine
        self.statemachine[self.activeState]()
        if (self.activeStateOld != self.activeState):
           self.activeStateOld = self.activeState
           print("Servo state: " + self.activeState)


    def sIDLE(self):
        self.activeState = "sWAIT_FOR_COMMAND"
        
    def sWAIT_FOR_COMMAND(self):
        global ServoDriveBoard
        self.moveAbsolute(180)
        
    
    def moveAbsolute(self, setPosDegree):
        #convert set position in degree to duty cycle duration
        dutyCycleDuration = self.workSpaceLin.calcYfromX(setPosDegree)
        
        #calculate number of duty cycle ticks
        dutyCycleTicksBegin = int(0) #always start cycle at beginning of period
        dutyCycleTicksEnd = int(PWM_PERIODE_TICKS / self.param.pwmPeriode * dutyCycleDuration)  

        #update PWM signal        
        ServoDriveBoard.set_pwm(int(self.param.pwmChannel), dutyCycleTicksBegin, dutyCycleTicksEnd)


class servoParameters:
    #init
    def __init__(self):
        self.angleMin = 0.0
        self.angleMax = 0.0
        self.pwmDutyCycleMin = 0.0
        self.pwmDutyCycleMax = 0.0
        self.pwmChannel = 0
        self.pwmPeriode = 0.0
        self.i2cAdr = 0



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

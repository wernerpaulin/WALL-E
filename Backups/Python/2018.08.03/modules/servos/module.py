#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.xycurvelin
import core.helper.rest

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Api, Resource
from flask_cors import CORS
import json
import re

# Import the PCA9685 module.
import Adafruit_PCA9685

MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./servos"
CFG_ROOT_ELEMENT_NAME = "/servo"


PWM_PERIODE_TICKS = 4096

JOB_NO_JOB = ""
JOB_MOVE_ABSOLUTE = "MoveAbsolute"
JOB_MOVE_VELOCITY = "MoveVelocity"
JOB_MOVE_STOP = "MoveStop"

#set up rest interface which is the bridge between the REST handler class and the servo manager
RESTinterface = {}



def init():
    global Servos
    global ServoDriveBoard
    global ServoDriveParameters
    global RestServer               #sends and receives REST messages

    Servos = dict()

    attrList = [] 
    servoID = None
        
    #read module configuration and initialize each servo
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()

        #read servo driver configuration (valid for all servos)
        ServoDriveParameters = servoDriveParameters()
        try:
            #simulation of entire driver
            simulation = cfgRoot.find(CFG_ROOT_NAME).get('simulation')
            if (simulation.lower() == "true"):
                ServoDriveParameters.simulation = True
                print("!!! WARNING: simulation of servos is active !!!")
            else:
               ServoDriveParameters.simulation = False 
        except:
            ServoDriveParameters.simulation = False

        #read configuration of switches
        for servoCfg in cfgRoot.findall(CFG_ROOT_NAME + CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a servo manager for each servo found in the configuration
                servoID = servoCfg.get('id')
                Servos[servoID] = servoManager(servoID)
                
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


        if ServoDriveParameters.simulation == False:
            # Initialize the PCA9685 using the i2c address and frequency of the first servo assuming all are the same (default: 0x40).
            i2cAdr = int(next(iter(Servos.values())).param.i2cAdr, 0)
            pwmFrequency = float(1.0 / next(iter(Servos.values())).param.pwmPeriode)
            ServoDriveBoard = Adafruit_PCA9685.PCA9685(address=i2cAdr)
            ServoDriveBoard.set_pwm_freq(pwmFrequency)        #set period of 20ms = 50Hz    


        #initialize rest server
        RestServer = core.helper.rest.server(route_origin = core.helper.rest.SERVOS_ROUTE_ORIGIN, server_visibility_public = True, server_ip = "", server_port = core.helper.rest.SERVOS_REST_SERVER_PORT, debug=False)
        
        #set up REST communication routes to resources of this modules
        #id: id of a specific servo channel
        #item: status data which should be sent back
        #type: type of movement which should be started
        RestServer.add_resource(RESTservice_Job, '/<string:id>/job/<string:job>')
        RestServer.add_resource(RESTservice_Status, '/<string:id>/status/<string:item>')


        #start rest server
        RestServer.run()

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
    def __init__(self, servoID):
        self.servoID = servoID
        self.param = servoParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sWAIT_FOR_COMMAND": self.sWAIT_FOR_COMMAND,
                             "sMOVE_ABSOLUTE": self.sMOVE_ABSOLUTE,
                             "sMOVE_VELOCITY": self.sMOVE_VELOCITY,
                             "sMOVE_STOP": self.sMOVE_STOP
                            }
        
        #this x/y chart linearization translates a given angle into pulse width
        self.workSpaceLin = core.helper.xycurvelin.chartLin()
        RESTinterface[servoID] = servoRESTinterface()


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
        if (RESTinterface[self.servoID].job.id == JOB_NO_JOB):
            self.activeState = "sWAIT_FOR_COMMAND"      #do nothing
        elif (RESTinterface[self.servoID].job.id == JOB_MOVE_STOP):
            self.activeState = "sMOVE_STOP"
        elif (RESTinterface[self.servoID].job.id == JOB_MOVE_VELOCITY):
            self.activeState = "sMOVE_VELOCITY"
        elif (RESTinterface[self.servoID].job.id == JOB_MOVE_ABSOLUTE):
            self.activeState = "sMOVE_ABSOLUTE"
        else:
            print("Warning: unknown job id <{0}> received".format(RESTinterface[self.servoID].job.id))
    
    def sMOVE_STOP(self):
        self.moveStop()
        RESTinterface[self.servoID].job.id = JOB_NO_JOB
        self.activeState = "sWAIT_FOR_COMMAND"
    
    def sMOVE_ABSOLUTE(self):
        self.moveAbsolute(RESTinterface[self.servoID].job.setPosition)
        RESTinterface[self.servoID].job.id = JOB_NO_JOB
        self.activeState = "sWAIT_FOR_COMMAND"

    def sMOVE_VELOCITY(self):
        self.moveVelocity(RESTinterface[self.servoID].job.setVelocity)
        RESTinterface[self.servoID].job.id = JOB_NO_JOB
        self.activeState = "sWAIT_FOR_COMMAND"

    def moveStop(self):
        if ServoDriveParameters.simulation == False:
            ServoDriveBoard.set_pwm(int(self.param.pwmChannel), 0, 0)

        
    def moveAbsolute(self, setPosDegree):
        if ServoDriveParameters.simulation == False:
            #convert set position[degree] to duty cycle duration
            dutyCycleDuration = self.workSpaceLin.calcYfromX(setPosDegree)
            
            #calculate number of duty cycle ticks
            dutyCycleTicksBegin = int(0) #always start cycle at beginning of period
            dutyCycleTicksEnd = int(PWM_PERIODE_TICKS / self.param.pwmPeriode * dutyCycleDuration)  
    
            #update PWM signal        
            ServoDriveBoard.set_pwm(int(self.param.pwmChannel), dutyCycleTicksBegin, dutyCycleTicksEnd)
            RESTinterface[self.servoID].status.actPosition = setPosDegree


    def moveVelocity(self, setVelocity):
        if ServoDriveParameters.simulation == False:
            print("TODO: moveVelocity implementieren")

            
class servoRESTinterface:
    #init
    def __init__(self):
        self.job = servoRESTjobs()
        self.status = servoRESTstatus()

class servoRESTjobs:
    #init
    def __init__(self):
        self.id = JOB_NO_JOB
        self.setVelocity = 0.0     #0-100%
        self.setPosition = 0.0     #0-360°

class servoRESTstatus:
    #init
    def __init__(self):
        self.actVelocity = 0.0     #0-100%
        self.actPosition = 0.0     #0-360°
        
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

class servoDriveParameters:
    #init
    def __init__(self):
        self.simulation = False


#definition of REST service
class RESTservice_Job(Resource):
    global RESTinterface

    def post(self, id, job):
        rxJsonData = request.get_json(force=True)

        #try update job interface of each servo with data from REST request, not received item will keep their old value
        for dataItem in rxJsonData:
            try:
                if dataItem in getClassAttributes(RESTinterface[id].job):
                    #convert to float or leave text
                    if is_number(getattr(RESTinterface[id].job, dataItem)):              
                        setattr(RESTinterface[id].job, dataItem, float(rxJsonData[dataItem]))
                    else:
                        setattr(RESTinterface[id].job, dataItem, rxJsonData[dataItem])
                    
            except Exception as e:
                errorMsg = 'ERROR: received data item <{0}> does not exist in servoRESTjobs; error: {1}'.format(dataItem, e)
                print(errorMsg)
                return errorMsg, core.helper.rest.HTTP_STATUS_NOT_FOUND

        #set job id to trigger action
        RESTinterface[id].job.id = job
        #print(RESTinterface[id].job.id)
        
        #print("Server - post MoveAbsolute received: data: {0}".format(rxJsonData))        
        return core.helper.rest.HTTP_STATUS_NO_CONTENT
    

class RESTservice_Status(Resource):
    global RESTinterface
    
    def get(self, id, item):
        #prepare a list so the data can be sent back as json      
        statusInfo = dict()
        statusInfo[item] = getattr(RESTinterface[id].status, item)
        return(json.dumps(statusInfo), core.helper.rest.HTTP_STATUS_OK) 





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

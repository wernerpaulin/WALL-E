#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.xycurvelin
import core.helper.rest
import core.helper.profgen

import json

from flask import request
from flask_restful import Resource

# Import the PCA9685 module.
import Adafruit_PCA9685

MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./servos"
CFG_ROOT_ELEMENT_NAME = "/servo"

SERVOBOARD_I2C_ADR = 0x40
SERVOBOARD_PWM_PERIODE_TICKS = 4096
SERVOBOARD_PWM_PERIODE_SECONDS = 0.02      #s (50Hz)

JOB_NO_JOB = ""
JOB_MOVE = "Move"
JOB_STOP = "Stop"

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
                    if (parameterCfg != None) and (parameterCfg.text != None):
                        #convert to float or leave text
                        if is_number(parameterCfg.text):              
                            setattr(Servos[servoID].param, parameterName, float(parameterCfg.text))
                        else:
                            #text can be either true, false or any arbitrary text
                            if (parameterCfg.text.lower() == "true"):
                                setattr(Servos[servoID].param, parameterName, True)
                            elif (parameterCfg.text.lower() == "false"):
                                setattr(Servos[servoID].param, parameterName, False)
                            else:
                                setattr(Servos[servoID].param, parameterName, parameterCfg.text)
                
                #set up work space conversion: absolute position in degrees into pwm duty cycle times
                Servos[servoID].servoDutyCycleLinPosition.addPointPair(float(Servos[servoID].param.sMin), float(Servos[servoID].param.pwmDutyCycleMin))
                Servos[servoID].servoDutyCycleLinPosition.addPointPair(float(Servos[servoID].param.sMax), float(Servos[servoID].param.pwmDutyCycleMax))

            except Exception as e:
                print("Loading configuration for servo channel <{0}> failed: {1}".format(servoID, e))
                return    


        if ServoDriveParameters.simulation == False:
            # Initialize the PCA9685
            ServoDriveBoard = Adafruit_PCA9685.PCA9685(address=SERVOBOARD_I2C_ADR)
            ServoDriveBoard.set_pwm_freq(float(1.0 / SERVOBOARD_PWM_PERIODE_SECONDS)) 


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
                             "sMOVING": self.sMOVING
                            }
        
        #this x/y chart linearization translates a given angle into pulse width
        self.servoDutyCycleLinPosition = core.helper.xycurvelin.chartLin()

        RESTinterface[self.servoID] = restInterface()
        self.profGenMovement = core.helper.profgen.profileGenerator()
        self.homingDone = False


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

        self.profGenMovement.update()
        
        if (self.param.isDCmotor == False):
            self.servoControl(self.profGenMovement.sProf)
        else:
            self.dcMotorControl(self.profGenMovement.vProf)

        RESTinterface[self.servoID].status.actVelocity = self.profGenMovement.vProf
        RESTinterface[self.servoID].status.actPosition = self.profGenMovement.sProf
        
    def sIDLE(self):
        self.activeState = "sWAIT_FOR_COMMAND"
        
        
    def sWAIT_FOR_COMMAND(self):
        #in case of a DC motor profile generator operates in velocity control 
        if (self.param.isDCmotor == True):
            moveType = core.helper.profgen.MOVE_TYPE_VELOCITY
        else:
            moveType = core.helper.profgen.MOVE_TYPE_POSITION
        
        if (self.homingDone == False):
            #initiate homing only if a specific position has been given otherwise ignore it - servo will home automatically due to PWM
            if (self.param.homingPosition != None):
                self.profGenMovement.initialize(self.param.aMax, self.param.vMax, self.param.sMin, self.param.sMax, self.profGenMovement.vProf, self.param.vMax / 2, self.profGenMovement.sProf, self.param.homingPosition, moveType)
                self.activeState = "sMOVING"

            #assume homing done anyway
            self.homingDone = True
            return
        else:
            if (RESTinterface[self.servoID].job.id == JOB_MOVE):
                self.profGenMovement.initialize(self.param.aMax, self.param.vMax, self.param.sMin, self.param.sMax, self.profGenMovement.vProf, RESTinterface[self.servoID].job.setVelocity, self.profGenMovement.sProf, RESTinterface[self.servoID].job.setPosition, moveType)
                RESTinterface[self.servoID].job.id = JOB_NO_JOB
                self.activeState = "sMOVING"


            
    def sMOVING(self):
        #print("ProfGen <{0}>: vProf={1}, sProf={2}, inPos={3}".format(self.servoID, round(self.profGenMovement.vProf,2), round(self.profGenMovement.sProf,2), self.profGenMovement.inPos))

        #status handling
        RESTinterface[self.servoID].status.inPos = self.profGenMovement.inPos
        RESTinterface[self.servoID].status.vMaxReached = self.profGenMovement.vMaxReached

        
        #during movement always give stop command highest priority
        if (RESTinterface[self.servoID].job.id == JOB_STOP):
            self.profGenMovement.cmdStop = True
        #in case of standard servo, go back to wait for new command if position has been reached
        elif (self.param.isDCmotor == False):
            if (self.profGenMovement.inPos == True):
                self.activeState = "sWAIT_FOR_COMMAND"
        #in case of a DC motor allow changes of speed during movement
        elif (self.param.isDCmotor == True):
            if (RESTinterface[self.servoID].job.id != JOB_NO_JOB):
                self.activeState = "sWAIT_FOR_COMMAND"                  #evaluate new command in sWAIT_FOR_COMMAND state
                

    def servoControl(self, sSet):
        #in case of simulation skip this function
        if ServoDriveParameters.simulation == True:
            return
        
        #limit moving range according to servo limits
        sSet = min(max(sSet, self.param.sMin), self.param.sMax)
        #convert set position[degree] to duty cycle duration
        dutyCycleDuration = self.servoDutyCycleLinPosition.calcYfromX(sSet)
        
        #calculate number of duty cycle ticks
        dutyCycleTicksBegin = int(0) #always start cycle at beginning of period
        dutyCycleTicksEnd = max(min(int(SERVOBOARD_PWM_PERIODE_TICKS / SERVOBOARD_PWM_PERIODE_SECONDS * dutyCycleDuration), SERVOBOARD_PWM_PERIODE_TICKS), 0)  #limit to 0..4096 to avoid damaging the servo

        #update PWM signal        
        ServoDriveBoard.set_pwm(int(self.param.pwmChannel), int(dutyCycleTicksBegin), int(dutyCycleTicksEnd))
        

    def dcMotorControl(self, vSet):
        #in case of simulation skip this function
        if ServoDriveParameters.simulation == True:
            return

        #limit moving range according to maximum speed in positive and negativ direction
        sSet = min(max(vSet, -self.param.vMax), self.param.vMax)

        #define motor direction depending on set speed
        if (vSet >= 0):
            motorDirection = 1
        else:
            motorDirection = -1 

        #invert motor direction if necessary to compensate wiring
        if (self.param.dcMotorReverseDirection == True):
            motorDirection = motorDirection * -1

        #set direction: PWM always on or off
        if (motorDirection >= 0):
            dutyCycleTicksBegin = int(0)
        else:
            dutyCycleTicksBegin = int(SERVOBOARD_PWM_PERIODE_TICKS)

        dutyCycleTicksEnd = int(0)
        ServoDriveBoard.set_pwm(int(self.param.directionChannel), dutyCycleTicksBegin, dutyCycleTicksEnd)
        
        #set speed which is proportional to duty cycle where maximum speed is equal to PWM always on (= max. periode ticks: 4096)
        dutyCycleTicksBegin = int(0)
        dutyCycleTicksEnd = max(min(abs(vSet / self.param.vMax * SERVOBOARD_PWM_PERIODE_TICKS), SERVOBOARD_PWM_PERIODE_TICKS), 0)

        #in case of an inverted direction the base of duty cycle is the maximum ticks
        if (motorDirection < 0):
            dutyCycleTicksEnd = SERVOBOARD_PWM_PERIODE_TICKS - int(dutyCycleTicksEnd) - 1
            dutyCycleTicksEnd = max(min(dutyCycleTicksEnd, SERVOBOARD_PWM_PERIODE_TICKS), 0)
        
        ServoDriveBoard.set_pwm(int(self.param.pwmChannel), int(dutyCycleTicksBegin), int(dutyCycleTicksEnd))
        return
            
class restInterface:
    #init
    def __init__(self):
        self.job = restJobs()
        self.status = restStatus()

class restJobs:
    #init
    def __init__(self):
        self.id = JOB_NO_JOB
        self.setVelocity = 0.0     #0-100%
        self.setPosition = 0.0     #0-360°

class restStatus:
    #init
    def __init__(self):
        self.actVelocity = 0.0     #0-100%
        self.actPosition = 0.0     #0-360°
        self.inPos = False
        self.vMaxReached = False
        
class servoParameters:
    #init
    def __init__(self):
        self.pwmChannel = 0
        self.pwmDutyCycleMin = 0.0
        self.pwmDutyCycleMax = 0.0
        self.directionChannel = 0
        self.sMin = 0.0
        self.sMax = 0.0
        self.vMax = 0.0
        self.aMax = 0.0
        self.homingPosition = None
        self.isDCmotor = False
        self.dcMotorReverseDirection = False


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
        
        #print("Server - post received: data: {0}".format(rxJsonData))     
        #print("job id:{0}, sSet:{1}, sVel: {2}".format(RESTinterface[id].job.id, RESTinterface[id].job.setVelocity, RESTinterface[id].job.setPosition))   
        return core.helper.rest.HTTP_STATUS_NO_CONTENT
    

class RESTservice_Status(Resource):
    global RESTinterface
    
    def get(self, id, item):
        try:
            #prepare a list so the data can be sent back as json      
            statusInfo = dict()
            statusInfo[item] = getattr(RESTinterface[id].status, item)
            return(json.dumps(statusInfo), core.helper.rest.HTTP_STATUS_OK) 
        except Exception as e:
            errorMsg = 'ERROR: fetching data item <{0}>. Does not exist in servoRESTjobs; error: {1}'.format(dataItem, e)
            print(errorMsg)
            return errorMsg, core.helper.rest.HTTP_STATUS_NOT_FOUND





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

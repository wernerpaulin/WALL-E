#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.rest
import core.helper.profgen
import core.helper.xycurvelin

import json

from flask import request
from flask_restful import Resource

# Import the ADS1x15 module.
import Adafruit_ADS1x15

DISTANCE_SENSOR_ADC_I2C_ADR = 0x48
DISTANCE_SENSOR_ADC_I2C_BUSNUM = 1
DISTANCE_SENSOR_ADC_GAIN = 1



MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./trackdrives"
CFG_ROOT_ELEMENT_NAME = "/trackdrive"

JOB_NO_JOB = ""
JOB_MOVE = "Move"
JOB_TURN_LEFT = "TurnLeft"
JOB_TURN_RIGHT = "TurnRight"
JOB_STOP = "Stop"

STILL_STAND_THRESHOLD = 0.1


#set up rest interface which is the bridge between the REST handler class and the track manager
RESTinterface = {}

PRESCALER_GET_SERVO_STATUS  = 10     #10 times of cycle time

def init():
    global TrackDrives
    global RestServer               #sends and receives REST messages
    global RestClient               #contains all REST clients which have channels to other servers 
    global TrackDriveParameters
    
    RestClient = dict()
    TrackDrives = dict()
    attrList = [] 
    trackDriveID = None

    #read module configuration and initialize each track drive
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()

        #read track driver configuration (valid for all track drives)
        TrackDriveParameters = trackDriveParameters()
        try:
            #simulation of entire driver
            simulation = cfgRoot.find(CFG_ROOT_NAME).get('simulation')
            if (simulation.lower() == "true"):
                TrackDriveParameters.simulation = True
                print("!!! WARNING: simulation of track drives is active !!!")
            else:
               TrackDriveParameters.simulation = False 
        except:
            TrackDriveParameters.simulation = False



        #read configuration
        for trackDriveCfg in cfgRoot.findall(CFG_ROOT_NAME + CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a switch manager for each switch found in the configuration
                trackDriveID = trackDriveCfg.get('id')
                TrackDrives[trackDriveID] = trackDriveManager(trackDriveID)
                
                #initialize track drive parameters
                parameterNameList = getClassAttributes(TrackDrives[trackDriveID].param)      #['testValue', ...]
                #try to find the corresponding entry in the configuration file 
                for parameterName in parameterNameList:
                    #get access to input configuration: <parameter name="testValue">
                    parameterCfg = trackDriveCfg.find('.//parameters/parameter[@name="' + parameterName + '"]')
                    #continue only if configuration exists
                    if (parameterCfg != None) and (parameterCfg.text != None):
                        #convert to float or leave text
                        if is_number(parameterCfg.text):          
                            setattr(TrackDrives[trackDriveID].param, parameterName, float(parameterCfg.text))
                        else:
                            #text can be either true, false or any arbitrary text
                            if (parameterCfg.text.lower() == "true"):
                                setattr(TrackDrives[trackDriveID].param, parameterName, True)
                            elif (parameterCfg.text.lower() == "false"):
                                setattr(TrackDrives[trackDriveID].param, parameterName, False)
                            else:
                                setattr(TrackDrives[trackDriveID].param, parameterName, parameterCfg.text)


                #obstacle handling - distance sensor linearization
                pointPairCfg = trackDriveCfg.findall('.//parameters/obstacleHandling/distanceMeasurement/pointpairs/pointpair')
                for pointPair in pointPairCfg:
                    TrackDrives[trackDriveID].param.distanceSensorLin.addPointPair(float(pointPair.attrib['adcValue']), float(pointPair.attrib['distance']))        

                #obstacle handling - observation zones
                zoneCfg = trackDriveCfg.findall('.//parameters/obstacleHandling/observationZones/observationZone')
                for zone in zoneCfg:
                    TrackDrives[trackDriveID].param.obstacleZones.append([])
                    TrackDrives[trackDriveID].param.obstacleZones[len(TrackDrives[trackDriveID].param.obstacleZones)-1] = paramObstacleZones()

                    TrackDrives[trackDriveID].param.obstacleZones[len(TrackDrives[trackDriveID].param.obstacleZones)-1].distance = float(zone.attrib['distance'])
                    TrackDrives[trackDriveID].param.obstacleZones[len(TrackDrives[trackDriveID].param.obstacleZones)-1].velocityScale = float(zone.attrib['velocityScale'])
                    TrackDrives[trackDriveID].param.obstacleZones[len(TrackDrives[trackDriveID].param.obstacleZones)-1].textToSpeech = str(zone.attrib['textToSpeech'])
                    TrackDrives[trackDriveID].param.obstacleZones[len(TrackDrives[trackDriveID].param.obstacleZones)-1].audioFile = str(zone.attrib['audioFile'])

                        

            except Exception as e:
                print("Loading configuration for track drive <{0}> failed: {1}".format(trackDriveID, e))
                return    

        #initialize rest server
        RestServer = core.helper.rest.server(route_origin = core.helper.rest.TRACK_ROUTE_ORIGIN, server_visibility_public = True, server_ip = "", server_port = core.helper.rest.TRACK_REST_SERVER_PORT, debug=False)
        
        #set up REST communication routes to resources of this modules
        #id: id of a specific track drive (currently WALL-E has only one called 'main'
        #item: status data which should be sent back
        #type: type of movement which should be started
        RestServer.add_resource(RESTservice_Job, '/<string:id>/job/<string:job>')
        RestServer.add_resource(RESTservice_Status, '/<string:id>/status/<string:item>')

        #start rest server
        RestServer.run()

        #setup REST channel to servo server
        RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN] = core.helper.rest.client(server_ip = core.helper.rest.SERVER_LOCAL_HOST_IP, server_port = core.helper.rest.SERVOS_REST_SERVER_PORT, route_origin = core.helper.rest.SERVOS_ROUTE_ORIGIN)
        
        #setup REST channel to audio manager
        RestClient[core.helper.rest.AUDIO_ROUTE_ORIGIN] = core.helper.rest.client(server_ip = core.helper.rest.SERVER_LOCAL_HOST_IP, server_port = core.helper.rest.AUDIO_REST_SERVER_PORT, route_origin = core.helper.rest.AUDIO_ROUTE_ORIGIN)
        
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
    def __init__(self, trackID):
        self.trackID = trackID
        self.param = trackDriveParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sWAIT_FOR_COMMAND": self.sWAIT_FOR_COMMAND,
                             "sMOVING": self.sMOVING
                            }

        RESTinterface[self.trackID] = restInterface()
        self.getServoStatusPrescalerCnt = 0
        
        if (TrackDriveParameters.simulation == False):
            self.distanceSensorADC = Adafruit_ADS1x15.ADS1115(address=DISTANCE_SENSOR_ADC_I2C_ADR, busnum=DISTANCE_SENSOR_ADC_I2C_BUSNUM)
        else:
            self.distanceSensorADC = None
            
        self.distanceReadIntervalTimer = 0.0
        self.distanceToObstacle = 0.0
        self.inZoneIndex = 0
        self.lastZoneIndex = 0
        self.setVelocityCurrentLeft = 0
        self.setVelocityCurrentRight = 0


    #cyclic logic    
    def update(self):
        #cycle time calculation
        self.samplingTime = max(time.time() - self.lastCallTime, 0)
        self.lastCallTime = time.time()

        #continous measurement of distance to obstacle
        self.distanceReadIntervalTimer = self.distanceReadIntervalTimer + self.samplingTime
        if (self.distanceReadIntervalTimer >= self.param.distanceMeasurementSamplingTime):
            self.distanceReadIntervalTimer = 0

            if (TrackDriveParameters.simulation == False):
                self.distanceToObstacle = self.param.distanceSensorLin.calcYfromX(self.distanceSensorADC.read_adc(int(self.param.distanceMeasurementADCchannel), gain=DISTANCE_SENSOR_ADC_GAIN))
            else:
                self.distanceToObstacle = 100000       #no obstical during simulation
            
            #print(self.distanceToObstacle)
            #print(self.distanceSensorADC.read_adc(int(self.param.distanceMeasurementADCchannel), gain=DISTANCE_SENSOR_ADC_GAIN))

        #execute state machine
        self.statemachine[self.activeState]()
        if (self.activeStateOld != self.activeState):
           self.activeStateOld = self.activeState
           #print("Track drive state: " + self.activeState)
           

    def sIDLE(self):
        self.activeState = "sWAIT_FOR_COMMAND"
        
    def sWAIT_FOR_COMMAND(self):
        if (RESTinterface[self.trackID].job.id == JOB_STOP):
            #no data required to pass on
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(dict(), "/" + self.param.driveIdLeft + "/job/Stop")
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(dict(), "/" + self.param.driveIdRight + "/job/Stop")

            RESTinterface[self.trackID].job.id = JOB_NO_JOB
            self.activeState = "sWAIT_FOR_COMMAND"
        
        elif (RESTinterface[self.trackID].job.id == JOB_MOVE):
            #print("New move job track: <{0}>".format(json.dumps(move_data)))
            move_data = dict()
            move_data["setVelocity"] = RESTinterface[self.trackID].job.setVelocity
            move_data["setPosition"] = RESTinterface[self.trackID].job.setPosition
            
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdLeft + "/job/Move")
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdRight + "/job/Move")

            RESTinterface[self.trackID].job.id = JOB_NO_JOB

            #keep current speed of both drives
            self.setVelocityCurrentLeft = RESTinterface[self.trackID].job.setVelocity
            self.setVelocityCurrentRight = RESTinterface[self.trackID].job.setVelocity

            self.activeState = "sMOVING"
        
        elif (RESTinterface[self.trackID].job.id == JOB_TURN_LEFT):
            #print("New turn job track: <{0}>".format(json.dumps(move_data)))

            #read current speed of both drives
            actVelocityLeft = self.getActVelocity(self.param.driveIdLeft)
            actVelocityRight = self.getActVelocity(self.param.driveIdRight)

            #do not issue another turning command if the track is already turning
            if (actVelocityLeft != actVelocityRight):
                RESTinterface[self.trackID].job.id = JOB_NO_JOB
                self.activeState = "sMOVING"
                return
            
            move_data = dict()
            
            #increase speed of left drive
            move_data["setVelocity"] = actVelocityLeft - abs(RESTinterface[self.trackID].job.setTurningDeltaVelocity)
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdLeft + "/job/Move")
            #keep current speed of drives
            self.setVelocityCurrentLeft = move_data["setVelocity"]
            
            #decrease speed of right drive
            move_data["setVelocity"] = actVelocityRight + abs(RESTinterface[self.trackID].job.setTurningDeltaVelocity)
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdRight + "/job/Move")
            #keep current speed of drives
            self.setVelocityCurrentRight = move_data["setVelocity"]

            RESTinterface[self.trackID].job.id = JOB_NO_JOB
            self.activeState = "sMOVING"
            
        elif (RESTinterface[self.trackID].job.id == JOB_TURN_RIGHT):
            #print("New turn job track: <{0}>".format(json.dumps(move_data)))

            #read current speed of both drives
            actVelocityLeft = self.getActVelocity(self.param.driveIdLeft)
            actVelocityRight = self.getActVelocity(self.param.driveIdRight)
            
            #do not issue another turning command if the track is already turning
            if (actVelocityLeft != actVelocityRight):
                RESTinterface[self.trackID].job.id = JOB_NO_JOB
                self.activeState = "sMOVING"
                return
            
            move_data = dict()
            
            #increase speed of left drive
            move_data["setVelocity"] = actVelocityLeft + abs(RESTinterface[self.trackID].job.setTurningDeltaVelocity)
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdLeft + "/job/Move")
            #keep current speed of drives
            self.setVelocityCurrentLeft = move_data["setVelocity"]
            
            #decrease speed of right drive
            move_data["setVelocity"] = actVelocityRight - abs(RESTinterface[self.trackID].job.setTurningDeltaVelocity)
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdRight + "/job/Move")
            #keep current speed of drives
            self.setVelocityCurrentRight = move_data["setVelocity"]

            RESTinterface[self.trackID].job.id = JOB_NO_JOB
            self.activeState = "sMOVING"
            

    def sMOVING(self):
        #cyclically get actual postion
        self.getServoStatusPrescalerCnt = self.getServoStatusPrescalerCnt + 1
        if (self.getServoStatusPrescalerCnt >= PRESCALER_GET_SERVO_STATUS):
            self.getServoStatusPrescalerCnt = 0

            actVelocityLeft = self.getActVelocity(self.param.driveIdLeft)
            actVelocityRight = self.getActVelocity(self.param.driveIdRight)

            #leave moving state if track stands still
            if abs(actVelocityLeft) <= STILL_STAND_THRESHOLD:
                self.activeState = "sWAIT_FOR_COMMAND"

        #obstacle handling
        for index, zone in enumerate(self.param.obstacleZones, start=0):   # default is zero
            #find smallest zone and set actions according to configuration
            if (self.distanceToObstacle <= zone.distance):
                self.inZoneIndex = index
        
        #check whether zone has been changed - do not set actions twice until zone has been left and reentered again
        if (self.inZoneIndex != self.lastZoneIndex):
            self.lastZoneIndex = self.inZoneIndex
            #print("Distance: {0}, Zone distance: {1}".format(self.distanceToObstacle, self.param.obstacleZones[self.inZoneIndex].distance))
            audio_data = dict()
            audio_data["audioFile"] = self.param.obstacleZones[self.inZoneIndex].audioFile
            audio_data["textToSpeech"] = self.param.obstacleZones[self.inZoneIndex].textToSpeech
            RestClient[core.helper.rest.AUDIO_ROUTE_ORIGIN].post(audio_data, "/" + self.param.audioDevice + "/job/Play")

            
            move_data = dict()
            #adapt speed of left drive
            move_data["setVelocity"] = self.setVelocityCurrentLeft * self.param.obstacleZones[self.inZoneIndex].velocityScale
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdLeft + "/job/Move")
            
            #adapt speed of right drive
            move_data["setVelocity"] = self.setVelocityCurrentRight * self.param.obstacleZones[self.inZoneIndex].velocityScale
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdRight + "/job/Move")


        if (RESTinterface[self.trackID].job.id != JOB_NO_JOB):
            self.activeState = "sWAIT_FOR_COMMAND"
    
    def getActVelocity(self, driveId):
        req = RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].get("/" + driveId + "/status/actVelocity")
        if (req['status'] >= core.helper.rest.HTTP_STATUS_CLIENT_ERRORS):
            print("REST GET error <{0}> in track handler <{1}> requesting servo status".format(req['status'], self.trackID))
            return(0.0)
        else:
            servo_move_status = json.loads(req['data'])
            return(float(servo_move_status["actVelocity"]))
        

class trackDriveParameters:
    #init
    def __init__(self):
        self.simulation = False


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
        self.setPosition = 0.0     #0-float max
        self.setTurningDeltaVelocity = 0.0 #0-100%   

class restStatus:
    #init
    def __init__(self):
        self.actVelocity = 0.0     #0-100%
        self.actPosition = 0.0     #0-float max

class trackDriveParameters:
    #init
    def __init__(self):
        self.driveIdLeft = ""
        self.driveIdRight = ""
        self.distanceMeasurementSamplingTime = 0.0
        self.distanceMeasurementADCchannel = 1
        self.audioDevice = ""

        self.distanceSensorLin = core.helper.xycurvelin.chartLin()  #this x/y chart linearization translates a measured analog value from IR-sensor into a distance in meter
        self.obstacleZones = []

class paramObstacleZones:
    #init
    def __init__(self):
        self.distance = 0.0
        self.velocityScale = 0.0
        self.audioFile = ""
        self.textToSpeech = ""

#definition of REST service
class RESTservice_Job(Resource):
    global RESTinterface

    def post(self, id, job):
        rxJsonData = request.get_json(force=True)

        #try update job interface with data from REST request, not received item will keep their old value
        for dataItem in rxJsonData:
            try:
                if dataItem in getClassAttributes(RESTinterface[id].job):
                    #convert to float or leave text
                    if is_number(getattr(RESTinterface[id].job, dataItem)):              
                        setattr(RESTinterface[id].job, dataItem, float(rxJsonData[dataItem]))
                    else:
                        setattr(RESTinterface[id].job, dataItem, rxJsonData[dataItem])
                    
            except Exception as e:
                errorMsg = 'ERROR: received data item <{0}> does not exist in trackRESTjobs; error: {1}'.format(dataItem, e)
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
        try:
            #prepare a list so the data can be sent back as json      
            statusInfo = dict()
            statusInfo[item] = getattr(RESTinterface[id].status, item)
            return(json.dumps(statusInfo), core.helper.rest.HTTP_STATUS_OK) 
        except Exception as e:
            errorMsg = 'ERROR: fetching data item <{0}>. Does not exist in trackRESTjobs; error: {1}'.format(dataItem, e)
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

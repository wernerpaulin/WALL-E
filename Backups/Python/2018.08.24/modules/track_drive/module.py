#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.rest
import core.helper.profgen

import json

from flask import request
from flask_restful import Resource


MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./trackdrives"
CFG_ROOT_ELEMENT_NAME = "/trackdrive"

JOB_NO_JOB = ""
JOB_MOVE = "Move"
JOB_MOVE_STOP = "MoveStop"
JOB_MOVE_TURNLEFT = "MoveTurnLeft"
JOB_MOVE_TURNRIGHT = "MoveTurnRight"


#set up rest interface which is the bridge between the REST handler class and the track manager
RESTinterface = {}

PRESCALER_GET_SERVO_STATUS  = 10     #10 times of cycle time

def init():
    global TrackDrives
    global RestServer               #sends and receives REST messages
    global RestClient               #contains all REST clients which have channels to other servers 
    
    RestClient = dict()
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
        self.activeState = "sWAIT_FOR_COMMAND"
        
    def sWAIT_FOR_COMMAND(self):
        if (RESTinterface[self.trackID].job.id == JOB_MOVE):
            self.activeState = "sMOVING"
            move_data = dict()
            move_data["setVelocity"] = RESTinterface[self.trackID].job.setVelocity
            move_data["setPosition"] = RESTinterface[self.trackID].job.setPosition
            
            #print("New job track: <{0}>".format(json.dumps(move_data)))
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdLeft + "/job/Move")
            RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].post(move_data, "/" + self.param.driveIdRight + "/job/Move")

    def sMOVING(self):
        RESTinterface[self.trackID].job.id = JOB_NO_JOB
        inPos = False
        
        self.getServoStatusPrescalerCnt = self.getServoStatusPrescalerCnt + 1
        if (self.getServoStatusPrescalerCnt >= PRESCALER_GET_SERVO_STATUS):
            self.getServoStatusPrescalerCnt = 0

            req = RestClient[core.helper.rest.SERVOS_ROUTE_ORIGIN].get("/" + self.param.driveIdLeft + "/status/inPos")
            if (req['status'] >= core.helper.rest.HTTP_STATUS_CLIENT_ERRORS):
                print("REST GET error <{0}> in track handler <{1}> requesting servo status".format(req['status'], self.trackID))
            else:
                servo_move_status = json.loads(req['data'])
                inPos = servo_move_status["inPos"]

        if (inPos == True):
            self.activeState = "sWAIT_FOR_COMMAND"
        elif (RESTinterface[self.trackID].job.id == JOB_MOVE_STOP):
            print("TODO: STOP of TRACK einbauen")
            self.activeState = "sWAIT_FOR_COMMAND"


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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import xml.etree.ElementTree as xmlParser
import datetime, time
import sys
import core.helper.rest
import threading

import json

from flask import request
from flask_restful import Resource


from omxplayer.player import OMXPlayer
from pathlib import Path
from subprocess import call



MODULE_CFG_FILE_NAME = "module.cfg.xml"
CFG_ROOT_NAME = "./audioDevices"
CFG_ROOT_ELEMENT_NAME = "/audioDevice"

JOB_NO_JOB = ""
JOB_PLAY = "Play"

#set up rest interface which is the bridge between the REST handler class and the audio handler
RESTinterface = {}

def init():
    global AudioDevices
    global RestServer               #sends and receives REST messages
    
    AudioDevices = dict()
    attrList = [] 
    audioID = None
        
    #read module configuration and initialize
    try:
        cfgFile = os.path.dirname(__file__) + '/' + MODULE_CFG_FILE_NAME
        cfgTree = xmlParser.parse(cfgFile)
        cfgRoot = cfgTree.getroot()


        #read configuration
        for audioDeviceCfg in cfgRoot.findall(CFG_ROOT_NAME + CFG_ROOT_ELEMENT_NAME):
            try:
                #set up a switch manager for each switch found in the configuration
                audioID = audioDeviceCfg.get('id')
                AudioDevices[audioID] = audioDeviceManager(audioID)
                
                #initialize audio device parameters
                parameterNameList = getClassAttributes(AudioDevices[audioID].param)      #['testValue', ...]
                #try to find the corresponding entry in the configuration file 
                for parameterName in parameterNameList:
                    #get access to input configuration: <parameter name="testValue">
                    parameterCfg = audioDeviceCfg.find('.//parameters/parameter[@name="' + parameterName + '"]')
                    #continue only if configuration exists
                    if (parameterCfg != None) and (parameterCfg.text != None):
                        #convert to float or leave text
                        if is_number(parameterCfg.text):          
                            setattr(AudioDevices[audioID].param, parameterName, float(parameterCfg.text))
                        else:
                            #text can be either true, false or any arbitrary text
                            if (parameterCfg.text.lower() == "true"):
                                setattr(AudioDevices[audioID].param, parameterName, True)
                            elif (parameterCfg.text.lower() == "false"):
                                setattr(AudioDevices[audioID].param, parameterName, False)
                            else:
                                setattr(AudioDevices[audioID].param, parameterName, parameterCfg.text)


            except Exception as e:
                print("Loading configuration for audio device <{0}> failed: {1}".format(audioID, e))
                return          
        
        #initialize rest server
        RestServer = core.helper.rest.server(route_origin = core.helper.rest.AUDIO_ROUTE_ORIGIN, server_visibility_public = True, server_ip = "", server_port = core.helper.rest.AUDIO_REST_SERVER_PORT, debug=False)
        
        #set up REST communication routes to resources of this modules
        #id: id of a specific audio device (currently WALL-E has only one called 'analog')
        RestServer.add_resource(RESTservice_Job, '/<string:id>/job/<string:job>')

        #start rest server
        RestServer.run()

    except Exception as e:
        print("Loading audio module configuration <{0}> failed: {1}".format(audioID, e))
        return    


def update():
    global AudioDevices
    '''
    Although WALL-E has only one audio device it is built like all other programs to have future flexibility 
    '''
    #for audioDevice in AudioDevices:
    #    AudioDevices[audioDevice].update()
        
class audioDeviceManager:
    "Control of audio devices"
    #init
    def __init__(self, audioID):
        self.audioID = audioID
        self.param = audioParameters()
        self.lastCallTime = time.time()
        self.samplingTime = 0
        self.activeState = "sIDLE"
        self.activeStateOld = ""
        
        self.statemachine = {
                             "sIDLE": self.sIDLE,
                             "sWAIT_FOR_COMMAND": self.sWAIT_FOR_COMMAND,
                             "sPLAY": self.sPLAY
                            }

        RESTinterface[self.audioID] = restInterface()
        self.playFileThread = None
        self.textToSpeechThread = None


    #cyclic logic    
    def update(self):
        #cycle time calculation
        self.samplingTime = max(time.time() - self.lastCallTime, 0)
        self.lastCallTime = time.time()

        #execute state machine
        self.statemachine[self.activeState]()
        if (self.activeStateOld != self.activeState):
           self.activeStateOld = self.activeState
           #print("Audio state: " + self.activeState)
           

    def sIDLE(self):
        self.activeState = "sWAIT_FOR_COMMAND"
        
    def sWAIT_FOR_COMMAND(self):
        if (RESTinterface[self.audioID].job.id == JOB_PLAY):
            RESTinterface[self.audioID].job.id = JOB_NO_JOB
            self.activeState = "sPLAY"

    def sPLAY(self):
        if (len(RESTinterface[self.audioID].job.textToSpeech) > 0):
            self.textToSpeechThread = threading.Thread(target=self.textToSpeech)
            self.textToSpeechThread.start()            


        if (len(RESTinterface[self.audioID].job.audioFile) > 0):
            self.playFileThread = threading.Thread(target=self.playFile)
            self.playFileThread.start()            
    
        self.activeState = "sWAIT_FOR_COMMAND"

    def playFile(self):
        try:
            player = OMXPlayer(Path(RESTinterface[self.audioID].job.audioFile))
            #player.quit()
        except Exception as e:
            print("Audio module playing file <{0}> failed: {1}".format(RESTinterface[self.audioID].job.audioFile, e))
        
    def textToSpeech(self):
        try:
            text = str(RESTinterface[self.audioID].job.textToSpeech).replace(' ', '_')
            cmd= 'espeak -v' + self.param.speakLanguageCode + ' ' + text + ' &>/dev/null'       #redirects stdout and stderr to null device to surpress any output
            #Calls the Espeak TTS Engine to read aloud a Text
            call([cmd], shell=True)
        except Exception as e:
            print("Audio module text-to-speech <{0}> failed: {1}".format(RESTinterface[self.audioID].job.textToSpeech, e))

        



class restInterface:
    #init
    def __init__(self):
        self.job = restJobs()

class restJobs:
    #init
    def __init__(self):
        self.id = JOB_NO_JOB
        self.audioFile = ""
        self.textToSpeech = ""

class audioParameters:
    #init
    def __init__(self):
        self.speakLanguageCode = ""


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
                errorMsg = 'ERROR: received data item <{0}> does not exist in REST jobs of Audio; error: {1}'.format(dataItem, e)
                print(errorMsg)
                return errorMsg, core.helper.rest.HTTP_STATUS_NOT_FOUND

        #set job id to trigger action
        RESTinterface[id].job.id = job
        #print(RESTinterface[id].job.id)
        
        #print("Server - post MoveAbsolute received: data: {0}".format(rxJsonData))        
        return core.helper.rest.HTTP_STATUS_NO_CONTENT

 
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

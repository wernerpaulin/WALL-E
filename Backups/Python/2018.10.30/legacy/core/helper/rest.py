#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import os.path
import sys
import threading

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Api, Resource
from flask_cors import CORS
import json

import requests
import json

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

#https://httpstatuses.com
HTTP_STATUS_OK = 200
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_CLIENT_ERRORS = 400
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422


SERVOS_REST_SERVER_PORT = 5000
SERVOS_ROUTE_ORIGIN = "servos"

TRACK_REST_SERVER_PORT = 5001
TRACK_ROUTE_ORIGIN = "track"

AUDIO_REST_SERVER_PORT = 5002
AUDIO_ROUTE_ORIGIN = "audio"

SERVER_LOCAL_HOST_IP = "127.0.0.1"


class server():
    "REST server"
    def __init__(self,route_origin, server_visibility_public, server_ip, server_port, debug):
        self.route_origin = route_origin
        
        #override server ip in case server is publicly available 
        if server_visibility_public == True:
            self.server_ip = '0.0.0.0'
        else:
            self.server_ip = server_ip

        self.server_port = server_port
        self.debug = debug

        #set up rest infrastructure
        self.app = Flask(self.route_origin)
        CORS(self.app)
        self.api = Api(self.app)
        return
    
    #add resource with route
    def add_resource(self, resourceClassName, route):
        self.api.add_resource(resourceClassName, '/' + self.route_origin + route)
        return

    def runThread(self):
        self.app.run(debug=self.debug, host=self.server_ip, port=self.server_port, threaded=True) #threaded=True ...processing multiple requests in parallel
        return

    #start REST server
    def run(self):
        self.restThread = threading.Thread(target=self.runThread)
        self.restThread.start()
        return
    


class client():
    "REST client"
    def __init__(self, server_ip, server_port, route_origin):
        self.server_ip = server_ip
        self.server_port = server_port
        self.route_origin = route_origin
        return

    def runThread(self):
        pass
    
    def post(self, json_data, route):
        req = requests.post('http://' + self.server_ip + ':' + str(self.server_port) + '/' + self.route_origin + route, json=json_data)
        if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
            print('REST POST http error <{0}> to server ip <{1}> with route <{2}>'.format(req.status_code, self.server_ip, route_origin + route))
        return req.status_code


        #start threat for initiating actions such as REST messages
        #if (self.postThread == None):
        #    self.postThread = threading.Thread(target=self.runThread)
        #   self.postThread.start()          
        #else:
        #    #restart thread if finished
        #    if (self.postThread.isAlive() == False):
        #        self.postThread = threading.Thread(target=self.runThread)
        #        self.postThread.start()


        
    def get(self, route):
        req = requests.get('http://' + self.server_ip + ':' + str(self.server_port) + '/' + self.route_origin + route)
        if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
            print('REST GET http error <{0}> to server ip <{1}>'.format(req.status_code, self.server_ip))
        
        return {'status': req.status_code, 'data' : json.loads(req.text)}       #json.loads necessary to get a real json string, strangly still not an object
        
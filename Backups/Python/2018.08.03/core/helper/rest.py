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


#https://httpstatuses.com
HTTP_STATUS_OK = 200
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_CLIENT_ERRORS = 400
HTTP_STATUS_BAD_REQUEST = 400
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422


SERVOS_REST_SERVER_PORT = 5000
SERVOS_ROUTE_ORIGIN = "servos"


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
    def __init__(self, server_is_local, server_ip, server_port, route):
        return
    
    def post(self, json_data):
        return
        
    def get(self):
        return
        
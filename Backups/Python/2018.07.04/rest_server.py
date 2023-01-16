#python3 /home/pi/wall-e/rest_server.py &

from flask import Flask, jsonify, request
from flask_restful import reqparse, abort, Api, Resource
from flask_cors import CORS
import json

REST_ROUTE_MODULE_NAME = "servos"
REST_ROUTE_SUB_MODULE = "1"
REST_PORT = 5000            #each Flask instance needs a different port

#https://httpstatuses.com
HTTP_STATUS_OK = 200
HTTP_STATUS_NO_CONTENT = 204
HTTP_STATUS_NOT_FOUND = 404
HTTP_STATUS_UNPROCESSABLE_ENTITY = 422

#set up command structure
MoveAbsolute = {}
MoveAbsolute["setPos"] = 0
MoveAbsolute["start"] = False

MoveStatus = {}
MoveStatus["moving"] = False
MoveStatus["standstill"] = False
MoveStatus["position"] = 0
MoveStatus["velocity"] = 0


#definition of REST service
class RESTservice_MoveAbsolute(Resource):
    def post(self):
        rxJsonData = request.get_json(force=True)
        #try update internal service data with data from REST request, not received item will keep their old value
        for dataItem in rxJsonData:
            if dataItem in MoveAbsolute:
                MoveAbsolute[dataItem] = rxJsonData[dataItem]
            else:
                errorMsg = 'ERROR: received data item <{0}> does not exist in service data dict'.format(dataItem)
                #print(errorMsg)
                return errorMsg, HTTP_STATUS_NOT_FOUND

        #print("Server - update of move absolute data: {0}".format(json.dumps(MoveAbsolute)))
        return HTTP_STATUS_NO_CONTENT
        #return "All ok", HTTP_STATUS_OK

    def get(self):
        #print("Server - get data: {0}".format(json.dumps(MoveAbsolute)))
        return json.dumps(MoveAbsolute), HTTP_STATUS_OK 


class RESTservice_ReadStatus(Resource):
    def get(self):
        return json.dumps(MoveStatus), HTTP_STATUS_OK 



#set up rest infrastructure for remote access
appRemoteHost = Flask(REST_ROUTE_MODULE_NAME)
CORS(appRemoteHost)
apiRemoteHost = Api(appRemoteHost)
#add services
apiRemoteHost.add_resource(RESTservice_MoveAbsolute, '/' + REST_ROUTE_MODULE_NAME + '/' + REST_ROUTE_SUB_MODULE + '/'  + 'MoveAbsolute')
apiRemoteHost.add_resource(RESTservice_ReadStatus, '/' + REST_ROUTE_MODULE_NAME + '/' + REST_ROUTE_SUB_MODULE + '/' + 'MoveStatus')
#start REST server for all connections (local host and remote)
appRemoteHost.run(debug=True, host='0.0.0.0', port=REST_PORT)    #netstat -lnt


#python3 /home/pi/wall-e/rest_client.py

#https://www.quora.com/What-is-the-way-to-send-a-JSON-object-via-a-POST-request-in-JavaScript-not-jQuery-or-Nodejs
import requests
import json

HTTP_STATUS_CLIENT_ERRORS = 400
HTTP_STATUS_BAD_REQUEST = 400

move_absolute_data = {}
move_absolute_data["setPos"] = 90
move_absolute_data["start"] = True

req = requests.post('http://127.0.0.1:5000/servos/1/MoveAbsolute', json=move_absolute_data)
if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
    print('Servo: error POST MoveAbsolute: {0} data: <{1}>'.format(req.status_code, req.text))


req = requests.get('http://127.0.0.1:5000/servos/1/MoveAbsolute')
if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
    print('Servo: GET MoveAbsolute: {0} data: <{1}>'.format(req.status_code, req.text))
else:
    print('Servo: received GET MoveAbsolute {0}'.format(json.loads(req.text)))

req = requests.get('http://127.0.0.1:5000/servos/1/MoveStatus')
if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
    print('Servo: GET MoveStatus: {0} data: <{1}>'.format(req.status_code, req.text))
else:
    print('Servo: received GET MoveAbsolute {0}'.format(json.loads(req.text)))

req = requests.get('http://127.0.0.1:5001/arms/1/MoveStatus')
if req.status_code >= HTTP_STATUS_CLIENT_ERRORS:
    print('Arms: GET MoveStatus: {0} data: <{1}>'.format(req.status_code, req.text))
else:
    print('Arm: received GET MoveAbsolute {0}'.format(json.loads(req.text)))

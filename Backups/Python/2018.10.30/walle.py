#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/walle.py

import asyncio
import time
from evdev import InputDevice, categorize, ecodes
import datetime, time

import helper.gamepad as gamepad
import helper.servo as servo
import helper.audio as audio

ASYNCIO_SLEEP_INTERVAL = 0.1

KEY_STICK_LEFT_UP_DOWN = "1"
KEY_STICK_LEFT_LEFT_RIGHT = "0"
KEY_STICK_RIGHT_UP_DOWN = "5"
KEY_STICK_RIGHT_LEFT_RIGHT = "2"
KEY_TRIGGER_LEFT = "312"
KEY_TRIGGER_RIGHT = "313"
KEY_ACTION_BUTTON_B = "305"
KEY_ACTION_BUTTON_Y = "308"


global gTrackDriveVelocity
global gTrackDriveDirectionAngle

DC_MOTOR_MAX_SPEED = 100
TRACK_DRIVE_MAX_VELOCITY = DC_MOTOR_MAX_SPEED * 0.5

async def gamepadKeyHandler():
    while True:
        await gamepad.processKeyEvents()           #is blocking but asyncio lets other task to be executed in parallel
        
async def keyActionHandler():
    global gTrackDriveVelocity
    global gTrackDriveDirectionAngle

    keyInterpreterLeftArm = gamepad.keyInterpreter(inMin=-32767, inMax=32768, outMin=10, outMax=150, keyCode=KEY_STICK_LEFT_UP_DOWN, selectorKeyCode=KEY_TRIGGER_LEFT, selectorKeyValue=1, newValueThreshold=1.0)
    keyInterpreterRightArm = gamepad.keyInterpreter(inMin=0, inMax=255, outMin=150, outMax=15, keyCode=KEY_STICK_RIGHT_UP_DOWN, selectorKeyCode=KEY_TRIGGER_RIGHT, selectorKeyValue=1, newValueThreshold=1.0)
    keyInterpreterHeadLeftRight = gamepad.keyInterpreter(inMin=0, inMax=255, outMin=120, outMax=60, keyCode=KEY_STICK_RIGHT_LEFT_RIGHT, selectorKeyCode=None, selectorKeyValue=None, newValueThreshold=1.0)
    keyInterpreterHeadUpDown = gamepad.keyInterpreter(inMin=0, inMax=255, outMin=110, outMax=50, keyCode=KEY_STICK_RIGHT_UP_DOWN, selectorKeyCode=None, selectorKeyValue=None, newValueThreshold=1.0)
    keyInterpreterTrackFwdBwd = gamepad.keyInterpreter(inMin=32767, inMax=-32768, outMin=-TRACK_DRIVE_MAX_VELOCITY, outMax=TRACK_DRIVE_MAX_VELOCITY, keyCode=KEY_STICK_LEFT_UP_DOWN, selectorKeyCode=KEY_TRIGGER_LEFT, selectorKeyValue=0, newValueThreshold=10.0)
    keyInterpreterTrackLeftRight = gamepad.keyInterpreter(inMin=-32768, inMax=32767, outMin=-20, outMax=20, keyCode=KEY_STICK_LEFT_LEFT_RIGHT, selectorKeyCode=None, selectorKeyValue=None, newValueThreshold=1.0)

    keyInterpreterHonk = gamepad.keyInterpreter(inMin=0, inMax=1, outMin=0, outMax=1, keyCode=KEY_ACTION_BUTTON_B, selectorKeyCode=None, selectorKeyValue=None, newValueThreshold=0)
    keyInterpreterText = gamepad.keyInterpreter(inMin=0, inMax=1, outMin=0, outMax=1, keyCode=KEY_ACTION_BUTTON_Y, selectorKeyCode=None, selectorKeyValue=None, newValueThreshold=0)


    while True:
        await asyncio.sleep(ASYNCIO_SLEEP_INTERVAL)
        #print("keyActionHandler() at: {0}".format(datetime.datetime.now().strftime("%S.%MSs")))
        
        #interpret keys
        #print(str())
        
        #left arm has a selector
        keyInterpreterLeftArm.update()
        if (keyInterpreterLeftArm.scaledValueChanged == True):
            keyInterpreterLeftArm.scaledValueChanged = False
            #print(keyInterpreterLeftArm.scaledValue)
            servo.moveAbsolute(keyInterpreterLeftArm.scaledValue, pwmChannel=6)
        
        #right arm has a selector
        keyInterpreterRightArm.update()
        if (keyInterpreterRightArm.scaledValueChanged == True):
            keyInterpreterRightArm.scaledValueChanged = False
            #print(keyInterpreterRightArm.scaledValue)
            servo.moveAbsolute(keyInterpreterRightArm.scaledValue, pwmChannel=7)

        #head left/right
        keyInterpreterHeadLeftRight.update()
        if (keyInterpreterHeadLeftRight.scaledValueChanged == True):
            keyInterpreterHeadLeftRight.scaledValueChanged = False
            #print(keyInterpreterHeadLeftRight.scaledValue)
            servo.moveAbsolute(keyInterpreterHeadLeftRight.scaledValue, pwmChannel=9)

        #head up/down
        keyInterpreterHeadUpDown.update()
        if (keyInterpreterHeadUpDown.scaledValueChanged == True):
            keyInterpreterHeadUpDown.scaledValueChanged = False
            #print(keyInterpreterHeadUpDown.scaledValue)
            #servo.moveAbsolute(keyInterpreterHeadUpDown.scaledValue, pwmChannel=8)
            """ Kopf Servo zittert!"""

        #track drive fwd/bwd
        keyInterpreterTrackFwdBwd.update()
        if (keyInterpreterTrackFwdBwd.scaledValueChanged == True):
            keyInterpreterTrackFwdBwd.scaledValueChanged = False
            #print(keyInterpreterTrackFwdBwd.scaledValue)
            gTrackDriveVelocity = keyInterpreterTrackFwdBwd.scaledValue

        #track drive left/right
        keyInterpreterTrackLeftRight.update()
        if (keyInterpreterTrackLeftRight.scaledValueChanged == True):
            keyInterpreterTrackLeftRight.scaledValueChanged = False
            #print(keyInterpreterTrackLeftRight.scaledValue)
            gTrackDriveDirectionAngle = keyInterpreterTrackLeftRight.scaledValue

        #honk 
        keyInterpreterHonk.update()
        if (keyInterpreterHonk.scaledValueChanged == True):
            keyInterpreterHonk.scaledValueChanged = False
            #print(keyInterpreterHonk.scaledValue)
            if (keyInterpreterHonk.scaledValue == 1):
                audio.playFile("wall-e/helper/sounds/honk.mp3")

        #Text-to-Speech 
        keyInterpreterText.update()
        if (keyInterpreterText.scaledValueChanged == True):
            keyInterpreterText.scaledValueChanged = False
            #print(keyInterpreterHonk.scaledValue)
            if (keyInterpreterText.scaledValue == 1):
                audio.textToSpeech("Please get out of my way!", "en")


async def trackDriveControl():
    global gTrackDriveVelocity
    global gTrackDriveDirectionAngle
    
    gTrackDriveVelocity = 0
    gTrackDriveDirectionAngle = 0
    
    while True:
        await asyncio.sleep(ASYNCIO_SLEEP_INTERVAL)
        #print("trackDriveControl() at: {0}".format(datetime.datetime.now().strftime("%S.%MSs")))

    
        leftDriveDirectionOffset = -gTrackDriveDirectionAngle
        rightDriveDirectionOffset = +gTrackDriveDirectionAngle

            
        #print("left: <{0}>; right: <{1}>".format(leftDriveDirectionOffset, rightDriveDirectionOffset))
        servo.moveDCmotor(gTrackDriveVelocity + leftDriveDirectionOffset, DC_MOTOR_MAX_SPEED, 0, 1, 2, False)
        servo.moveDCmotor(gTrackDriveVelocity + rightDriveDirectionOffset, DC_MOTOR_MAX_SPEED, 5, 3, 4, True)

        



try:
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(gamepadKeyHandler())
    asyncio.ensure_future(keyActionHandler())
    asyncio.ensure_future(trackDriveControl())
    loop.run_forever()
except Exception as e:
    print("WALL-E event loop failed: {0}".format(e))
finally:
    print("WALL-E event loop stopped")
    loop.close()


#python3 /home/pi/wall-e/walle.py





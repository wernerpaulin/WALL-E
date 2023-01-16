#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/walle.py

# Import the PCA9685 module.
import Adafruit_PCA9685
import helper.xycurvelin as xycurvelin

SERVOBOARD_PWM_PERIODE_TICKS = 4096
SERVOBOARD_PWM_PERIODE_SECONDS = 0.02      #s (50Hz)

SERVO_DUTY_CYCLE_MIN = 0.00083
SERVO_DUTY_CYCLE_MAX = 0.00230
SERVO_MIN_POSITION = 0     #degree
SERVO_MAX_POSITION = 180   #degree



# Initialize the PCA9685
global ServoDriveBoard
ServoDriveBoard = Adafruit_PCA9685.PCA9685(address=0x40)
ServoDriveBoard.set_pwm_freq(float(1.0 / SERVOBOARD_PWM_PERIODE_SECONDS)) 



def moveAbsolute(sSet, pwmChannel):
    dutyCycleLin = xycurvelin.chartLin()
    dutyCycleLin.addPointPair(float(SERVO_MIN_POSITION), float(SERVO_DUTY_CYCLE_MIN))
    dutyCycleLin.addPointPair(float(SERVO_MAX_POSITION), float(SERVO_DUTY_CYCLE_MAX))
    
    
    #limit moving range according to servo limits
    sSet = min(max(sSet, SERVO_MIN_POSITION), SERVO_MAX_POSITION)
    #convert set position[degree] to duty cycle duration
    dutyCycleDuration = dutyCycleLin.calcYfromX(sSet)
    
    #calculate number of duty cycle ticks
    dutyCycleTicksBegin = int(0) #always start cycle at beginning of period
    dutyCycleTicksEnd = max(min(int((SERVOBOARD_PWM_PERIODE_TICKS-1) / SERVOBOARD_PWM_PERIODE_SECONDS * dutyCycleDuration), SERVOBOARD_PWM_PERIODE_TICKS-1), 0)  #limit to 0..4096 to avoid damaging the servo

    #update PWM signal        
    ServoDriveBoard.set_pwm(int(pwmChannel), int(dutyCycleTicksBegin), int(dutyCycleTicksEnd))



def moveDCmotor(vSet, vMax, pwmChannel, directionChannel1, directionChannel2, reverseDirection):
    #limit moving range according to maximum speed in positive and negativ direction
    vSet = min(max(vSet, -vMax), vMax)

    #define motor direction depending on set speed
    if (vSet >= 0):
        motorDirection = 1
    else:
        motorDirection = -1 

    #invert motor direction if necessary to compensate wiring
    if (reverseDirection == True):
        motorDirection = motorDirection * -1

    #set direction using 2 channels which act inverted to each other: PWM always on or off - logic 0 or 1
    if (motorDirection >= 0):
        dutyCycleTicksBegin = int(0)
    else:
        dutyCycleTicksBegin = int(SERVOBOARD_PWM_PERIODE_TICKS)

    dutyCycleTicksEnd = int(0)
    ServoDriveBoard.set_pwm(int(directionChannel1), dutyCycleTicksBegin, dutyCycleTicksEnd)

    if (motorDirection >= 0):
        dutyCycleTicksBegin = int(SERVOBOARD_PWM_PERIODE_TICKS) #inverted to channel 1
    else:
        dutyCycleTicksBegin = int(0)

    dutyCycleTicksEnd = int(0)
    ServoDriveBoard.set_pwm(int(directionChannel2), dutyCycleTicksBegin, dutyCycleTicksEnd)

    
    #set speed which is proportional to duty cycle where maximum speed is equal to PWM always on (= max. periode ticks: 4096)
    #print(vSet)

    dutyCycleTicksBegin = int(0)
    dutyCycleTicksEnd = max(min(int(abs(vSet / vMax * (SERVOBOARD_PWM_PERIODE_TICKS-1))), SERVOBOARD_PWM_PERIODE_TICKS-1), 0)       #avoid coming close to periode ticks otherwise the servo boards freezes!
    #print(dutyCycleTicksEnd)
    #in case of an inverted direction the base of duty cycle is the maximum ticks
    #only for HG7881 necessary because this driver board has only one direction channel and needs an inverted PWM
    #if (motorDirection < 0):
    #    dutyCycleTicksEnd = SERVOBOARD_PWM_PERIODE_TICKS - int(dutyCycleTicksEnd) - 1
    #    dutyCycleTicksEnd = max(min(dutyCycleTicksEnd, SERVOBOARD_PWM_PERIODE_TICKS), 0)
    
    #print("ch: {0}; cycle: {1}".format(pwmChannel, dutyCycleTicksEnd))
    ServoDriveBoard.set_pwm(int(pwmChannel), int(dutyCycleTicksBegin), int(dutyCycleTicksEnd))
    return

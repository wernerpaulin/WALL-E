#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/walle.py


import Adafruit_ADS1x15

DISTANCE_SENSOR_ADC_I2C_ADR = 0x48
DISTANCE_SENSOR_ADC_I2C_BUSNUM = 1
DISTANCE_SENSOR_ADC_GAIN = 1


<pointpair adcValue="22000" distance="0.05" ></pointpair>
<pointpair adcValue="13700" distance="0.1" ></pointpair>
<pointpair adcValue="6000"  distance="0.2" ></pointpair>
<pointpair adcValue="3100"  distance="0.3" ></pointpair>
<pointpair adcValue="1500"  distance="0.4" ></pointpair>
<pointpair adcValue="100"   distance="0.5" ></pointpair>
<pointpair adcValue="-4000" distance="0.8" ></pointpair>

TrackDrives[trackDriveID].param.distanceSensorLin.addPointPair(float(pointPair.attrib['adcValue']), float(pointPair.attrib['distance']))        


def distanceToObstacle():


            self.distanceSensorADC = Adafruit_ADS1x15.ADS1115(address=DISTANCE_SENSOR_ADC_I2C_ADR, busnum=DISTANCE_SENSOR_ADC_I2C_BUSNUM)


                self.distanceToObstacle = self.param.distanceSensorLin.calcYfromX(self.distanceSensorADC.read_adc(int(self.param.distanceMeasurementADCchannel), gain=DISTANCE_SENSOR_ADC_GAIN))

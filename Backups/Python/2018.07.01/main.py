#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import datetime, time
import threading
import sys


import core.modules.manager

SYSTEM_TICK_CYCLE_TIME = 0.1    #seconds
SYSTEM_TICK_TOLERANCE  = 0.2   #seconds


def SystemTick():
    print("WALL-E started at %s"%(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    #initialize plug-in modules
    moduleManager = core.modules.manager.main()

    #initialize system tick    
    nextStartTime = time.time()
    while True:
        #################### BEGIN OF MODULE EXECUTION #################### 
        moduleManager.updateModules()
        ##################### END OF MODULE EXECUTION ##################### 

        #prepare next cycle
        nextStartTime = nextStartTime + SYSTEM_TICK_CYCLE_TIME

        #Statistics
        idleTime = nextStartTime - time.time() #this contains the sleep time shortened by the last cycle duration
        cpuLoad = 1.0 - (idleTime / SYSTEM_TICK_CYCLE_TIME)
        systemTickRunTime = SYSTEM_TICK_CYCLE_TIME - idleTime

        try:
            #plausibility check if time has been set backward
            if (nextStartTime - time.time() < SYSTEM_TICK_CYCLE_TIME):
                time.sleep(nextStartTime - time.time()) #sleep time by runtime of previous cycle
            else:
                print("Cycle time jitter due to time manipulation")
                nextStartTime = time.time() + SYSTEM_TICK_CYCLE_TIME    #reinitialize time measurement
                time.sleep(SYSTEM_TICK_CYCLE_TIME)
        #cycle time violation: skip compensation     
        except:                          
            print('Cycle time violation: %s'%(nextStartTime - time.time()))
            nextStartTime = time.time() + SYSTEM_TICK_CYCLE_TIME + SYSTEM_TICK_TOLERANCE    #reinitialize time measurement
            time.sleep(SYSTEM_TICK_CYCLE_TIME + SYSTEM_TICK_TOLERANCE) #allow temporarily a tolerance to overcome cycle time violation 



#start cyclic system
systemTickThread = threading.Thread(target=SystemTick)
systemTickThread.start()
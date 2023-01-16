#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/main.py

import os
import os.path
import sys

MODULES_ROOT_PATH = '/home/pi/wall-e/modules'

class main():
    "Module manager"
    def __init__(self):
        self.ModuleReferenceList = dict()
        self.ModuleRootPath = None
        
        #load all modules and initialize them
        self.createModuleList(MODULES_ROOT_PATH)
        self.initializeModules()
        
    
    #imports all modules found and creates a module information structure    
    def createModuleList(self, moduleRootPath):
        self.ModuleRootPath = moduleRootPath
        
        #go through all directories in modules folder and dynamically import all module.py files as modules
        for item in os.listdir(self.ModuleRootPath):
            path = os.path.join(self.ModuleRootPath, item)
            
            #ignore all files, just go for directories
            if os.path.isdir(path):
                pyPackageName = os.path.basename(item)
                pyModuleName = os.path.basename(item) + ".module"

                #ignore system modules e.g. __pycache__
                if "__" in pyPackageName:
                    continue
                
                #set up module information structure and assign function pointers to init and update function
                self.ModuleReferenceList[pyPackageName] = moduleInfo()
                self.ModuleReferenceList[pyPackageName].ModuleRef = __import__("modules.%s" % (pyModuleName), fromlist=["init", "update"])
                self.ModuleReferenceList[pyPackageName].InitFunctionRef = self.ModuleReferenceList[pyPackageName].ModuleRef.init
                self.ModuleReferenceList[pyPackageName].UpdateFunctionRef = self.ModuleReferenceList[pyPackageName].ModuleRef.update

    #initialize all registered modules
    def initializeModules(self):
        for module in self.ModuleReferenceList:
            try:
                self.ModuleReferenceList[module].InitFunctionRef()
            except Exception as e:
                print("Module manager: init function not defined: %s"%(e))

    #call call registered modules (cyclically by scheduler)
    def updateModules(self):
        for module in self.ModuleReferenceList:
            try:
                self.ModuleReferenceList[module].UpdateFunctionRef()
            except Exception as e:
                print("Module manager: update function not defined: %s"%(e))


class moduleInfo():
    "Contains all information for a certain module"
    def __init__(self):
        self.ModuleRef = None
        self.InitFunctionRef = None
        self.UpdateFunctionRef = None
        
    
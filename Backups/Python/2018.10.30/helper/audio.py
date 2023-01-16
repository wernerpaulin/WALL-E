#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#python3 /home/pi/wall-e/walle.py

from omxplayer.player import OMXPlayer
from pathlib import Path
from subprocess import call


def playFile(audioFile):
    try:
        player = OMXPlayer(Path(audioFile))
        #player.quit()
    except Exception as e:
        print("Playing file <{0}> failed: {1}".format(audioFile, e))
    
def textToSpeech(text, languageCode):
    try:
        text = str(text).replace(' ', '_')
        cmd= 'espeak -v' + languageCode + ' ' + text + ' &>/dev/null'       #redirects stdout and stderr to null device to surpress any output
        #Calls the Espeak TTS Engine to read aloud a Text
        #cmd="ls"
        call([cmd], shell=True)
    except Exception as e:
        print("Text-to-speech of text <{0}> failed: {1}".format(text, e))

    
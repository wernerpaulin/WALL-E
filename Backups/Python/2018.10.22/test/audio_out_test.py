#python3 /home/pi/wall-e/audio_out_test.py


from omxplayer.player import OMXPlayer
from pathlib import Path
from time import sleep

VIDEO_PATH = Path("/home/pi/wall-e/audio/honk.mp3")

#player = OMXPlayer(VIDEO_PATH)

#player.quit()




from num2words import num2words
from subprocess import call


cmd_beg= 'espeak '
cmd_end= ' | aplay /home/pi/Desktop/Text.wav  2>/dev/null' # To play back the stored .wav file and to dump the std errors to /dev/null
cmd_out= '--stdout > /home/pi/Desktop/Text.wav ' # To store the voice file

#text = input("Enter the Text: ")
#print(text)

text = "I will need to stop soon!"

#Replacing ' ' with '_' to identify words in the text entered
text = text.replace(' ', '_')

#Calls the Espeak TTS Engine to read aloud a Text
call([cmd_beg+cmd_out+text+cmd_end], shell=True)

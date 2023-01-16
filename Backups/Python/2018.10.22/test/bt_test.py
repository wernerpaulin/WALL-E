#python3 /home/pi/wall-e/test/bt_test.py
#import evdev
from evdev import InputDevice, categorize, ecodes
import time

#connect to controller
import subprocess
subprocess.call('~/wall-e/bt_autoconnect', shell=True)
#time.sleep(15)

from pathlib import Path
bt_device = Path("/dev/input/event1")
while bt_device.exists() == False:
    pass

print("Success!")
#time.sleep(2)


#creates object 'gamepad' to store the data
#you can call it whatever you like
gamepad = InputDevice('/dev/input/event1')

#prints out device info at start
#print(gamepad)

#evdev takes care of polling the controller in a loop
for event in gamepad.read_loop():
    #filters by event type
    if event.type == ecodes.EV_KEY:
        print(event)
    elif event.type == ecodes.EV_ABS:
        print(event)
    elif event.type != ecodes.EV_SYN:
        print(event)


"WEITER MACHEN"
"IMPLEMENTIERUNG"
#State in dem InputDevice mit try/except probiert wird. wenn except: connect state anspringen, dann warten für 2s dann reconnect

" 1. Integration in Module"
" 2. XML"

#https://github.com/spotify/linux/blob/master/include/linux/input.h
#define EV_SYN            0x00
#define EV_KEY            0x01
#define EV_REL            0x02
#define EV_ABS            0x03
#define EV_MSC            0x04
#define EV_SW            0x05
#define EV_LED            0x11
#define EV_SND            0x12
#define EV_REP            0x14
#define EV_FF            0x15
#define EV_PWR            0x16
#define EV_FF_STATUS        0x17
#define EV_MAX            0x1f
#define EV_CNT            (EV_MAX+1)
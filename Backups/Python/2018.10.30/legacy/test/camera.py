#python3 /home/pi/wall-e/test/camera.py

#https://projects.raspberrypi.org/en/projects/getting-started-with-picamera

from picamera import PiCamera
from time import sleep

camera = PiCamera()


#still pictures
#camera.start_preview(alpha=200)
#sleep(5)
#camera.capture('/home/pi/wall-e/test/image.jpg')
#camera.stop_preview()

#motion picture
camera.start_preview()
camera.start_recording('/home/pi/wall-e/test/video.h264')
sleep(10)
camera.stop_recording()
camera.stop_preview()

#shell: omxplayer video.h264
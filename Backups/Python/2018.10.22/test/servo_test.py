#python3 /home/pi/wall-e/servo_test.py
# Import the PCA9685 module.
import Adafruit_PCA9685



PWM_PERIODE_TICKS = 4096

# Initialize the PCA9685 using the i2c address and frequency of the first servo assuming all are the same (default: 0x40).
i2cAdr = 0x40
pwmPeriode = 0.02
pwmFrequency = float(1.0 / pwmPeriode)

ServoDriveBoard = Adafruit_PCA9685.PCA9685(address=i2cAdr)
ServoDriveBoard.set_pwm_freq(pwmFrequency)        #set period of 20ms = 50Hz    


#SG99
#0 = 210 (= 1ms)
#90 = 325 (= 1.5ms)
#180 = 435 (= 2ms)

#MG996R
#0 = 210 (= 1ms)
#90 = 325 (= 1.5ms)
#180 = 435 (= 2ms)
#ServoDriveBoard.set_pwm(0, 0, 300)
#ServoDriveBoard.set_pwm(1, 0, 0)


ServoDriveBoard.set_pwm(4, 0, 170)


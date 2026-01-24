#!/usr/bin/env/python
# File name   : move.py
# Website     : www.Adeept.com
# Author      : Adeept
# Date		  : 2025/03/12

import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor

class Adeept4WD:
    '''
Motor interface.
    M1  _____  M4
       |     |
       |     |
       |     |
    M2 |_____| M3
'''
    def __init__(self):
        self.freq = 50
        self.motor_in1_pins = [15, 12, 11, 8]
        self.motor_in2_pins = [14, 13, 10, 9]
        self.motor_directions = [-1, -1, -1, -1]

        self.motors=[]
        for in1, in2 in zip(self.motor_in1_pins, self.motor_in2_pins):
            motor = motor.DCMotor(pwm_motor.channels[in1], pwm_motor.channels[in2])
            motor.decay_mode = motor.SLOW_DECAY
            self.motors.append(motor)
        
        self.pwm_motor = PCA9685(busio.I2C(SCL, SDA), address=0x5f)
        self.pwm_motor.frequency = self.freq
        

    def map(self,x,in_min,in_max,out_min,out_max):
        return (x - in_min)/(in_max - in_min) *(out_max - out_min) +out_min

    def stop(self):
        for m in self.motors:
            m.throttle = 0
            

def motorStop():#Motor stops
    global motor1,motor2,motor3,motor4
    motor1.throttle = 0
    motor2.throttle = 0
    motor3.throttle = 0
    motor4.throttle = 0

def Motor(channel,direction,motor_speed):
    # channel,1~4:M1~M4
  if motor_speed > 100:
    motor_speed = 100
  elif motor_speed < 0:
    motor_speed = 0

  speed = map(motor_speed, 0, 100, 0, 1.0)

  pwm_motor.frequency = FREQ
  # Prevent the servo from affecting the frequency of the motor
  if direction == -1:
    speed = -speed
  if channel == 1:
    motor1.throttle = speed
  elif channel == 2:
    motor2.throttle = speed
  elif channel == 3:
    motor3.throttle = speed
  elif channel == 4:
    motor4.throttle = speed

def move(speed, direction, turn, radius=0.6):   # 0 < radius <= 1  
    #eg: move(100, 1, "no")--->forward
    #    move(100, 1, "left")---> left forward
    #speed:0~100. direction:1/-1. turn: "left", "right", "no".
    if speed == 0:
        motorStop() #all motor stop.
    else:
        if direction == 1: 			# forward
            if turn == 'rotate-left': 		# rotate left
                Motor(1, -M1_Direction, speed)
                Motor(2, -M2_Direction, speed)
                Motor(3, M3_Direction, speed)
                Motor(4, M4_Direction, speed)
            elif turn == 'rotate-right': 	# rotate right
                Motor(1, M1_Direction, speed)
                Motor(2, M2_Direction, speed)
                Motor(3, -M3_Direction, speed)
                Motor(4, -M4_Direction, speed)
            elif turn == 'forward-left': 	# left forward
                Motor(1, M1_Direction, 0)
                Motor(2, M2_Direction, speed)
                Motor(3, M3_Direction, 0)
                Motor(4, M4_Direction, speed)
            elif turn == 'forward-right': 	# right forward
                Motor(1, M1_Direction, speed)
                Motor(2, M2_Direction, 0)
                Motor(3, M3_Direction, speed)
                Motor(4, M4_Direction, 0)    
            elif turn == 'left': 	# left
                Motor(1, -M1_Direction, speed)
                Motor(2, M2_Direction, speed)
                Motor(3, -M3_Direction, speed)
                Motor(4, M4_Direction, speed)
            elif turn == 'right': 	# right
                Motor(1, M1_Direction, speed)
                Motor(2, -M2_Direction, speed)
                Motor(3, M3_Direction, speed)
                Motor(4, -M4_Direction, speed)            
            else: 					# forward  (mid)
                Motor(1, M1_Direction, speed)
                Motor(2, M2_Direction, speed)
                Motor(3, M3_Direction, speed)
                Motor(4, M4_Direction, speed)
        elif direction == -1: 		# backward
            if turn == 'backward-left': 	# left backward
                Motor(1, -M1_Direction, speed)
                Motor(2, -M2_Direction, 0)
                Motor(3, -M3_Direction, speed)
                Motor(4, -M4_Direction, 0)
            elif turn == 'backward-right': 	# right backward
                Motor(1, -M1_Direction, 0)
                Motor(2, -M2_Direction, speed)
                Motor(3, -M3_Direction, 0)
                Motor(4, -M4_Direction, speed)  
            else: 					# backward (mid)
                Motor(1, -M1_Direction, speed)
                Motor(2, -M2_Direction, speed)
                Motor(3, -M3_Direction, speed)
                Motor(4, -M4_Direction, speed)

def destroy():
    motorStop()
    pwm_motor.deinit()


if __name__ == '__main__':
    try:
        speed_set = 20
        setup()
        move(speed_set, -1, 'no', 0.8)
        time.sleep(3)
        motorStop()
        time.sleep(1)
        move(speed_set, 1, 'no', 0.8)
        time.sleep(3)
        motorStop()
    except KeyboardInterrupt:
        destroy()


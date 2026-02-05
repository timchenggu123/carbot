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
from lib import Motor

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

        pwm_motor = PCA9685(busio.I2C(SCL, SDA), address=0x5f)
        pwm_motor.frequency = self.freq

        self.motors=[]
        for in1, in2 in zip(self.motor_in1_pins, self.motor_in2_pins):
            motor = motor.DCMotor(pwm_motor.channels[in1], pwm_motor.channels[in2])
            motor.decay_mode = motor.SLOW_DECAY
            self.motors.append(motor)
        
        self.motor_speeds = [0, 0, 0, 0] #Integer values from -100 to 100
        
        # Legacy API for motor speed control
        self.dir_current_angle = 0
        self.left_motor_base_power = 0
        self.right_motor_base_power = 0
        self.left_motor_speed = 0
        self.right_motor_speed = 0

    #Common API
    def map(self,x,in_min,in_max,out_min,out_max):
        return (x - in_min)/(in_max - in_min) *(out_max - out_min) +out_min
    
    #Common API
    def stop(self):
        for m in self.motors:
            m.throttle = 0
        
    #Common API
    def set_cam_pan_angle(self, angle):
        pass  # Placeholder for camera pan control
    
    #Common API
    def set_cam_tilt_angle(self, angle):
        pass  # Placeholder for camera tilt control
    
    #Common API
    def update_motor(self):
    # channel,1~4:M1~M4
        for i in range(4):
            motor_speed = self.motor_speeds[i]
            if motor_speed > 100:
                motor_speed = 100
            elif motor_speed < -100:
                motor_speed = -100

            speed = map(motor_speed, 0, 100, 0, 1.0)
            self.motors[i].throttle = speed if motor_speed >= 0 else -speed 
        
    #Common API
    def turn(self, angle):
        if angle > 0:
            self.move(100, 'right')
        else:
            self.move(100, 'left')
    
    def move(self, speed, turn, radius=0.6):   # 0 < radius <= 1  
        #eg: move(100, 1, "no")--->forward
        #    move(100, 1, "left")---> left forward
        #speed:0~100. direction:1/-1. turn: "left", "right", "no".
                if turn == 'rotate-left': 		# rotate left
                    self.motor_speeds = [-speed, -speed, speed, speed]
                elif turn == 'rotate-right': 	# rotate right
                    self.motor_speeds = [speed, speed, -speed, -speed]
                elif turn == 'forward-left': 	# left forward
                    self.motor_speeds = [speed, 0, speed, 0]
                elif turn == 'forward-right': 	# right forward
                    self.motor_speeds = [0, speed, 0, speed]
                elif turn == 'left': 	# left
                    self.motor_speeds = [speed, -speed, speed, -speed]
                elif turn == 'right': 	# right
                    self.motor_speeds = [-speed, speed, -speed, speed]
                elif turn == "forward"					# forward  (mid)
                    self.motor_speeds = [speed, speed, speed, speed]
                elif turn == 'backward-left': 	# left backward
                    self.motor_speeds = [0, -speed, 0, -speed]
                elif turn == 'backward-right': 	# right backward
                    self.motor_speeds = [-speed, 0, -speed, 0]
                elif turn == "backward":				# backward (mid)
                    self.motor_speeds = [-speed, -speed, -speed, -speed]
                else: 
                    self.motor_speeds = [0, 0, 0, 0]

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


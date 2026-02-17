#!/usr/bin/env/python
# File name   : move.py
# Website     : www.Adeept.com
# Author      : Adeept
# Date		  : 2025/03/12

import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor, servo
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
        #Servo setup
        self.i2c = busio.I2C(SCL, SDA)
        self.pwm = PCA9685(self.i2c, address=0x5f)
        self.pwm.frequency = 50
        
        # Initialize pan and tilt servos (channels 0 and 1)
        self.servo_pan = servo.Servo(self.pwm.channels[0], min_pulse=500, max_pulse=2400, actuation_range=180)
        self.servo_tilt = servo.Servo(self.pwm.channels[1], min_pulse=500, max_pulse=2400, actuation_range=180)
        
        # Set servos to center position (90 degrees)
        self.servo_pan.angle = 90
        self.servo_tilt.angle = 90
        
        #Motor setup
        self.freq = 50
        self.motor_in1_pins = [15, 12, 11, 8]
        self.motor_in2_pins = [14, 13, 10, 9]
        self.motor_directions = [-1, -1, -1, -1]

        pwm_motor = self.pwm
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
    def stop(self):
        for m in self.motors:
            m.throttle = 0

    #Common API
    def set_cam_pan_angle(self, angle):
        """Set camera pan angle (0-180 degrees)"""
        if angle < 0:
            angle = 0
        elif angle > 180:
            angle = 180
        self.servo_pan.angle = angle
    
    #Common API
    def set_cam_tilt_angle(self, angle):
        """Set camera tilt angle (0-180 degrees)"""
        if angle < 0:
            angle = 0
        elif angle > 180:
            angle = 180
        self.servo_tilt.angle = angle
    
    def _map(self,x,in_min,in_max,out_min,out_max):
        return (x - in_min)/(in_max - in_min) *(out_max - out_min) +out_min

    #Common API
    def update_motor(self):
    # channel,1~4:M1~M4
        for i in range(4):
            motor_speed = self.motor_speeds[i]
            if motor_speed > 100:
                motor_speed = 100
            elif motor_speed < -100:
                motor_speed = -100

            speed = self._map(motor_speed, 0, 100, 0, 1.0)
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
                elif turn == "forward":					# forward  (mid)
                    self.motor_speeds = [speed, speed, speed, speed]
                elif turn == 'backward-left': 	# left backward
                    self.motor_speeds = [0, -speed, 0, -speed]
                elif turn == 'backward-right': 	# right backward
                    self.motor_speeds = [-speed, 0, -speed, 0]
                elif turn == "backward":				# backward (mid)
                    self.motor_speeds = [-speed, -speed, -speed, -speed]
                else: 
                    self.motor_speeds = [0, 0, 0, 0]
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from time import sleep


px = Picarx()

px.left_motor_base_power=50
px.right_motor_base_power=50

px.update_motor()

sleep(1)

px.stop()
sleep(1)
px.left_motor_base_power=-50
px.right_motor_base_power=-50

px.update_motor()

sleep(1)

px.stop()

for angle in range(-30, 31, 5):
    px.set_cam_pan_angle(angle)
    sleep(0.1)

for angle in range(30, 0, -5):
    px.set_cam_pan_angle(angle)
    sleep(0.1)

for angle in range(-30, 31, 5):
    px.set_cam_tilt_angle(angle)
    sleep(0.1)

for angle in range(30, 10, -5):
    px.set_cam_tilt_angle(angle)
    sleep(0.1)

px.set_cam_pan_angle(0)
px.set_cam_tilt_angle(0)

sleep(1)

px.activate_pump()

sleep(1.5)

px.deactivate_pump()

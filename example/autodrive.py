import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from autopilot.autopilot import Autopilot, SensorInputs
from sensors import lidar
from time import sleep

px = Picarx()

def main():
    ap = Autopilot()
    sin = SensorInputs()
    while True:
        sin.ultrasonic_distance = px.get_distance()
        sin.lidar_distance = lidar.read()[0] if lidar.read() else sin.lidar_distance

        cmd = ap.run(sin)
        speed, angle, pan, tilt= cmd.speed, cmd.angle, cmd.pan, cmd.tilt
        px.dir_current_angle = angle
        px.turn(0)
        px.left_motor_base_power = speed 
        px.right_motor_base_power = speed
        px.update_motor()

        px.set_cam_pan_angle(pan)
        px.set_cam_tilt_angle(tilt)
        # print(f"Speed: {speed}, Angle: {angle}, Distance: {sin.ultrasonic_distance}, State: {ap.state}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:    
        print("error:%s" % e)
    finally:
        px.stop()
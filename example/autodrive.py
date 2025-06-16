import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from autopilot.autopilot import Autopilot
from time import sleep

px = Picarx()

def main():
    ap = Autopilot()
    sensor_inputs = {
        'obstacle_distance': 0
    }
    while True: 
        sensor_inputs['obstacle_distance'] = px.get_distance()
        speed, angle = ap.run(sensor_inputs)
        px.dir_current_angle = angle
        px.turn(0)
        px.left_motor_base_power = speed 
        px.right_motor_base_power = speed
        px.update_motor()
        print(f"Speed: {speed}, Angle: {angle}, Distance: {sensor_inputs['obstacle_distance']}, State: {ap.state}")
        sleep(0.01)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:    
        print("error:%s" % e)
    finally:
        px.stop()
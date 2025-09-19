import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from autopilot.autopilot import Autopilot, SensorInputs
from sensors import lidar
from time import sleep

px = Picarx()

class AutoDrivePilot(Autopilot):

    def __init__(self, px):
        super().__init__()
        self.px = px
    
    def change_state_hook(self):
        self.px.stop()
        sleep(1.5)

    def scan_area(self):
        self.scan = self.pan_tilt_scan
        
        #First, turn 45 degrees to the right and scan)
        turn_func = lambda: self.init_turn(45)
        self.function_queue.append(turn_func)
        self.function_queue.append(self.pan_tilt_scan)
        turn_back_func = lambda: self.init_turn(-45)
        self.function_queue.append(turn_back_func)
        self.function_queue.append(self.cruise)
        return

    def run_step(self, sensor_inputs: SensorInputs = None):
        if sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        self.sensor_inputs = sensor_inputs
        print(f"State: {self.state}, Step: {self.step}")
        if self.state == self.STATE_READY:
            return self.function_queue.pop(0)()
        elif self.state == self.STATE_CRUISING:
            print(self.step)
            self.d_threshold = self.D_THRESHOLD_BASE
            self.scan = self.pan_tilt_scan
            if self.check_obstacle():
                return self.stop()

            # Scan area every 1 meter
            d = self.get_cruise_dist()
            print(f"Cruised {d} meters")
            if d > 1.0:
                self.log(f"Cruised {d} meters, scanning area")
                self.scan_area()
                return self.function_queue.pop(0)()
            return self.cruise()
        elif self.state == self.STATE_SCANNING:
            print(self.step)
            if self.step >= self.num_steps:
                self.step = 0
                return self.function_queue.pop(0)()  # Return the result of next function
            return self.scan()
        elif self.state == self.STATE_TURNING:
            print(self.step)
            if self.step >= self.num_steps:
                self.step = 0
                return self.function_queue.pop(0)()  # Return the result of next function
            return self.turn()
        elif self.state == self.STATE_BACKING:
            if not self.check_obstacle():
                self.step = 0
                return self.function_queue.pop(0)()  # Return the result of next function
            if self.step >= self.num_steps:
                self.step = 0
                return self.function_queue.pop(0)()  # Return the result of next function
            return self.back()
        elif self.state == self.STATE_STOPPED:
            return self.stop()

def main():
    ap = AutoDrivePilot(px)
    sin = SensorInputs()
    while True:
        # sin.ultrasonic_distance = px.get_distance() #New version of vehicle does not use this
        sin.ultrasonic_distance = 100  #Dummy value, not used
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
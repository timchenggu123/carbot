import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/.." + "/..")
from driver.adeept4wd import Adeept4WD
from autopilot.autopilot import Autopilot, SensorInputs, Command
from time import sleep

car = Adeept4WD()

class AutoDrivePilot(Autopilot):
    STATE_STRAFE_LEFT = 5
    STATE_STRAFE_RIGHT = 6
    STRAFE_STEPS = 20
    PARALLEL_SCAN_THRESHOLD = 80
    
    def parallel_scan(self, direction="r"):
        """
        Only apply to vehicles with Mechanum wheels that can strafe. Perform a quick scan by strafing left or right while measuring distance. This is faster than rotating in place and can be used as the first scan when an obstacle is detected.
        """
        if direction == "r":
            if self.state != self.STATE_STRAFE_RIGHT:
                self.change_state(self.STATE_STRAFE_RIGHT)
        else:
            if self.state != self.STATE_STRAFE_LEFT:
                self.change_state(self.STATE_STRAFE_LEFT)

        #Initialize scan if not already started
        if self.step == 0:
            #randomly choose -1 and 1 to start strafing left or right
            self.distances = []
            self.num_steps = self.STRAFE_STEPS
            
        #record distance
        self.distances.append(self.sensor_inputs.get_distance())

        # If the past 5 distances are all above the parallel scan threshold, we can assume the obstacle is not in front and skip the rest of the scan
        if len(self.distances) >= 5 and all(d > self.PARALLEL_SCAN_THRESHOLD for d in self.distances[-5:]):
            self.step = self.num_steps
            return Command(self.base_speed, 0, 0, 0, dir="right" if direction == "r" else "left")
        # Strafe and increase progress
        self.step += 1
        return Command(self.base_speed, 0, 0, 0, dir="right" if direction == "r" else "left")
        

    def run_step(self, sensor_inputs: SensorInputs = None):
        if sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        self.sensor_inputs = sensor_inputs

        if self.state == self.STATE_READY:
            return self.cruise()
        elif self.state == self.STATE_CRUISING:
            self.d_threshold = self.D_THRESHOLD_BASE
            self.scan = self.quick_rotate_scan
            if self.check_obstacle():
                return self.scan()
            return self.cruise()
        elif self.state == self.STATE_SCANNING:
            if self.step >= self.num_steps:
                self.step = 0
                if self.max_dist < self.d_threshold:
                    self.log(f"Obstacle too close, backing up, d_threshold: {self.d_threshold}, max_dist: {self.max_dist}")
                    self.increase_scan_threshold()
                    self.scan = self.full_rotate_scan
                    return self.back()
                else:
                    print("!!!!!!!!!!", self.target_angle)
                    if self.target_angle < 0: 
                        return self.parallel_scan("l")
                    else:
                        return self.parallel_scan("r")
            return self.scan()
        elif self.state == self.STATE_STRAFE_RIGHT:
            if self.step >= self.num_steps:
                self.step = 0
                return self.cruise()
            return self.parallel_scan("r")
        elif self.state == self.STATE_STRAFE_LEFT:
            if self.step >= self.num_steps:
                self.step = 0
                return self.cruise()
            return self.parallel_scan("l")
        elif self.state == self.STATE_TURNING:
            if self.step >= self.num_steps:
                self.step = 0
                return self.cruise()
            return self.turn()
        elif self.state == self.STATE_BACKING:
            if not self.check_obstacle():
                self.step = 0
                return self.scan()
            if self.step >= self.num_steps:
                self.step = 0
                return self.scan()
            return self.back()
        elif self.state == self.STATE_STOPPED:
            return self.stop()
        if sensor_inputs.ultrasonic_distance < self.D_THRESHOLD:
            self.scan()

def main():
    ap = AutoDrivePilot()
    sin = SensorInputs()
    while True:
        sin.ultrasonic_distance = car.get_distance() #New version of vehicle does not use this
        sin.lidar_distance = 100 #Placeholder until we have lidar working

        cmd = ap.run(sin)
        speed, angle, pan, tilt, dir= cmd.speed, cmd.angle, cmd.pan, cmd.tilt, cmd.dir
        print(cmd)
        if angle != 0:
            car.turn(angle)
        else:
            car.move(speed, dir)
        print(car.motor_speeds)
        car.update_motor()

        car.set_cam_pan_angle(pan)
        car.set_cam_tilt_angle(tilt)
        # print(f"Speed: {speed}, Angle: {angle}, Distance: {sin.ultrasonic_distance}, State: {ap.state}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:    
        print("error:%s" % e)
    finally:
        car.stop()
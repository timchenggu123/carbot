import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from autopilot.autopilot import Autopilot, SensorInputs, Command
from sensors import lidar
from time import sleep

px = Picarx()

class AutoDrivePilot(Autopilot):

    def run_step(self, sensor_inputs: SensorInputs = None):
        if sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        self.sensor_inputs = sensor_inputs

        if self.state == self.STATE_READY:
            return self.cruise()
        elif self.state == self.STATE_CRUISING:
            self.d_threshold = self.D_THRESHOLD_BASE
            self.scan = self.pan_tilt_scan
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
                    angle = self.target_angle if self.target_angle < 180 else self.target_angle - 360
                    return self.turn(angle)
            return self.scan()
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
    ap = Autopilot()
    sin = SensorInputs()
    while True:
        # sin.ultrasonic_distance = px.get_distance() #New version of vehicle does not use this
        sin.ultrasonic_distance = 100  #Dummy value, not used
        sin.lidar_distance = lidar.read()[0] if lidar.read() else sin.lidar_distance

        cmd = ap.run(sin)
        speed, angle, pan, tilt= cmd.speed, cmd.angle, cmd.pan, cmd.tilt
        px.turn(angle)
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
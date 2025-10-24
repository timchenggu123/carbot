import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from driver.picarx import Picarx
from autopilot.autopilot import Autopilot, SensorInputs, Command
from sensors import lidar
from sensors.camera import get_camera_instance
from time import sleep
from vision.fly.detect import FlyYOLO

px = Picarx()

class AutoDrivePilot(Autopilot):
    STATE_FLY_DETECTION=0
    STATE_SPRAY_PESTICIDE=1

    def __init__(self, px, fly_detect=None):
        super().__init__()
        #print all class attributes
        print(dir(self))
        self.px = px
        self.camera = get_camera_instance()
        self.model = fly_detect if fly_detect is not None else FlyYOLO()
        if self.camera is None:
            print("Failed to initialize camera. Exiting...")
            exit(1)
    
    def change_state_hook(self):
        #Sleep to reduce instantaneous motor current spike
        self.px.stop()
        sleep(1.5)

    
    def spray_pesticide(self):
        if self.state != self.STATE_SPRAY_PESTICIDE:
            self.change_state(self.STATE_SPRAY_PESTICIDE)

        # Initialize scan if not already started
        if self.step == 0:
            self.num_steps = 60
            self.px.activate_pump()
            self.log("Pesticide spray activated")

        pan = -30 + (self.step * 60 / self.num_steps)
        tilt = -10
        self.step += 1
        return Command(0, 0, pan, tilt)

    def fly_detect(self):
        if self.state != self.STATE_FLY_DETECTION:
            self.change_state(self.STATE_FLY_DETECTION)

        # Initialize scan if not already started
        if self.step == 0:
            self.num_steps = 60
            
        #Run fly detection model
        frame = self.camera.capture_frame()
        if frame is not None:
            detections = self.model.get_detection_centers(frame)
            if detections:
                #early exit if fly detected
                self.step=self.num_steps
                self.function_queue.insert(0, self.spray_pesticide)

        else:
            self.log("Failed to capture frame")

        pan = -30 + (self.step * 60 / self.num_steps)
        tilt = -10
        self.step += 1
        return Command(0, 0, pan, tilt)

    def scan_area(self):
        self.scan = self.pan_tilt_scan
        
        #First, turn 45 degrees to the right and scan)
        turn_func = lambda: self.init_turn(45)
        self.function_queue.append(turn_func)
        self.function_queue.append(self.fly_detect)
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
        elif self.state == self.STATE_FLY_DETECTION:
            print(self.step)
            if self.step >= self.num_steps:
                self.step = 0
                return self.function_queue.pop(0)()  # Return the result of next function
            return self.fly_detect()
        elif self.state == self.STATE_SPRAY_PESTICIDE:
            print(self.step)
            if self.step >= self.num_steps:
                self.step = 0
                self.px.deactivate_pump()
                self.log("Pesticide spray deactivated")
                return self.function_queue.pop(0)()  # Return the result of next function
            return self.spray_pesticide()
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
    model = FlyYOLO()
    ap = AutoDrivePilot(px, model)
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
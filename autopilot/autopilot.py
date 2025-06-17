import random, time
from dataclasses import dataclass

@dataclass
class Command:
    """
    Class to represent a command for the autopilot.
    This class can be extended to include more parameters as needed.
    """
    speed: int = 0
    angle: int = 0
    pan: int = 0
    tilt: int = 0

@dataclass
class SensorInputs:
    """
    Class to represent sensor inputs for the autopilot.
    This class can be extended to include more sensor data as needed.
    """
    ultrasonic_distance: float = float('inf')
    lidar_distance: float = float('inf')

class Autopilot:
    """
    Class for autopilot functionality.
    This class defines the basic structure and constants for an autopilot system.
    It should be agnostic to the specific vehicle implementation,
    allowing for different vehicles to inherit and implement the methods.
    """
    D_THREASHOLD_CRITICAL = 15 # Critical distance threshold for obstacle avoidance
    D_THRESHOLD_BASE = 30 # Distance threshold for obstacle avoidance
    D_THRESHOLD_INC = 20 # Distance threshold for backing
    FREQ = 0.5 # Frequency autopilot should run at

    # States for the autopilot
    STATE_READY = -1
    STATE_STOPPED = 0
    STATE_CRUISING = 1
    STATE_SCANNING = 2
    STATE_TURNING = 3
    STATE_BACKING = 4

    def __init__(self):
        self.state = self.STATE_READY
        self.d_threshold = self.D_THRESHOLD_BASE
        self.cur_speed = 0
        self.cur_angle = 0
        self.step = 0
        self.num_steps = 200  # Maximum progress for scanning or turning
        self.sensor_inputs = None
        self.dir = 0 
        self.base_speed = 50
        self.time_started = 0
        self.target_angle = 0

    def run(self, sensor_inputs: SensorInputs = None):
        time.sleep(self.FREQ)  # Simulate the frequency of the autopilot
        if sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        self.sensor_inputs = sensor_inputs
        if self.state == self.STATE_READY:
            return self.cruise()
        elif self.state == self.STATE_CRUISING:
            if self.check_obstacle():
                return self.scan()
            return self.cruise()
        elif self.state == self.STATE_SCANNING:
            self.d_threshold = self.D_THRESHOLD_BASE
            if self.step >= self.num_steps:
                self.step = 0
                if self.max_dist < self.d_threshold:
                    self.log("Obstacle too close, backing up")
                    self.increase_scan_threshold()
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
            return self.turn_step()
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
    
    def check_obstacle(self):
        """
        Check for obstacles using sensor inputs.
        Returns True if an obstacle is detected, False otherwise.
        """
        if self.sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        return self.sensor_inputs.lidar_distance < self.d_threshold
    
    def check_obstacle_critical(self):
        """
        Check for critical obstacles using sensor inputs.
        Returns True if a critical obstacle is detected, False otherwise.
        """
        if self.sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        return self.sensor_inputs.lidar_distance < self.D_THREASHOLD_CRITICAL

    def scan(self):
        """
        Perform a scan to detect potential path around obstacles.
        This method simulates scanning by increasing the progress.
        """
        # if self.check_obstacle_critical():
        #     self.log("Critical obstacle detected, backing up")
        #     return self.back()
        return self.rotate_scan()
    
    def rotate_scan(self):
        """
        Perfrom a scan to detect potential path around obstacles.
        This method simulates scanning by increasing the progress.
        Scanning starts by turing left, then all the way to the right, and then back to center. 
        """
        self.state = self.STATE_SCANNING
        #Initialize scan if not already started
        if self.step == 0:
            #randomly choose -1 and 1 to start turning left or right
            self.max_dist = -1
            self.num_steps = 3 // self.FREQ # 3 seconds of scanning
            
        # record larges distance
        if self.sensor_inputs.lidar_distance > self.max_dist:
            self.max_dist = self.sensor_inputs.lidar_distance
            self.target_angle = self.step * 360 / self.num_steps

        if self.max_dist > 100:
            self.step = self.num_steps
            return Command(0, 0, 0, 0)
        
        # Turn left and increase progress
        self.step += 1
        return Command(0, 30, 0, 0)
    
    def pan_tilt_scan(self):
        """
        Perfrom a scan to detect potential path around obstacles.
        This method simulates scanning by increasing the progress.
        Scanning starts by turing left, then all the way to the right, and then back to center. 
        """
        self.state = self.STATE_SCANNING
        # record largest distance
        if self.sensor_inputs.lidar_distance > self.max_dist:
            self.max_dist = self.sensor_inputs.lidar_distance
            self.max_progress = self.step

        #Early exit if max distance is too high
        if self.max_dist > 100:
            self.step = self.num_steps
            return Command(0, 0, 0, 0)

        pan = -30 + (self.step * 60 / self.num_steps)
        tilt = -15
        return Command(0, 0, pan, tilt)

    def increase_scan_threshold(self):
        self.d_threshold += self.D_THRESHOLD_INC
        return
    
    def turn(self, angle=30):
        #Picarx takes about 3 seconds to turn 360 degrees at 100% power
        self.state = self.STATE_TURNING
        self.dir = 1 if angle > 0 else -1
        angle = abs(angle)
        self.num_steps = int(3 / self.FREQ * angle / 360)  # Number of steps to complete the turn
        print("!!!!!!!!!! Set num steps to", self.num_steps, "for angle", angle)
        self.step = 0
        return self.turn_step()
        
    def turn_step(self):
        #Picarx takes about 3 seconds to turn 360 degrees at 100% power
        print("!!!!!!!!!!!!!!!!! Turning step:", self.step, "of", self.num_steps)
        self.step +=1
        return Command(0, 30 * self.dir, 0, 0)

    def stop(self):
        self.state = self.STATE_STOPPED
        return Command(0, 0, 0, 0)
    
    def back(self):
        self.state = self.STATE_BACKING
        self.step += 1
        return Command(-self.base_speed, 0, 0, 0)
    
    def cruise(self):
        if self.check_obstacle_critical():
            self.log("Critical obstacle detected, backing up")
            return self.back()
        self.state = self.STATE_CRUISING
        return Command(self.base_speed, 0, 0, 0)
    
    def log(self, message):
        """
        Log a message to the console or a file.
        This method can be overridden to change logging behavior.
        """
        print(f"[Autopilot] {message}")
    

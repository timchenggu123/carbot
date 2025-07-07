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
    camera_image: bytes = b''  # Placeholder for camera image data

class Autopilot:
    """
    Class for autopilot functionality.
    This class defines the basic structure and constants for an autopilot system.
    It should be agnostic to the specific vehicle implementation,
    allowing for different vehicles to inherit and implement the methods.
    """
    D_THREASHOLD_CRITICAL = 15 # Critical distance threshold for obstacle avoidance
    D_THRESHOLD_BASE =35 # Distance threshold for obstacle avoidance
    D_THRESHOLD_INC = 20 # Distance threshold for backing
    FREQ = 0.05 # Frequency autopilot should run at

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
        self.scan = self.pan_tilt_scan
        self.register_states() 
    
    def register_states(self):
        """
        Register a new state for the autopilot.
        This can be used to extend the autopilot with additional states.
        """
        val = 0
        for attr in dir(self):
            if attr.startswith('STATE_'):
                setattr(self, attr, val)
                val += 1
    
    def change_state(self, new_state, init_fun=None, *init_args):
        '''
        Call this function when you want to change the state of the autopilot.
        '''
        self.state = new_state
        self.step = 0  # Reset step when changing state
        self.log(f"State changed to {self.state}")
        if init_fun is not None:
            self.log(f"Running initialization function for state {self.state}")
            init_fun(self, *init_args)

    def sleep(self):
        time.sleep(self.FREQ)  # Sleep for the frequency duration

    def run(self, sensor_inputs: SensorInputs = None):
        """
        Run the autopilot logic based on the current state and sensor inputs.
        This method should be overridden by the vehicle implementation to provide specific behavior.
        """
        self.sleep()
        return self.run_step(sensor_inputs)

    def run_step(self, sensor_inputs: SensorInputs = None):
        #This can be overridden by the vehicle implementation to run the autopilot
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
    
    def quick_rotate_scan(self):
        """
        Perform a quick rotate scan from -30 to 30 degrees.
        """
        if self.state != self.STATE_SCANNING:
            self.change_state(self.STATE_SCANNING)
        #Initialize scan if not already started
        if self.step == 0:
            #randomly choose -1 and 1 to start turning left or right
            self.max_dist = -1
            self.num_steps = 3 * 60 / 360 // self.FREQ # scanning for 60 degrees
            
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
    

    def full_rotate_scan(self):
        """
        Perfrom a scan to detect potential path around obstacles.
        This method simulates scanning by increasing the progress.
        Scanning starts by turing left, then all the way to the right, and then back to center. 
        """
        if self.state != self.STATE_SCANNING:
            self.change_state(self.STATE_SCANNING)
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
        if self.state != self.STATE_SCANNING:
            self.change_state(self.STATE_SCANNING)

        # Initialize scan if not already started
        if self.step == 0:
            self.max_dist = -1
            self.num_steps = 60
            
        # Record largest distance
        if self.sensor_inputs.lidar_distance > self.max_dist:
            self.max_dist = self.sensor_inputs.lidar_distance
            self.target_angle = self.step - 30

        #Early exit if max distance is too high
        if self.max_dist > 100:
            self.step = self.num_steps
            return Command(0, 0, 0, 0)

        pan = -30 + (self.step * 60 / self.num_steps)
        tilt = -10
        self.step += 1
        return Command(0, 0, pan, tilt)

    def increase_scan_threshold(self):
        self.d_threshold += self.D_THRESHOLD_INC
        return
    
    def init_turn(self, angle):
        '''
        Initialize the turn state.
        '''
        self.dir = 1 if angle > 0 else -1
        angle = abs(angle)
        self.num_steps = int(3 / self.FREQ * angle / 360)  # Number of steps to complete the turn
        print("!!!!!!!!!! Set num steps to", self.num_steps, "for angle", angle)

    def turn(self, angle=30):
        #Picarx takes about 3 seconds to turn 360 degrees at 100% power
        if self.state != self.STATE_TURNING:
            self.change_state(self.STATE_TURNING, self.init_turn, angle)
        self.step +=1
        return Command(0, 30 * self.dir, 0, 0)
        
    def stop(self):
        if self.state != self.STATE_STOPPED:
            self.change_state(self.STATE_STOPPED)
        return Command(0, 0, 0, 0)
    
    def back(self):
        if self.state != self.STATE_BACKING:
            self.change_state(self.STATE_BACKING)
        self.step += 1
        return Command(-self.base_speed, 0, 0, 0)
    
    def cruise(self):
        if self.state != self.STATE_CRUISING:
            self.change_state(self.STATE_CRUISING)

        if self.check_obstacle_critical():
            self.log("Critical obstacle detected, backing up")
            return self.back()

        return Command(self.base_speed, -1, 0, -5)
    
    def log(self, message):
        """
        Log a message to the console or a file.
        This method can be overridden to change logging behavior.
        """
        print(f"[Autopilot] {message}")
    

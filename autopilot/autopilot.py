import random, time
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
    FREQ = 0.01 # Frequency autopilot should run at

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
        self.progress = 0
        self.progress_max = 200  # Maximum progress for scanning or turning
        self.sensor_inputs = None
        self.dir = 0 
        self.turn_stop = 0
        self.base_speed = 50

    def run(self, sensor_inputs):
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
            if self.progress >= self.progress_max:
                self.progress = 0
                if self.max_dist < self.d_threshold:
                    self.log("Obstacle too close, backing up")
                    self.increase_scan_threshold()
                    return self.back()
                else:
                    quarter = self.progress_max // 4
                    if self.max_progress < self.progress_max // 4:
                        self.turn_stop = self.max_progress
                        return self.turn(self.dir)
                    elif self.max_progress < self.progress_max // 2:
                        self.turn_stop = 2*quarter - self.max_progress
                        return self.turn(self.dir)
                    elif self.max_progress < self.progress_max // 4 * 3:
                        self.turn_stop = self.max_progress - 2*quarter
                        self.dir = -self.dir
                        return self.turn(self.dir)
                    else:
                        self.turn_stop = 4*quarter - self.max_progress
                        self.dir = -self.dir
                        return self.turn(self.dir)
            return self.scan()
        elif self.state == self.STATE_TURNING:
            if self.progress >= self.turn_stop:
                self.progress = 0
                return self.cruise()
            return self.turn(self.dir)
        elif self.state == self.STATE_BACKING:
            if not self.check_obstacle():
                self.progress = 0
                return self.scan()
            if self.progress >= self.progress_max:
                self.progress = 0
                return self.scan()
            return self.back()
        elif self.state == self.STATE_STOPPED:
            return self.stop()
        if sensor_inputs.get('obstacle_distance', float('inf')) < self.D_THRESHOLD:
            self.scan()
    
    def check_obstacle(self):
        """
        Check for obstacles using sensor inputs.
        Returns True if an obstacle is detected, False otherwise.
        """
        if self.sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        return self.sensor_inputs.get('obstacle_distance', float('inf')) < self.d_threshold
    
    def check_obstacle_critical(self):
        """
        Check for critical obstacles using sensor inputs.
        Returns True if a critical obstacle is detected, False otherwise.
        """
        if self.sensor_inputs is None:
            raise ValueError("Sensor inputs must be provided")
        return self.sensor_inputs.get('obstacle_distance', float('inf')) < self.D_THREASHOLD_CRITICAL

    def scan(self):
        """
        Perfrom a scan to detect potential path around obstacles.
        This method simulates scanning by increasing the progress.
        Scanning starts by turing left, then all the way to the right, and then back to center. 
        """
        self.state = self.STATE_SCANNING
        dir = 0
        if self.progress == 0:
            #randomly choose -1 and 1 to start turning left or right
            self.dir = random.choice([-1, 1])
            self.max_dist = -1
            self.max_progress = 0
            
        # record larges distance
        if self.sensor_inputs.get('obstacle_distance', float('inf')) > self.max_dist:
            self.max_dist = self.sensor_inputs.get('obstacle_distance', float('inf'))
            self.max_progress = self.progress

        if self.max_dist > 100:
            self.progress = self.progress_max
            return (0, 0)
        
        dir = self.dir
        mx = self.progress_max
        # Turn left and increase progress
        if self.progress < (mx//4):
            dir = dir
        elif self.progress < (mx//4*3):
            dir = -1*dir
        elif self.progress < mx:
            dir = dir
        self.progress += 1
        return (0, 30 * dir)

    def increase_scan_threshold(self):
        self.d_threshold += self.D_THRESHOLD_INC
        return
    
    def turn(self, direction):
        self.state = self.STATE_TURNING
        self.progress +=1
        return (0, 30 * direction)

    def stop(self):
        self.state = self.STATE_STOPPED
        return (0, 0)
    
    def back(self):
        self.state = self.STATE_BACKING
        self.progress += 1
        return (-self.base_speed, 0)
    
    def cruise(self):
        self.state = self.STATE_CRUISING
        return (self.base_speed, 0)
    
    def log(self, message):
        """
        Log a message to the console or a file.
        This method can be overridden to change logging behavior.
        """
        print(f"[Autopilot] {message}")
    

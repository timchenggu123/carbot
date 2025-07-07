import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from autopilot.autopilot import Autopilot, SensorInputs, Command
import asyncio

    
class FlyDetectionAutopilot(Autopilot):
    """
    Autopilot class for detecting and avoiding flies.
    This class extends the basic Autopilot functionality to include fly detection.
    """
    STATE_DETCTING_FLY = 5  # New state for fly detection

    def __init__(self):
        super().__init__()
        self.fly_detected = False
        self.register_states()

    def init_server(self):
        """
        Initialize the server for communication.
        """
        from comm import server
        server.start_server()

    def detect_fly(self, sensor_inputs):
        # Placeholder for fly detection logic
        # For example, using a camera or ultrasonic sensor to detect flies
        return False  # Replace with actual detection logic

    def run(self, sensor_inputs: SensorInputs) -> Command:
        self.sleep()

        if sensor_inputs is None:
            raise ValueError("Sensor inputs cannot be None")
        self.sensor_inputs = sensor_inputs

        if self.state == self.STATE_DETCTING_FLY:
            if self.detect_fly(sensor_inputs):
                self.fly_detected = True
                print("Fly detected! Taking evasive action.")
                # Implement evasive action logic here
                return Command(speed=0, angle=0, pan=0, tilt=0)

        return super().run(sensor_inputs)

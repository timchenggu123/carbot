#!/usr/bin/env python3
"""
Vehicle state logger utility for logging vehicle telemetry to CSV and saving detection images.
"""

import csv
import os
import time
from datetime import datetime
from pathlib import Path
import threading


class VehicleStateLogger:
    """Logs vehicle state to CSV file with configurable interval."""
    
    def __init__(self, log_dir=None, log_interval=1.0, mode="fly_hunt"):
        """
        Initialize the vehicle state logger.
        
        Args:
            log_dir (str): Directory to save logs. Defaults to home directory.
            log_interval (float): Seconds between log writes (0 = log every call).
            mode (str): Logger mode name (used for file naming).
        """
        if log_dir is None:
            log_dir = os.path.expanduser("~")
        
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_interval = log_interval
        self.mode = mode
        self.last_log_time = 0
        
        # Create CSV file path with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = os.path.join(log_dir, f"vehicle_state_{mode}_{timestamp}.csv")
        
        # Initialize CSV file with headers
        self.fieldnames = [
            "timestamp",
            "state",
            "speed",
            "cam_pan",
            "cam_tilt",
            "target_detected"
        ]
        
        self.csv_file = None
        self.csv_writer = None
        self._lock = threading.Lock()
        
        self._init_csv()
    
    def _init_csv(self):
        """Initialize the CSV file with headers."""
        try:
            self.csv_file = open(self.csv_filename, 'w', newline='')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames)
            self.csv_writer.writeheader()
            self.csv_file.flush()
        except Exception as e:
            print(f"Error initializing CSV: {e}")
    
    def log_state(self, state, speed=0, cam_pan=0, cam_tilt=0, target_detected=False):
        """
        Log vehicle state. Will only write if interval has elapsed.
        
        Args:
            state (str): Current vehicle state (e.g., "PATROL", "SCANNING").
            speed (int): Current vehicle speed.
            cam_pan (int): Camera pan angle in degrees.
            cam_tilt (int): Camera tilt angle in degrees.
            target_detected (bool): Whether a target is currently detected.
        """
        now = time.time()
        
        # Check if enough time has passed
        if self.log_interval > 0 and (now - self.last_log_time) < self.log_interval:
            return
        
        with self._lock:
            try:
                if self.csv_writer is None:
                    return
                
                timestamp = datetime.now().isoformat()
                
                row = {
                    "timestamp": timestamp,
                    "state": state,
                    "speed": speed,
                    "cam_pan": cam_pan,
                    "cam_tilt": cam_tilt,
                    "target_detected": int(target_detected)
                }
                
                self.csv_writer.writerow(row)
                self.csv_file.flush()
                self.last_log_time = now
                
            except Exception as e:
                print(f"Error logging state: {e}")
    
    def set_log_interval(self, interval):
        """
        Set the logging interval in seconds.
        
        Args:
            interval (float): Seconds between log writes. Set to 0 to log every call.
        """
        self.log_interval = interval
    
    def save_detection_image(self, frame_data, detection_index=None):
        """
        Save a camera frame as JPEG when a fly is detected.
        
        Args:
            frame_data (bytes): JPEG frame data.
            detection_index (int): Optional detection index for filename.
        
        Returns:
            str: Path to saved image, or None if save failed.
        """
        try:
            detection_dir = os.path.join(self.log_dir, f"fly_detections_{self.mode}")
            os.makedirs(detection_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            if detection_index is not None:
                filename = f"detection_{detection_index}_{timestamp}.jpg"
            else:
                filename = f"detection_{timestamp}.jpg"
            
            filepath = os.path.join(detection_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(frame_data)
            
            return filepath
        except Exception as e:
            print(f"Error saving detection image: {e}")
            return None
    
    def get_log_file_path(self):
        """Get the path to the current CSV log file."""
        return self.csv_filename
    
    def get_detection_dir(self):
        """Get the detection images directory path."""
        return os.path.join(self.log_dir, f"fly_detections_{self.mode}")
    
    def close(self):
        """Close the CSV file."""
        try:
            with self._lock:
                if self.csv_file is not None:
                    self.csv_file.close()
                    self.csv_file = None
                    self.csv_writer = None
        except Exception as e:
            print(f"Error closing CSV: {e}")
    
    def __del__(self):
        """Cleanup on deletion."""
        self.close()

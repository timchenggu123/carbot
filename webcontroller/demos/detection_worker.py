#This file is similar to camera, except it uses vision/fly/detect.py's batch detection functionality to detect flies and draw boxes around the frames, #then writes the processed frames to the FIFO.

import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
import time
from sensors.camera import Camera
from utils.io import AsyncFrameFIFO, AsyncTextFIFO
from vision.fly.detect import FlyYOLO
import numpy as np
from driver.adeept4wd import Adeept4WD

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'vision', 'models', 'best.pt')
FIFO_NAME = "detection"

# Optimization parameters
JPEG_QUALITY = 75  # Reduced from 95 for faster encoding/decoding
INFERENCE_SIZE = 416  # Reduced from 480x640 for faster inference
CONFIDENCE_THRESHOLD = 0.5  # Default confidence for detection
DETECTION_INTERVAL = 3  # Run detection every N frames (CPU optimization)

# Tracking parameters
PAN_SPEED = 1  # Pan speed in degrees
TILT_SPEED = 0.75  # Tilt speed in degrees

# Detection persistence parameters (temporal filtering)
MIN_DETECTION_FRAMES = 2  # Require detections to persist for N frames to reduce false positives
DETECTION_BUFFER_SIZE = 5  # History size for detection tracking

# Home position parameters
HOME_PAN = 0  # Home pan angle in degrees
HOME_TILT = 0  # Home tilt angle in degrees
IDLE_TIMEOUT = 5.0  # Seconds without detections before returning home
HOME_RETURN_SPEED = 3  # Speed to return home (degrees per frame)

class DetectionFilter:
    """Filter detections with temporal persistence to reduce false positives"""
    def __init__(self, min_frames=2, buffer_size=5):
        self.min_frames = min_frames
        self.buffer_size = buffer_size
        self.detection_history = []  # List of detection frames
    
    def update(self, detections):
        """
        Update filter with new detections.
        Returns stable detections that have persisted for min_frames.
        Returns list of (center_x, center_y, conf, x1, y1, x2, y2)
        """
        # Add current detections to history
        self.detection_history.append(detections)
        
        # Keep only recent history
        if len(self.detection_history) > self.buffer_size:
            self.detection_history.pop(0)
        
        # If not enough frames accumulated yet, return empty
        if len(self.detection_history) < self.min_frames:
            return []
        
        # Find detections that appear consistently across recent frames
        # Use simple heuristic: detections present in at least min_frames
        stable_detections = []
        
        # Get detections from the oldest retained frame
        reference_detections = self.detection_history[0]
        
        for ref_det in reference_detections:
            ref_x, ref_y = ref_det[0], ref_det[1]
            persistence_count = 1  # Already in reference frame
            
            # Check if similar detection appears in subsequent frames
            for frame_idx in range(1, len(self.detection_history)):
                current_frame_dets = self.detection_history[frame_idx]
                
                # Find closest detection in current frame
                for curr_det in current_frame_dets:
                    curr_x, curr_y = curr_det[0], curr_det[1]
                    distance = np.sqrt((ref_x - curr_x)**2 + (ref_y - curr_y)**2)
                    
                    # If close enough, count as persistence
                    if distance < 50:  # Max 50 pixel drift per frame
                        persistence_count += 1
                        break
            
            # If detection persisted long enough, include it
            if persistence_count >= self.min_frames:
                stable_detections.append(ref_det)
        
        return stable_detections

def calculate_distance_to_center(center_x, center_y, img_width, img_height):
    """Calculate Euclidean distance from center of frame"""
    frame_center_x = img_width / 2
    frame_center_y = img_height / 2
    return np.sqrt((center_x - frame_center_x)**2 + (center_y - frame_center_y)**2)

async def main():
    # Initialize async FIFO channels
    frame_fifo = AsyncFrameFIFO(FIFO_NAME)
    text_fifo = AsyncTextFIFO(FIFO_NAME)
    car = Adeept4WD()

    try:
        await text_fifo.write_line("Detection worker starting...")
        
        # Initialize camera
        cam = Camera()
        await text_fifo.write_line("Camera initialized successfully")
        
        # Initialize FlyYOLO model with optimizations
        fly_yolo = FlyYOLO(model_path=MODEL_PATH, use_fp16=False)  # CPU doesn't support FP16
        await text_fifo.write_line(f"FlyYOLO model loaded (Device: {fly_yolo.device}, FP16: {fly_yolo.use_fp16})")
        
        # Initialize filter for temporal persistence (reduces false positives)
        detection_filter = DetectionFilter(min_frames=MIN_DETECTION_FRAMES, buffer_size=DETECTION_BUFFER_SIZE)
        
        frame_count = 0
        start_time = time.time()
        last_detections = []  # Store last detection results
        current_pan = 0
        current_tilt = 0
        last_detection_time = time.time()  # Track when objects were last detected
        is_returning_home = False  # Track if camera is returning to home position
        
        while True:
            data = cam.capture_jpeg(quality=JPEG_QUALITY)  # Reduced quality for speed
            if data is None:
                await text_fifo.write_line("Warning: Failed to capture frame")
                await asyncio.sleep(0.02)
                continue
            
            # Convert JPEG to NumPy array for processing
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img_height, img_width = img.shape[:2]
            
            # Run detection only every N frames
            if frame_count % DETECTION_INTERVAL == 0:
                detections = fly_yolo.get_detection_centers(img, conf=CONFIDENCE_THRESHOLD, imgsz=INFERENCE_SIZE)
                last_detections = detections  # Store for next frames
            else:
                detections = last_detections  # Use cached detections
            
            # Filter detections with temporal persistence to reduce false positives
            stable_detections = detection_filter.update(detections)
            
            # Find closest detection to center
            closest_detection = None
            min_distance = float('inf')
            
            for detection in stable_detections:
                center_x, center_y = detection[0], detection[1]
                dist = calculate_distance_to_center(center_x, center_y, img_width, img_height)
                if dist < min_distance:
                    min_distance = dist
                    closest_detection = (center_x, center_y, detection[2], detection[3], detection[4], detection[5], detection[6], dist)
            
            # Draw stable detections
            for detection in stable_detections:
                center_x, center_y, conf, x1, y1, x2, y2 = detection
                is_closest = closest_detection and center_x == closest_detection[0] and center_y == closest_detection[1]
                color = (0, 0, 255) if is_closest else (0, 255, 0)  # Red for closest, green for others
                thickness = 3 if is_closest else 2
                
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
                cv2.circle(img, (int(center_x), int(center_y)), 5, color, -1)
                cv2.putText(img, f"Conf: {conf:.2f}", (int(x1), int(y1) - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Draw frame center crosshair
            cv2.line(img, (img_width // 2 - 20, img_height // 2), (img_width // 2 + 20, img_height // 2), (255, 255, 0), 1)
            cv2.line(img, (img_width // 2, img_height // 2 - 20), (img_width // 2, img_height // 2 + 20), (255, 255, 0), 1)
            
            # Auto-home camera to closest detection or return home if idle
            current_time = time.time()
            time_since_detection = current_time - last_detection_time
            
            if closest_detection:
                # Object detected - update detection time and track it
                last_detection_time = current_time
                is_returning_home = False
                
                center_x, center_y, conf, x1, y1, x2, y2, dist = closest_detection
                
                # Calculate pan/tilt adjustments
                frame_center_x = img_width / 2
                frame_center_y = img_height / 2
                
                pan_error = center_x - frame_center_x
                tilt_error = center_y - frame_center_y
                
                # Only adjust if error is significant (deadzone)
                deadzone = 30
                if abs(pan_error) > deadzone:
                    pan_adjustment = np.sign(pan_error) * PAN_SPEED
                    current_pan -= pan_adjustment
                    try:
                        car.set_cam_pan_angle(int(current_pan))
                    except:
                        pass  # Ignore errors if car control fails
                
                if abs(tilt_error) > deadzone:
                    tilt_adjustment = np.sign(tilt_error) * TILT_SPEED
                    current_tilt += tilt_adjustment
                    try:
                        car.set_cam_tilt_angle(int(current_tilt))
                    except:
                        pass
            
            elif time_since_detection > IDLE_TIMEOUT:
                # No objects detected for idle timeout period - return home
                is_returning_home = True
                
                # Move pan towards home
                car.set_cam_pan_angle(0)
                car.set_cam_tilt_angle(0)
                current_pan = 0
                current_tilt = 0
            
            # Encode back to JPEG with reduced quality
            _, processed_data = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            
            # Write processed frame to FIFO
            await frame_fifo.write_frame(processed_data.tobytes())
            
            frame_count += 1
            
            # Status update every 30 frames (~1 second at 30fps)
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                num_detections = len(stable_detections)
                status_mode = "RETURNING HOME" if is_returning_home else ("TRACKING" if closest_detection else "IDLE")
                await text_fifo.write_line(f"Status: {frame_count} frames, {fps:.1f} fps, {num_detections} stable detections, Mode: {status_mode} (Pan: {current_pan}°, Tilt: {current_tilt}°)")
            
            await asyncio.sleep(1/30)

    finally:
        try:
            cam.release()
            car.stop()
        except:
            pass
        await text_fifo.write_line("Detection worker stopped")
        frame_fifo.close()
        text_fifo.close()

if __name__ == "__main__":
    asyncio.run(main())

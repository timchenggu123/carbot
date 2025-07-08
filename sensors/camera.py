#!/usr/bin/env python3

import cv2
import base64
import numpy as np
from picamera2 import Picamera2

class Camera:
    def __init__(self, size=(320, 240)):
        """
        Initialize the Pi Camera
        
        Args:
            size (tuple): Camera resolution (width, height)
        """
        self.picam2 = Picamera2()
        self.size = size
        self.is_initialized = False
        
        print("Attempting to initialize Pi Camera...")
        
        # Configure camera
        config = self.picam2.create_preview_configuration(
            main={"size": self.size, "format": "RGB888"}
        )
        self.picam2.configure(config)
        
        try:
            self.picam2.start()
            print("Pi Camera initialized successfully")
            
            # Test capture
            test_frame = self.picam2.capture_array()
            if test_frame is not None:
                print(f"Camera test successful - frame shape: {test_frame.shape}")
                self.is_initialized = True
            else:
                print("Camera test failed - no frame captured")
                self.is_initialized = False
        except Exception as e:
            print(f"Failed to initialize Pi Camera: {e}")
            self.is_initialized = False
            raise e
    
    def capture_frame(self):
        """
        Capture a frame from the camera
        
        Returns:
            numpy.ndarray: BGR image frame or None if capture fails
        """
        if not self.is_initialized:
            return None
            
        try:
            # Capture frame from Pi Camera
            frame = self.picam2.capture_array()
            
            # picamera2 captures in RGB, convert to BGR for OpenCV compatibility
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def capture_frame_base64(self, resize_to=None, show_preview=False):
        """
        Capture a frame and return it as base64 encoded JPEG
        
        Args:
            resize_to (tuple): Optional resize dimensions (width, height)
            show_preview (bool): Whether to show preview window
            
        Returns:
            str: Base64 encoded JPEG image or None if capture fails
        """
        frame = self.capture_frame()
        if frame is None:
            return None
            
        try:
            # Resize frame if requested
            if resize_to:
                frame = cv2.resize(frame, resize_to)
            
            # Display the frame in a window (optional, for debugging)
            if show_preview:
                cv2.imshow("Camera Feed", frame)
                cv2.waitKey(1)
            
            # Encode frame as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                return None

            # Base64 encode the image
            b64jpeg = base64.b64encode(jpeg.tobytes()).decode('utf-8')
            return b64jpeg
        except Exception as e:
            print(f"Error processing frame: {e}")
            return None
    
    def close(self):
        """
        Stop the camera and cleanup
        """
        if self.is_initialized:
            self.picam2.stop()
            self.is_initialized = False
            print("Camera closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Global camera instance for backward compatibility
_camera_instance = None

def get_camera_instance():
    """
    Get the global camera instance, creating it if necessary
    
    Returns:
        Camera: The global camera instance
    """
    global _camera_instance
    if _camera_instance is None:
        _camera_instance = Camera()
    return _camera_instance

def capture_frame():
    """
    Capture a frame using the global camera instance
    
    Returns:
        numpy.ndarray: BGR image frame or None if capture fails
    """
    camera = get_camera_instance()
    return camera.capture_frame()

def capture_frame_base64(resize_to=(320, 240)):
    """
    Capture a frame and return it as base64 encoded JPEG using global camera instance
    
    Args:
        resize_to (tuple): Resize dimensions (width, height)
        show_preview (bool): Whether to show preview window
        
    Returns:
        str: Base64 encoded JPEG image or None if capture fails
    """
    camera = get_camera_instance()
    return camera.capture_frame_base64(resize_to=resize_to)

def decode_frame(self, base64_data):
    """
    Decode base64 encoded JPEG frame
    
    Args:
        base64_data (str): Base64 encoded JPEG image
        
    Returns:
        numpy.ndarray: Decoded BGR image or None if decode fails
    """
    try:
        # Decode base64 to bytes
        jpeg_bytes = base64.b64decode(base64_data)
        
        # Convert bytes to numpy array
        np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        
        # Decode JPEG to OpenCV image
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        return frame
    except Exception as e:
        print(f"Error decoding frame: {e}")
        return None

def close_camera():
    """
    Close the global camera instance
    """
    global _camera_instance
    if _camera_instance:
        _camera_instance.close()
        _camera_instance = None

#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import websockets
import cv2
import base64
import json
import numpy as np
import time
from datetime import datetime
from vision.fly.detect import get_detection_centers

class FrameReceiver:
    def __init__(self, server_host="localhost", server_port=8765):
        """
        Initialize the frame receiver
        
        Args:
            server_host (str): WebSocket server hostname/IP
            server_port (int): WebSocket server port
        """
        self.server_host = server_host
        self.server_port = server_port
        self.ws_url = f"ws://{server_host}:{server_port}"
        self.running = False
        
        # Stats tracking
        self.frame_count = 0
        self.start_time = None
        self.last_fps_time = None
        self.fps = 0.0
        
        # Frame processing optimization
        self.process_every_n_frames = 3  # Only run detection every 3rd frame
        self.last_detections = []  # Cache last detection results
        
        print(f"Frame Receiver initialized for {self.ws_url}")
    
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
    
    def calculate_fps(self):
        """Calculate and update FPS"""
        current_time = time.time()
        
        if self.start_time is None:
            self.start_time = current_time
            self.last_fps_time = current_time
        
        self.frame_count += 1
        
        # Update FPS every second
        if current_time - self.last_fps_time >= 1.0:
            elapsed = current_time - self.last_fps_time
            self.fps = self.frame_count / (current_time - self.start_time) if self.start_time else 0
            self.last_fps_time = current_time
            
        return self.fps
    
    def display_frame_with_info(self, frame, sensor_data):
        """
        Display frame with overlay information (optimized)
        
        Args:
            frame (numpy.ndarray): BGR image frame
            sensor_data (dict): Sensor data dictionary
        """
        if frame is None:
            return
            
        # Calculate FPS
        fps = self.calculate_fps()
        
        # Create a copy for drawing overlay
        display_frame = frame.copy()
        
        # Get frame dimensions
        height, width = display_frame.shape[:2]
        
        # Draw overlay information
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        
        # FPS
        fps_text = f"FPS: {fps:.1f}"
        cv2.putText(display_frame, fps_text, (10, 25), font, font_scale, (0, 255, 0), thickness)
        
        # Frame count
        frame_text = f"Frame: {self.frame_count}"
        cv2.putText(display_frame, frame_text, (10, 50), font, font_scale, (0, 255, 0), thickness)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(display_frame, timestamp, (10, 75), font, font_scale, (0, 255, 0), thickness)
        
        # Sensor data
        if sensor_data:
            y_offset = 100
            for key, value in sensor_data.items():
                if value is not None:
                    sensor_text = f"{key}: {value}"
                else:
                    sensor_text = f"{key}: N/A"
                cv2.putText(display_frame, sensor_text, (10, y_offset), font, font_scale, (255, 255, 0), thickness)
                y_offset += 25
        
        # Connection status
        status_text = f"Connected to: {self.server_host}:{self.server_port}"
        cv2.putText(display_frame, status_text, (10, height - 10), font, font_scale, (255, 255, 255), thickness)
        
        # Only run detection every N frames to reduce processing time
        if self.frame_count % self.process_every_n_frames == 0:
            self.last_detections = get_detection_centers(display_frame)
        
        # # Draw cached detections
        # for center_x, center_y, confidence, _, _, _, _ in self.last_detections:
        #     cv2.circle(display_frame, (center_x, center_y), 5, (0, 0, 255), -1)
        #     cv2.putText(display_frame, f"{confidence:.2f}", (center_x + 10, center_y), font, font_scale, (0, 0, 255), thickness)
        # cv2.imshow("Camera Feed - Receiver", display_frame)

        # Draw cached detection boxes
        for center_x, center_y, confidence, x1, y1, x2, y2 in self.last_detections:
            cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.circle(display_frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
            cv2.putText(display_frame, f"{confidence:.2f}", (int(center_x) + 10, int(center_y)), font, font_scale, (0, 0, 255), thickness)
        cv2.imshow("Camera Feed - Receiver", display_frame)
    
    async def receive_frames(self):
        """
        Main loop to receive and display frames with frame dropping
        """
        print(f"Connecting to {self.ws_url}...")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("Connected! Receiving frames...")
                self.running = True
                
                while self.running:
                    try:
                        # Clear the receive queue by getting all available messages
                        # and only processing the most recent one
                        latest_message = None
                        dropped_frames = 0
                        
                        # Non-blocking receive to clear queue
                        try:
                            while True:
                                message = await asyncio.wait_for(websocket.recv(), timeout=0.001)
                                if latest_message is not None:
                                    dropped_frames += 1
                                latest_message = message
                        except asyncio.TimeoutError:
                            # No more messages available
                            pass
                        
                        # If no new message, wait for one
                        if latest_message is None:
                            latest_message = await websocket.recv()
                        
                        # Show dropped frame count if any
                        if dropped_frames > 0:
                            print(f"Dropped {dropped_frames} frames")
                        
                        # Parse JSON data
                        data = json.loads(latest_message)
                        
                        # Extract camera and sensor data
                        camera_data = data.get("camera")
                        sensor_data = data.get("sensors", {})
                        
                        if camera_data:
                            # Decode and display frame
                            frame = self.decode_frame(camera_data)
                            if frame is not None:
                                self.display_frame_with_info(frame, sensor_data)
                                
                                # Check for 'q' key press to quit
                                key = cv2.waitKey(1) & 0xFF
                                if key == ord('q'):
                                    print("Quit key pressed. Stopping...")
                                    self.running = False
                                    break
                            else:
                                print("Failed to decode frame")
                        else:
                            print("No camera data in message")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed by server")
                        break
                    except json.JSONDecodeError as e:
                        print(f"Error parsing JSON: {e}")
                    except Exception as e:
                        print(f"Error processing frame: {e}")
                        
        except websockets.exceptions.ConnectionRefused:
            print(f"Could not connect to {self.ws_url}")
            print("Make sure the server is running!")
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.running = False
            cv2.destroyAllWindows()
            print("Receiver stopped")
    
    def stop(self):
        """Stop the receiver"""
        self.running = False

async def main():
    """
    Main function to run the receiver
    """
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WebSocket Camera Frame Receiver")
    parser.add_argument("--host", default="localhost", help="Server hostname/IP (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    args = parser.parse_args()
    
    # Create and run receiver
    receiver = FrameReceiver(server_host=args.host, server_port=args.port)
    
    print("=== WebSocket Camera Frame Receiver ===")
    print(f"Server: {args.host}:{args.port}")
    print("Press 'q' in the video window to quit")
    print("=" * 40)
    
    try:
        await receiver.receive_frames()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        receiver.stop()

if __name__ == "__main__":
    asyncio.run(main())


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
from sensors.camera import decode_frame
from comm.client import Client 
from vision.fly.detect import FlyYOLO

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
        self.client =  Client(server_host, server_port)
        
        # Stats tracking
        self.frame_count = 0
        self.start_time = None
        self.last_fps_time = None
        self.fps = 0.0
        
        # Frame processing optimization - async batch processing
        self.detector = FlyYOLO()  # Initialize the YOLO detector
        self.batch_size = 3  # Number of frames to collect before processing
        self.frame_queue = asyncio.Queue()  # Queue for frames to be processed
        self.result_queue = asyncio.Queue()  # Queue for detection results
        self.last_detections = []  # Cache last detection results for display
        self.processing_task = None  # Background processing task
        
        # Other settings
        self.show_info = True  # Toggle to show overlay info
        print(f"Frame Receiver initialized for {self.ws_url}")
    
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
        
        # Only run detection for display purposes (batch processing handles actual detection)
        if self.frame_count % self.batch_size == 0 or len(self.last_detections) == 0:
            self.last_detections = self.detector.get_detection_centers(display_frame)
        
        # Draw cached detection boxes
        for center_x, center_y, confidence, x1, y1, x2, y2 in self.last_detections:
            cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.circle(display_frame, (int(center_x), int(center_y)), 5, (0, 0, 255), -1)
            cv2.putText(display_frame, f"{confidence:.2f}", (int(center_x) + 10, int(center_y)), font, font_scale, (0, 0, 255), thickness)
        cv2.imshow("Camera Feed - Receiver", display_frame)
    
    async def background_batch_processor(self):
        """
        Background task that processes frames in batches
        """
        frame_batch = []
        frame_metadata_batch = []
        
        print("Background batch processor started...")
        
        while self.running:
            try:
                # Wait for frames to be added to the queue
                frame_data = await asyncio.wait_for(self.frame_queue.get(), timeout=1.0)
                
                if frame_data is None:  # Shutdown signal
                    print("Received shutdown signal in batch processor")
                    break
                    
                frame, metadata = frame_data
                frame_batch.append(frame)
                frame_metadata_batch.append(metadata)
                
                print(f"Added frame to batch. Current batch size: {len(frame_batch)}")
                
                # Process batch when it reaches the desired size
                if len(frame_batch) >= self.batch_size:
                    print(f"Processing batch of {len(frame_batch)} frames...")
                    
                    # Use batch detection method
                    batch_detections = self.detector.get_detection_centers_batch(frame_batch)
                    
                    print(f"Batch detection complete. Results: {len(batch_detections)} frame results")
                    
                    # Create results for each frame
                    for i, detections in enumerate(batch_detections):
                        metadata = frame_metadata_batch[i]
                        detection_coords = [[d[0], d[1]] for d in detections]
                        
                        result = {
                            "detections": detection_coords,
                            "frame_id": metadata.get("frame_id", -1),
                            "timestamp": metadata.get("timestamp", None),
                            "full_detections": detections  # Keep full detection info for display
                        }
                        
                        # Put result in the result queue
                        await self.result_queue.put(result)
                        print(f"Added result to queue. Detections: {len(detection_coords)}")
                    
                    # Clear the batch
                    frame_batch.clear()
                    frame_metadata_batch.clear()
                    
            except asyncio.TimeoutError:
                # No frames to process, continue
                continue
            except Exception as e:
                print(f"Error in batch processor: {e}")
                import traceback
                traceback.print_exc()
        
        print("Background batch processor ending...")
        
        # Process any remaining frames
        if frame_batch:
            print(f"Processing remaining {len(frame_batch)} frames...")
            batch_detections = self.detector.get_detection_centers_batch(frame_batch)
            
            for i, detections in enumerate(batch_detections):
                metadata = frame_metadata_batch[i]
                detection_coords = [[d[0], d[1]] for d in detections]
                
                result = {
                    "detections": detection_coords,
                    "frame_id": metadata.get("frame_id", -1),
                    "timestamp": metadata.get("timestamp", None),
                    "full_detections": detections
                }
                
                await self.result_queue.put(result)

    async def add_frame_to_batch(self, frame, data):
        """
        Add frame to processing queue (non-blocking)
        
        Args:
            frame (numpy.ndarray): BGR image frame
            data (dict): Frame data including frame_id and timestamp
        """
        metadata = {
            "frame_id": data.get("frame_id", -1),
            "timestamp": data.get("timestamp", None)
        }
        
        # Add frame to processing queue (non-blocking)
        try:
            self.frame_queue.put_nowait((frame.copy(), metadata))
            print(f"Added frame to queue. Queue size: {self.frame_queue.qsize()}")
        except asyncio.QueueFull:
            print("Frame queue is full, dropping frame")

    async def get_detection_result(self):
        """
        Get detection result from queue (non-blocking)
        
        Returns:
            dict or None: Detection result if available, None otherwise
        """
        try:
            result = self.result_queue.get_nowait()
            print(f"Retrieved result from queue. Result queue size: {self.result_queue.qsize()}")
            # Update last_detections for display
            if "full_detections" in result:
                self.last_detections = result["full_detections"]
            return result
        except asyncio.QueueEmpty:
            return None
    
    def detect_frame(self, frame):
        """
        Detect objects in the frame using YOLO
        
        Args:
            frame (numpy.ndarray): BGR image frame
        """
        # if self.frame_count % self.process_every_n_frames == 0:
        #     return self.detector.get_detection_centers(frame)
        # return []
        return self.detector.get_detection_centers(frame)
    
    async def receive_frames(self):
        """
        Main loop to receive and display frames with frame dropping
        """
        print(f"Connecting to {self.ws_url}...")
        
        try:
            await self.client.connect()
            print("Connected! Receiving frames...")
            self.running = True
            
            # Start background batch processing task
            self.processing_task = asyncio.create_task(self.background_batch_processor())
            
            while self.running:
                try:
                    # Clear the receive queue by getting all available messages
                    # and only processing the most recent one
                    latest_message = None
                    
                    # Non-blocking receive to clear queue
                    try:
                        while True:
                            message = await self.client.receive_data()
                            if message is not None:
                                latest_message = message
                            else:
                                break
                    except Exception:
                        # No more messages available
                        pass
                    
                    # If no new message, wait for one
                    if latest_message is None:
                        latest_message = await self.client.await_data()
                        if latest_message is None:
                            continue
                    
                    # Data is already parsed JSON from client
                    data = latest_message
                    
                    # Debug: Print received data structure
                    if data:
                        print(f"Received data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Extract camera and sensor data
                    camera_data = data.get("camera") if isinstance(data, dict) else None
                    sensor_data = data.get("sensors", {}) if isinstance(data, dict) else {}
                    
                    if camera_data:
                        # Decode and display frame
                        frame = decode_frame(camera_data)
                        if frame is not None:
                            if self.show_info: 
                                self.display_frame_with_info(frame, sensor_data)
                            
                            # Add frame to batch processing queue (non-blocking)
                            await self.add_frame_to_batch(frame, data)
                            
                            # Check for available detection results (non-blocking)
                            detection_result = await self.get_detection_result()
                            if detection_result and detection_result["detections"]:
                                #remove the full detections from the result
                                # and only send the coordinates
                                detection_result["full_detections"] = None
                                await self.client.send_data(detection_result)
                                
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
                    
        except websockets.exceptions.ConnectionRefused:
            print(f"Could not connect to {self.ws_url}")
            print("Make sure the server is running!")
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            self.running = False
            
            # Signal background processor to stop and wait for it
            if self.processing_task:
                await self.frame_queue.put(None)  # Shutdown signal
                try:
                    await asyncio.wait_for(self.processing_task, timeout=5.0)
                except asyncio.TimeoutError:
                    print("Background processor didn't stop in time, cancelling...")
                    self.processing_task.cancel()
            
            cv2.destroyAllWindows()
            print("Receiver stopped")
    
    def stop(self):
        """Stop the receiver and process any remaining frames"""
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

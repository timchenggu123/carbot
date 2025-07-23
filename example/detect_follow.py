import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from sensors.camera import get_camera_instance, close_camera
from comm.server import Server
import asyncio
import sensors.lidar as lidar
from driver.picarx import Picarx
import cv2
import time
from PIL import Image
import base64
import io
W = 640
H = 480
JPEG_QUALITY = 75  # Reduce from default 95
X_CENTER = W // 2
Y_CENTER = H // 2
def tracker(px, x, y, angles):
    '''
    Track the object using PicarX
    '''

    x_angle, y_angle = angles
    # Calculate the error from the center
    x_angle += (x-X_CENTER) / W * 35 * 0.6
    px.set_cam_pan_angle(x_angle)

    y_angle += -(y - Y_CENTER) / H * 35 * 0.6
    px.set_cam_tilt_angle(y_angle)

    angles[0] = x_angle
    angles[1] = y_angle
    
    print(f"Tracking object at ({x}, {y}) with angles ({x_angle}, {y_angle})")

# def process_frame(frame):
#     '''
#     Process the frame to increase contrast and brightness
#     '''
#     frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
#     frame = cv2.convertScaleAbs(frame, alpha=1.5, beta=0)
#     return frame

# def fast_encode_frame(frame, quality=JPEG_QUALITY):
#     """
#     Fast frame encoding with optimizations
#     """
#     # Convert to PIL Image

#     frame = cv2.resize(frame, (W, H))
#     if len(frame.shape) == 3:
#         pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#     else:
#         pil_img = Image.fromarray(frame)
    
#     # Encode to JPEG with specified quality
#     buffer = io.BytesIO()
#     pil_img.save(buffer, format='JPEG', quality=quality, optimize=True)
    
#     # Convert to base64
#     encoded_img = base64.b64encode(buffer.getvalue()).decode('utf-8')
#     return encoded_img

async def video_streamer(server):
    """
    Stream video frames using the server
    """
    camera = get_camera_instance()
    px = Picarx()
    if camera is None:
        print("Failed to initialize camera. Exiting...")
        return
    
    print("Camera initialized successfully")
    print("Starting video stream...")
    
    frame_count = 0

    print("Waiting for server to start...")
    while not server.is_running:
        await asyncio.sleep(0.1)
    angles = [0, 0]  # Initial angles for pan and tilt
    refresh_rate = 20  # Target refresh rate in FPS
    idle_count = 0
    try:
        while True:
            time_start = time.time()
            frame_count += 1
            
            # Capture camera frame (time this)
            # img = camera.capture_frame()
            # img = process_frame(img)
            # img = fast_encode_frame(img, quality=JPEG_QUALITY)
            img = camera.capture_frame_base64(resize_to=(W, H))
            
            if img is None:
                print("Failed to capture frame")
                await asyncio.sleep(0.1)
                continue
            
            # Get sensor data
            lidar_data = lidar.read()
            sensor_data = {
                "lidar_distance": lidar_data[0] if lidar_data else None
            }
            
            # Create data packet
            data = {
                "type": "video_stream",
                "camera": img,
                "sensors": sensor_data,
                "frame_id": frame_count,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send data through server (time this)
            await server.send_data(data)
            
            # Check for commands
            command = await server.receive_data()
            if command is not None:
                print(f"Received command: {command}")
                # Process the command here
                detections = command.get("detections", [])
                if detections:
                    idle_count = 0
                    x, y = detections[0][0], detections[0][1]
                    tracker(px, x, y, angles)
                else:
                    idle_count += 1
                    if idle_count > refresh_rate:  # If idle for too long, reset tracking
                        idle_count = 0
                        angles[0] = angles[1] = 0  # Reset angles if no detections
                        tracker(px, X_CENTER, Y_CENTER, angles)  # Reset tracking if no detections
            else:
                idle_count += 1
                if idle_count > refresh_rate:
                    idle_count = 0
                    angles[0] = angles[1] = 0  # Reset angles if no command
                    tracker(px, X_CENTER, Y_CENTER, angles)  # Reset tracking if no command
            # Control frame rate (~30 FPS)
            duration = time.time() - time_start
            sleep_time = max(0, (1 / refresh_rate) - duration)
            await asyncio.sleep(sleep_time)

    except Exception as e:
        print(f"Error in video streamer: {e}")
    finally:
        close_camera()
        print("Camera closed")

async def main():
    """
    Main function to run the video stream server.
    """
    print("Starting video streaming server...")
    
    # Create server (pure communication only)
    server = Server()
    
    # Create tasks for server and video streaming
    asyncio.create_task(server.start_server())
    streamer_task = asyncio.create_task(video_streamer(server))
    
    try:
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [streamer_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            
    except KeyboardInterrupt:
        print("Server stopped by user")
    finally:
        print("Video streaming stopped")

if __name__ == "__main__":
    asyncio.run(main())
        

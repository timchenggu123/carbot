import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))
import asyncio
import websockets
import cv2
import base64
import json
from sensors import lidar
from sensors.camera import get_camera_instance, close_camera

# Initialize camera
try:
    camera = get_camera_instance()
    print("Camera module loaded successfully")
except Exception as e:
    print(f"Failed to initialize camera: {e}")
    exit(1)

async def get_camera():
    """
    Get camera data as base64 encoded JPEG
    
    Returns:
        str: Base64 encoded JPEG or None if capture fails
    """
    return camera.capture_frame_base64(resize_to=(320, 240), show_preview=True)

async def get_sensor_data():
    lidar_distance = lidar.read()[0] if lidar.read() else None
    return {
        "lidar_distance": lidar_distance         # Example value
    }

async def send_frames(websocket):
    print(f"Client connected: {websocket.remote_address}")
    i = 0
    try:
        while True:
            i += 1
            
            cam_data = await get_camera()
            
            print(f"Frame {i}: Processing...")
            if cam_data is None:
                print("Failed to capture camera frame")
                continue

            sensor_data = await get_sensor_data()
            if sensor_data is None:
                print("Failed to get sensor data")
                continue

            data = {
                "camera": cam_data,
                "sensors": sensor_data
            }

            await websocket.send(json.dumps(data))
            print(f"Frame {i}: Sent successfully")

            await asyncio.sleep(0.03)  # ~30 FPS
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")
    except Exception as e:
        print(f"Error in send_frames: {e}")

async def main():
    async with websockets.serve(send_frames, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        print("Waiting for clients to connect...")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        close_camera()
        cv2.destroyAllWindows()

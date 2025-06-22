import asyncio
import websockets
import cv2
import base64
import json
from autobot.sensors import ultrasonic, lidar

# Open default camera
cap = cv2.VideoCapture(0)

async def get_camera():
    ret, frame = cap.read()
    if not ret:
        return None

    # Resize frame to reduce bandwidth (optional)
    frame = cv2.resize(frame, (320, 240))

    # Encode frame as JPEG
    ret, jpeg = cv2.imencode('.jpg', frame)
    if not ret:
        return None

    # Base64 encode the image
    b64jpeg = base64.b64encode(jpeg.tobytes()).decode('utf-8')
    return b64jpeg

async def get_sensor_data():
    lidar_distance = lidar.read()[0] if lidar.read() else None
    return {
        "lidar_distance": lidar_distance         # Example value
    }

async def send_frames(websocket):
    print(f"Client connected: {websocket.remote_address}")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            cam_data = await get_camera()
            if cam_data is None:
                continue

            sensor_data = await get_sensor_data()
            if sensor_data is None:
                continue

            data = {
                "camera": cam_data,
                "sensors": sensor_data
            }

            await websocket.send(json.dumps(data))

            await asyncio.sleep(0.03)  # ~30 FPS
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected: {websocket.remote_address}")

async def main():
    async with websockets.serve(send_frames, "0.0.0.0", 8765):
        print("WebSocket server started on ws://0.0.0.0:8765")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        cap.release()

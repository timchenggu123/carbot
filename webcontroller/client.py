# robot_client.py
import asyncio
import websockets
import threading
import cv2
import requests
import time
import json

SERVER_IP = "192.168.x.xxx"  # 👈 change this to your PC/server IP
VIDEO_URL = f"http://{SERVER_IP}:8001/static/video_feed"
CONTROL_WS = f"ws://{SERVER_IP}:8001/ws/robot"

def stream_video():
    """Stream MJPEG video to server via HTTP POST (Flask server part optional)."""
    cam = cv2.VideoCapture(0)
    _, frame = cam.read()
    while True:
        ret, frame = cam.read()
        if not ret:
            break
        _, jpeg = cv2.imencode('.jpg', frame)
        # Could POST to server or serve locally — for now we’ll serve locally
        # To keep it simple, robot just runs a local video feed on port 8000
    cam.release()

async def listen_for_commands():
    async with websockets.connect(CONTROL_WS) as ws:
        print("Connected to server control channel.")
        while True:
            data = await ws.recv()
            cmd = json.loads(data)
            print("Received command:", cmd)
            # Here you’d control motors, servos, etc.
            # Example:
            if cmd["cmd"] == "move":
                print("Moving", cmd["dir"])

def main():
    thread = threading.Thread(target=stream_video, daemon=True)
    thread.start()
    asyncio.run(listen_for_commands())

if __name__ == "__main__":
    main()
# camera_websocket_streamer.py

import asyncio
import websockets
import cv2
import base64

# Open default camera
cap = cv2.VideoCapture(0)

async def send_frames(websocket):
    print(f"Client connected: {websocket.remote_address}")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            # Resize frame to reduce bandwidth (optional)
            frame = cv2.resize(frame, (320, 240))

            # Encode frame as JPEG
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            # Base64 encode the image
            b64jpeg = base64.b64encode(jpeg.tobytes()).decode('utf-8')

            # Send over WebSocket
            await websocket.send(b64jpeg)

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

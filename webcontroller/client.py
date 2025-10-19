# robot_webrtc.py
import asyncio, json, cv2
from aiortc import RTCPeerConnection, VideoStreamTrack
from aiortc.contrib.signaling import BYE
from av import VideoFrame
import websockets

SERVER_IP = "192.168.x.xxx"  # 👈 change to your PC/server IP
SIGNALING_URL = f"ws://{SERVER_IP}:8001/ws/robot"

class CameraStream(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(3, 640)
        self.cap.set(4, 480)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        if not ret:
            await asyncio.sleep(0.05)
            return await self.recv()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        av_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        av_frame.pts = pts
        av_frame.time_base = time_base
        return av_frame

async def main():
    pc = RTCPeerConnection()
    pc.addTrack(CameraStream())

    async with websockets.connect(SIGNALING_URL) as ws:
        print("Connected to signaling server.")
        async for msg in ws:
            data = json.loads(msg)

            if "offer" in data:
                offer = data["offer"]
                await pc.setRemoteDescription(
                    {"sdp": offer["sdp"], "type": offer["type"]}
                )
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await ws.send(json.dumps({"answer": {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }}))

asyncio.run(main())

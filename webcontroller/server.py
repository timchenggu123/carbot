# server.py
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

# Serve static files (dashboard.html)
app.mount("/static", StaticFiles(directory="static"), name="static")

robot_ws = None
clients = set()

@app.get("/")
async def index():
    with open("static/dashboard.html") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws/robot")
async def robot_socket(websocket: WebSocket):
    global robot_ws
    await websocket.accept()
    robot_ws = websocket
    print("🤖 Robot connected")
    try:
        while True:
            await websocket.receive_text()  # Not used yet
    except WebSocketDisconnect:
        print("❌ Robot disconnected")
        robot_ws = None

@app.websocket("/ws/control")
async def control_socket(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    print("📱 Controller connected")
    try:
        while True:
            data = await websocket.receive_text()
            if robot_ws:
                await robot_ws.send_text(data)
    except WebSocketDisconnect:
        clients.remove(websocket)
        print("❌ Controller disconnected")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
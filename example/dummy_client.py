#!/usr/bin/env python3
import asyncio
import websockets
import json
import time

class DummyClient:
    def __init__(self, server_host="localhost", server_port=8765):
        self.server_host = server_host
        self.server_port = server_port
        self.ws_url = f"ws://{server_host}:{server_port}"
        self.running = False
        
    async def connect_and_test(self):
        """Connect to server and send test messages"""
        print(f"Connecting to {self.ws_url}...")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print("✅ Connected successfully!")
                self.running = True
                
                # Send a few test messages
                test_messages = [
                    {"type": "test", "message": "Hello from dummy client", "id": 1},
                    {"type": "detection", "detections": [{"x": 100, "y": 200, "confidence": 0.85}], "frame_id": 123},
                    {"type": "heartbeat", "timestamp": time.time()},
                    {"type": "control", "command": "move_forward", "speed": 50}
                ]
                
                for i, message in enumerate(test_messages):
                    try:
                        # Convert to JSON string
                        json_message = json.dumps(message)
                        print(f"📤 Sending message {i+1}: {json_message[:100]}...")
                        
                        # Send to server
                        await websocket.send(json_message)
                        print(f"✅ Message {i+1} sent successfully")
                        
                        # Wait a bit between messages
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        print(f"❌ Error sending message {i+1}: {e}")
                
                print("📤 All test messages sent. Keeping connection open for 10 seconds...")
                
                # Keep connection open and listen for any responses
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    print(f"📥 Received response: {response}")
                except asyncio.TimeoutError:
                    print("⏰ No response received within 10 seconds")
                
                print("🔚 Test complete")
                
        except websockets.exceptions.ConnectionRefused:
            print(f"❌ Could not connect to {self.ws_url}")
            print("Make sure the server is running!")
        except Exception as e:
            print(f"❌ Connection error: {e}")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dummy WebSocket Client for Testing")
    parser.add_argument("--host", default="localhost", help="Server hostname/IP (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="Server port (default: 8765)")
    args = parser.parse_args()
    
    print("=== Dummy WebSocket Client ===")
    print(f"Target: {args.host}:{args.port}")
    print("=" * 30)
    
    client = DummyClient(server_host=args.host, server_port=args.port)
    await client.connect_and_test()

if __name__ == "__main__":
    asyncio.run(main())
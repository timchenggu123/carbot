import asyncio
import websockets
import json

class Server():
    def __init__(self):
        """
        Minimal async server for sending/receiving single pieces of data
        """
        self.clients = set()
        self.message_queue = asyncio.Queue()
        self.is_running = False
        
    async def send_data(self, data):
        """
        Send a single piece of data to all connected clients
        
        Args:
            data: Data to send (will be JSON serialized)
        """
        if not self.clients:
            return
            
        message = json.dumps(data)
        
        # Send to all clients, remove disconnected ones
        disconnected = []
        for client in self.clients:
            try:
                await client.send(message)
            except:
                disconnected.append(client)
        
        for client in disconnected:
            self.clients.discard(client)
    
    async def receive_data(self):
        """Receive data from clients (non-blocking)"""
        try:
            data = await asyncio.wait_for(self.message_queue.get(), timeout=0.01)
            print(f"SERVER: Retrieved data from queue: {data}")
            return data
        except asyncio.TimeoutError:
            return None
    
    async def _handle_client(self, websocket):
        """Handle a single client connection"""
        self.clients.add(websocket)
        print(f"SERVER: Client connected: {websocket.remote_address}")
        print(f"SERVER: Total clients: {len(self.clients)}")
        self.is_running = True
        
        try:
            async for message in websocket:
                print(f"SERVER: Raw message received from {websocket.remote_address}: {message[:100]}...")
                try:
                    data = json.loads(message)
                    print(f"SERVER: Parsed JSON from {websocket.remote_address}: {data}")
                    await self.message_queue.put(data)
                    print(f"SERVER: Data added to queue, queue size: {self.message_queue.qsize()}")
                except json.JSONDecodeError as e:
                    print(f"SERVER: JSON decode error: {e}")
        except Exception as e:
            print(f"SERVER: Connection exception: {e}")
        finally:
            self.clients.discard(websocket)
            print(f"SERVER: Client disconnected: {websocket.remote_address}")
            print(f"SERVER: Remaining clients: {len(self.clients)}")
    
    
    async def start_server(self, host="0.0.0.0", port=8765):
        """
        Start WebSocket server in background (returns immediately)
        
        Args:
            host (str): Host to bind to
            port (int): Port to bind to
        """
        async def _server():
            async with websockets.serve(self._handle_client, host, port):
                await asyncio.Future()  # Run forever
        
        asyncio.create_task(_server())
        return f"ws://{host}:{port}"

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
        """
        Receive a single piece of data from any client
        
        Returns:
            Data received from client, or None if no data available
        """
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout=0.01)
        except asyncio.TimeoutError:
            return None
    
    async def _handle_client(self, websocket):
        """Handle a single client connection"""
        self.clients.add(websocket)
        print(f"Client connected: {websocket.remote_address}")
        self.is_running = True
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.message_queue.put(data)
                except json.JSONDecodeError:
                    pass  # Ignore invalid JSON
        except:
            pass  # Connection closed
        finally:
            self.clients.discard(websocket)
    
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

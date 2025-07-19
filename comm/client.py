#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import websockets
import time
import json

class Client:
    def __init__(self, server_host="localhost", server_port=8765):
        """
        Initialize the frame receiver
        
        Args:
            server_host (str): WebSocket server hostname/IP
            server_port (int): WebSoc
            
            ket server port
        """
        self.server_host = server_host
        self.server_port = server_port
        self.ws_url = f"ws://{server_host}:{server_port}"
        self.running = False
        
        self.ws = None  # WebSocket connection
        
        # Frame processing optimizatio
        print(f"Client initialized for {self.ws_url}")
    
    async def connect(self):
        """
        Connect to the WebSocket server
        """
        while True:
            try:
                self.ws = await websockets.connect(self.ws_url)
                self.running = True
                print(f"Connected to {self.ws_url}")
            except websockets.exceptions.ConnectionRefused:
                time.sleep(0.3)  # Wait before retrying
                continue
            except Exception as e:
                print(f"Connection error: {e}")
                return False
            return True

    async def receive_data(self, timeout=0.001):
        """
        Try to receive a single frame from the WebSocket server
        
        Returns:
            Parsed JSON data or None if no data/timeout
        """
        if self.ws is None or not self.running:
            return None
            
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            # Parse JSON if it's a string
            if isinstance(msg, str):
                return json.loads(msg)
            return msg
        except asyncio.TimeoutError:
            return None  # No data available
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.running = False
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None

    async def await_data(self):
        """
        Await data from the WebSocket server, blocking until data is received
        """
        if self.ws is None or not self.running:
            return None
            
        try:
            msg = await self.ws.recv()
            # Parse JSON if it's a string
            if isinstance(msg, str):
                return json.loads(msg)
            return msg
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.running = False
            return None
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None
    
    async def send_data(self, data):
        """
        Send data to the WebSocket server
        
        Args:
            data (str): Data to send
        """
        if self.ws is None or not self.running:
            print("WebSocket connection is not established")
            return
        
        try:
            data = json.dumps(data) if isinstance(data, dict) else data
            await self.ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.running = False
        except Exception as e:
            print(f"Error sending data: {e}")
                
    def stop(self):
        """Stop the receiver"""
        self.running = False


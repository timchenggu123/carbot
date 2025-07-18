#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import websockets
import time

class Client:
    def __init__(self, server_host="localhost", server_port=8765):
        """
        Initialize the frame receiver
        
        Args:
            server_host (str): WebSocket server hostname/IP
            server_port (int): WebSocket server port
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
     
        """
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
            return msg
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")

    async def await_data(self):
        """
        Await data from the WebSocket server, blocking until data is received
        """
        try:
            return await self.ws.recv()
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
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
            await self.ws.send(data)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
            self.running = False
        except Exception as e:
            print(f"Error sending data: {e}")
                
    def stop(self):
        """Stop the receiver"""
        self.running = False


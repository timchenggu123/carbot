#!/usr/bin/env python3
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
import websockets
import cv2
import base64
import json
import numpy as np
import time
from datetime import datetime
from autobot.sensors.camera import decode_frame
from vision.fly.detect import get_detection_centers

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
            msg = await asyncio.wait_for(self.ws.recv())
            return msg
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed by server")
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
        except Exception as e:
            print(f"Error processing frame: {e}")

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
                
    def stop(self):
        """Stop the receiver"""
        self.running = False


# ws_camera_subscriber.py

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import os

import asyncio
import websockets
import base64
import cv2
import numpy as np
import threading

class UpstreamClient(Node):
    def __init__(self):
        super().__init__('camera_ws_client')
        self.publisher_ = self.create_publisher(Image, 'camera/image_raw', 10)
        self.bridge = CvBridge()

        # WebSocket URL of host streamer (adjust IP as needed)
        host_ip = os.environ.get("HOST_IP", "localhost")
        self.ws_url = f'ws://{host_ip}:8765'  # or use your LAN IP
        self.get_logger().info(f'Connecting to {self.ws_url}')
        
        # Run the asyncio client in a thread
        threading.Thread(target=self.run_ws_client, daemon=True).start()

    def run_ws_client(self):
        asyncio.run(self.receive_loop())

    async def receive_loop(self):
        async with websockets.connect(self.ws_url) as websocket:
            while rclpy.ok():
                try:
                    msg = await websocket.recv()
                    camera_data = msg["camera"]
                    jpeg_bytes = base64.b64decode(camera_data)
                    np_arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
                    cv_image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                    ros_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8')
                    self.publisher_.publish(ros_msg)
                except Exception as e:
                    self.get_logger().error(f'WebSocket error: {e}')
                    break

def main(args=None):
    rclpy.init(args=args)
    node = UpstreamClient()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()

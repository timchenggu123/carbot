import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

from sensors.camera import get_camera_instance, close_camera
from comm.server import Server
import asyncio
import sensors.lidar as lidar

async def video_streamer(server):
    """
    Stream video frames using the server
    """
    camera = get_camera_instance()
    if camera is None:
        print("Failed to initialize camera. Exiting...")
        return
    
    print("Camera initialized successfully")
    print("Starting video stream...")
    
    frame_count = 0

    print("Waiting for server to start...")
    while not server.is_running:
        await asyncio.sleep(0.1)
    
    try:
        while True:
            frame_count += 1
            
            # Capture camera frame
            img = camera.capture_frame_base64(resize_to=(640, 480))
            if img is None:
                print("Failed to capture frame")
                await asyncio.sleep(0.1)
                continue
            
            # Get sensor data
            lidar_data = lidar.read()
            sensor_data = {
                "lidar_distance": lidar_data[0] if lidar_data else None
            }
            
            # Create data packet
            data = {
                "type": "video_stream",
                "camera": img,
                "sensors": sensor_data,
                "frame_id": frame_count,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Send data through server
            await server.send_data(data)
            
            # Check for commands
            command = await server.receive_data()
            if command is not None:
                print(f"Received command: {command}")
                # Process the command here
                
            # Control frame rate (~30 FPS)
            await asyncio.sleep(0.033)

    except Exception as e:
        print(f"Error in video streamer: {e}")
    finally:
        close_camera()
        print("Camera closed")

async def main():
    """
    Main function to run the video stream server.
    """
    print("Starting video streaming server...")
    
    # Create server (pure communication only)
    server = Server()
    
    # Create tasks for server and video streaming
    asyncio.create_task(server.start_server())
    streamer_task = asyncio.create_task(video_streamer(server))
    
    try:
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [streamer_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
            
    except KeyboardInterrupt:
        print("Server stopped by user")
    finally:
        print("Video streaming stopped")

if __name__ == "__main__":
    asyncio.run(main())
        

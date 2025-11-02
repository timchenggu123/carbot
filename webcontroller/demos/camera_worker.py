import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
import time
from sensors.camera import WebCamera
from utils.io import AsyncFrameFIFO, AsyncTextFIFO

async def main():
    # Initialize async FIFO channels
    frame_fifo = AsyncFrameFIFO("camera")
    # text_fifo = AsyncTextFIFO("camera")
    
    try:
        # await text_fifo.write_line("Camera worker starting...")
        
        # Initialize camera
        cam = WebCamera()
        # await text_fifo.write_line("WebCamera initialized successfully")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            data = cam.capture_jpeg(quality=95)
            if data is None:
                # await text_fifo.write_line("Warning: Failed to capture frame")
                await asyncio.sleep(0.05)
                continue
            
            # Write frame to FIFO
            await frame_fifo.write_frame(data)
            
            frame_count += 1
            
            # Status update every 30 frames (~1 second at 30fps)
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                # await text_fifo.write_line(f"Status: {frame_count} frames, {fps:.1f} fps, {len(data)} bytes")
            
            await asyncio.sleep(1/30)

    finally:
        try:
            cam.release()
        except:
            pass
        
        # await text_fifo.write_line("Camera worker stopped")
        frame_fifo.close()
        # text_fifo.close()

if __name__ == "__main__":
    asyncio.run(main())

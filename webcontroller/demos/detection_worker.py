#This file is similar to camera, except it uses vision/fly/detect.py's batch detection functionality to detect flies and draw boxes around the frames, #then writes the processed frames to the FIFO.

import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
import time
from sensors.camera import WebCamera
from utils.io import AsyncFrameFIFO, AsyncTextFIFO
from vision.fly.detect import FlyYOLO
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'vision', 'models', 'best.pt')
FIFO_NAME = "detection"

async def main():
    # Initialize async FIFO channels
    frame_fifo = AsyncFrameFIFO(FIFO_NAME)
    text_fifo = AsyncTextFIFO(FIFO_NAME)

    try:
        await text_fifo.write_line("Detection worker starting...")
        
        # Initialize camera
        cam = WebCamera()
        await text_fifo.write_line("WebCamera initialized successfully")
        
        # Initialize FlyYOLO model
        fly_yolo = FlyYOLO(model_path=MODEL_PATH)
        await text_fifo.write_line("FlyYOLO model loaded successfully")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            data = cam.capture_jpeg(quality=95)
            if data is None:
                await text_fifo.write_line("Warning: Failed to capture frame")
                await asyncio.sleep(0.02)
                continue
            
            # Convert JPEG to NumPy array for processing
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Get detections
            detections = fly_yolo.get_detection_centers(img)
            
            # Draw detections on image
            for (center_x, center_y, conf, x1, y1, x2, y2) in detections:
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.circle(img, (center_x, center_y), 3, (0, 0, 255), -1)
            
            # Encode back to JPEG
            _, processed_data = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            
            # Write processed frame to FIFO
            await frame_fifo.write_frame(processed_data.tobytes())
            
            frame_count += 1
            
            # Status update every 30 frames (~1 second at 30fps)
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                await text_fifo.write_line(f"Status: {frame_count} frames processed, {fps:.1f} fps")
            
            await asyncio.sleep(1/30)

    finally:
        try:
            cam.release()
        except:
            pass
        await text_fifo.write_line("Camera worker stopped")
        frame_fifo.close()
        text_fifo.close()

if __name__ == "__main__":
    asyncio.run(main())
              
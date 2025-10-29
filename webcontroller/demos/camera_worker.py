import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import struct
import time
from sensors.camera import Camera

def main():
    cam = Camera()
    while True:
        data = cam.capture_jpeg()
        if data is None:
            time.sleep(0.05)
            continue
        # Write frame length as 4 bytes (big-endian) followed by frame
        sys.stdout.buffer.write(struct.pack('>I', len(data)))
        sys.stdout.buffer.write(data)
        sys.stdout.flush()
        time.sleep(1/30)

if __name__ == "__main__":
    main()

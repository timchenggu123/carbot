import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
from sensors.camera import get_camera_instance, close_camera
from vision.fly.detect import FlyYOLO

def main():
    camera = get_camera_instance()
    if camera is None:
        print("Failed to initialize camera. Exiting...")
        return
    
    print("Camera initialized successfully")
    print("Starting fly detection...")

    model = FlyYOLO()

    try:
        while True:
            frame = camera.capture_frame()
            if frame is None:
                print("Failed to capture frame")
                continue

            detections = model.get_detection_centers(frame)
            if detections:
                for det in detections:
                    print(f"Detected fly at ({det[0]}, {det[1]}) with confidence {det[2]:.2f}")
            else:
                print("No flies detected")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        close_camera()
        print("Camera closed")

    

if __name__ == "__main__":
    main()
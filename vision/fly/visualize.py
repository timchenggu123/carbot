from ultralytics import YOLO
import cv2
import os

base_path = os.path.dirname(os.path.abspath(__file__))
# Load your trained model
model = YOLO(os.path.join(base_path, "runs/detect/yolov8n_fly2/weights/best.pt"))

# Path to test image(s)
# image_path = "data/test/images/20200727_164747_jpg.rf.3f46f39723633b4a891c82e9868cb81c.jpg"  # or a list of image paths
# image_path = "data/test/images/20200727_164747_jpg.rf.db433ed00bc03e98f7e06bae4ec0da37.jpg"
# image_path = "data/test/images/QJKRFAQ8EOLA_jpg.rf.075558446f29616ac826a8e168ef6331.jpg"
# image_path = "data/test/images/N1QQBA6U4DTY_jpg.rf.7154a88751675df00cd1afa7f44f5eb2.jpg"
image_path = f"data/test/images/RD2WCCO2EX7T_jpg.rf.373e2dd50664bbb5804f8cd2c0380144.jpg"

image_path = os.path.join(base_path, image_path)
# Run prediction
results = model(image_path, conf=0.15, iou=0.5, max_det=100, save=False)

# Visualize with OpenCV
for r in results:
    img = r.plot()  # draws boxes on image (returns a NumPy array)
    cv2.imshow("Detection", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
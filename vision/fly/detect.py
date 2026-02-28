from ultralytics import YOLO
import cv2
import os
import torch
import numpy as np

class FlyYOLO():
    def __init__(self, model_path=None, device=None, use_fp16=True):
        """
        Initialize the YOLO model for object detection.
        
        Args:
            model_path (str): Path to the YOLO model weights. If None, uses default path.
            device (str): Device to use for inference ('cuda', 'cpu', or None for auto). Default: auto-detect GPU.
            use_fp16 (bool): Enable half-precision (FP16) inference for faster performance. Default: True.
        """
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Load your trained model
        if model_path is None:
            model_path = os.path.join(base_path, "model/best.pt")
        
        # Auto-detect device if not specified
        if device is None:
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.model = YOLO(model_path)
        self.device = device
        self.use_fp16 = use_fp16 and device == 'cuda'  # FP16 only works on CUDA
        
        # Warm up the model with a dummy inference
        try:
            dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
            self.model(dummy_img, conf=0.5, device=self.device, half=self.use_fp16, imgsz=416, verbose=False)
        except Exception as e:
            print(f"Warning: Model warmup failed: {e}. Continuing anyway...")

    def get_detection_centers(self, image, conf=0.5, imgsz=416):
        """
        Detect objects and return center coordinates ranked by confidence.
        
        Args:
            image: Input image (NumPy array)
            conf (float): Confidence threshold. Default: 0.5
            imgsz (int): Inference image size. Smaller = faster. Default: 416
            
        Returns:
            List of tuples: [(x, y, confidence, x1, y1, x2, y2), ...] sorted by confidence (highest first)
        """
        
        # Run prediction with optimizations
        results = self.model(image, conf=conf, iou=0.45, max_det=30, device=self.device, 
                            half=self.use_fp16, imgsz=imgsz, verbose=False)
        
        # Extract center coordinates and confidence scores
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Get bounding box coordinates (x1, y1, x2, y2)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Calculate center coordinates
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # Get confidence score
                    confidence = float(box.conf[0].cpu().numpy())
                    
                    detections.append((center_x, center_y, confidence, x1, y1, x2, y2))
        
        # Sort by confidence (highest first)
        detections.sort(key=lambda x: x[2], reverse=True)
        
        return detections

    def get_detection_centers_batch(self, images, conf=0.5, imgsz=416):
        """
        Detect objects in a batch of images and return center coordinates ranked by confidence.
        
        Args:
            images (list): List of images to process
            conf (float): Confidence threshold. Default: 0.5
            imgsz (int): Inference image size. Smaller = faster. Default: 416
            
        Returns:
            List of lists: [[(x, y, confidence, x1, y1, x2, y2), ...], ...] for each image
        """
        if not images:
            return []
        
        # Run prediction on batch with optimizations
        results = self.model(images, conf=conf, iou=0.45, max_det=30, device=self.device,
                            half=self.use_fp16, imgsz=imgsz, verbose=False)
        
        batch_detections = []
        for r in results:
            detections = []
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Get bounding box coordinates (x1, y1, x2, y2)
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    
                    # Calculate center coordinates
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # Get confidence score
                    confidence = float(box.conf[0].cpu().numpy())
                    
                    detections.append((center_x, center_y, confidence, x1, y1, x2, y2))
            
            # Sort by confidence (highest first)
            detections.sort(key=lambda x: x[2], reverse=True)
            batch_detections.append(detections)
        
        return batch_detections

    def visualize_detections(self, image_path, model_path=None):
        """
        Visualize detections with OpenCV (original functionality).
        """
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # Load your trained model
        if model_path is None:
            model_path = os.path.join(base_path, "runs/detect/yolov8n_fly2/weights/best.pt")
        model = YOLO(model_path)
        
        # Ensure image path is absolute
        if not os.path.isabs(image_path):
            image_path = os.path.join(base_path, image_path)
        
        # Run prediction
        results = model(image_path, conf=0.15, iou=0.5, max_det=100, save=False)
        
        # Visualize with OpenCV
        for r in results:
            img = r.plot()  # draws boxes on image (returns a NumPy array)
            cv2.imshow("Detection", img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

# Example usage
if __name__ == "__main__":
    image_path = "data/test/images/RD2WCCO2EX7T_jpg.rf.373e2dd50664bbb5804f8cd2c0380144.jpg"
    
    fly_yolo = FlyYOLO()
    # Get detection centers ranked by confidence
    centers = fly_yolo.get_detection_centers(image_path)
    
    print(f"Found {len(centers)} detections:")
    for i, (x, y, conf) in enumerate(centers):
        print(f"  {i+1}. Center: ({x}, {y}), Confidence: {conf:.3f}")
    
    # Optionally visualize
    fly_yolo.visualize_detections(image_path)

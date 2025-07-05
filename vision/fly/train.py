from ultralytics import YOLO

# Load a base model (YOLOv8n is lightweight)
model = YOLO("runs/detect/yolov8n_fly/weights/epoch25.pt")

def main():
# Train it
    model.train(
        data="./data/data.yaml",
        epochs=50,
        imgsz=640,
        batch=48,
        name="yolov8n_fly",
        device=0,  # Use GPU 0, change as needed
        save_period=5,  # Save model every 5 epochs
    )


if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()
    main()
    metrics = model.val()
    print(metrics)
    
import cv2
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import asyncio
import time
import numpy as np

from sensors.camera import Camera
from utils.io import AsyncFrameFIFO, AsyncTextFIFO
from utils.vehicle_logger import VehicleStateLogger
from vision.fly.detect import FlyYOLO
from driver.adeept4wd import Adeept4WD

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'vision', 'models', 'best.pt')
FIFO_NAME = "fly_hunt"

JPEG_QUALITY = 75
INFERENCE_SIZE = 416
CONFIDENCE_THRESHOLD = 0.5
DETECTION_INTERVAL = 2

PATROL_SPEED = 35
PATROL_DURATION_STEPS = 50
SCAN_MIN_PAN = -35
SCAN_MAX_PAN = 35
SCAN_STEP = 3
SCAN_INTERVAL_SEC = 0.05
CAM_TILT = 0

ATTACK_FORWARD_SEC = 1.0
ATTACK_BACKWARD_SEC = 1.0
CAMERA_FOV_DEG = 80.0
TURN_SEC_PER_DEG = 0.018
TURN_DEADZONE_DEG = 1.0
TURN_MAX_SEC = 0.7
TURN_SPEED = 55

LOOP_DELAY_SEC = 1 / 30

# State constants
STATE_PATROL = "PATROL"
STATE_SCANNING = "SCANNING"
STATE_ATTACKING = "ATTACKING"

# Vehicle state logging
STATE_LOG_INTERVAL = 1.0  # Seconds between CSV log entries (0 = log every frame)


def pick_target(detections, img_width, img_height):
    if not detections:
        return None

    center_x = img_width / 2
    center_y = img_height / 2

    best_detection = None
    best_score = float('inf')

    for detection in detections:
        det_x, det_y, conf, x1, y1, x2, y2 = detection
        dist = np.sqrt((det_x - center_x) ** 2 + (det_y - center_y) ** 2)
        score = dist - (conf * 120.0)
        if score < best_score:
            best_score = score
            best_detection = (det_x, det_y, conf, x1, y1, x2, y2)

    return best_detection


async def run_for_duration(car, direction, speed, duration_sec):
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        car.move(speed, direction)
        car.update_motor()
        await asyncio.sleep(0.03)
    car.stop()


async def execute_attack(car, text_fifo, target_x, target_pan_angle, img_width):
    """
    Execute attack sequence toward detected target.
    target_x: pixel x-position of target in frame
    target_pan_angle: camera pan angle when target was detected
    img_width: width of image frame
    """
    frame_center_x = img_width / 2
    error_x = target_x - frame_center_x
    degrees_per_pixel = CAMERA_FOV_DEG / img_width
    pixel_angle_offset = error_x * degrees_per_pixel
    
    # Total turn = camera pan angle + pixel offset from center
    total_turn_deg = target_pan_angle + pixel_angle_offset

    if abs(total_turn_deg) < TURN_DEADZONE_DEG:
        turn_duration = 0.0
    else:
        turn_duration = min(TURN_MAX_SEC, abs(total_turn_deg) * TURN_SEC_PER_DEG)

    if total_turn_deg > 0:
        toward = "rr"
        back_to_heading = "rl"
    else:
        toward = "rl"
        back_to_heading = "rr"

    await text_fifo.write_line(
        f"Attack: pan={target_pan_angle:.1f}°, pixel_offset={pixel_angle_offset:.1f}°, total_turn={total_turn_deg:.1f}°, duration={turn_duration:.2f}s"
    )

    if turn_duration > 0:
        await run_for_duration(car, toward, TURN_SPEED, turn_duration)

    await run_for_duration(car, "f", PATROL_SPEED, ATTACK_FORWARD_SEC)
    await run_for_duration(car, "b", PATROL_SPEED, ATTACK_BACKWARD_SEC)

    if turn_duration > 0:
        await run_for_duration(car, back_to_heading, TURN_SPEED, turn_duration)

async def log(text_fifo, message):
    await text_fifo.write_line(message)
    print(message)
    
def nod(car, text_fifo):
    for _ in range(2):
        for i in range(0, 30, 5):
            car.set_cam_tilt_angle(CAM_TILT - i)
            time.sleep(0.02)
        for i in range(25, -5, -5):
            car.set_cam_tilt_angle(CAM_TILT - i)
            time.sleep(0.02)
    
async def main():
    frame_fifo = AsyncFrameFIFO(FIFO_NAME)
    text_fifo = AsyncTextFIFO(FIFO_NAME)
    car = None
    cam = None
    state_logger = None

    try:
        await text_fifo.write_line("Fly hunt worker starting...")
        print("Fly hunt worker starting...")

        car = Adeept4WD()
        cam = Camera()
        fly_yolo = FlyYOLO(model_path=MODEL_PATH, use_fp16=False)

        await text_fifo.write_line(f"Model loaded (Device: {fly_yolo.device}, FP16: {fly_yolo.use_fp16})")

        # Initialize vehicle state logger
        state_logger = VehicleStateLogger(log_interval=STATE_LOG_INTERVAL, mode="fly_hunt")
        await text_fifo.write_line(f"Vehicle state logger initialized: {state_logger.get_log_file_path()}")

        frame_count = 0
        last_detections = []
        current_pan = 0
        current_speed = 0
        scan_direction = 1
        start_time = time.time()
        detection_count = 0  # Counter for saved detections
        
        # State machine variables
        state = STATE_PATROL
        state_start_time = time.time()
        step = 0
        detected_target = None
        detected_target_pan = 0  # Remember pan angle when target was detected

        car.set_cam_tilt_angle(CAM_TILT)
        car.set_cam_pan_angle(0)

        while True:
            detections = []
            data = cam.capture_jpeg(quality=JPEG_QUALITY)
            if data is None:
                await text_fifo.write_line("Warning: camera capture failed")
                await asyncio.sleep(0.02)
                continue

            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                await asyncio.sleep(0.02)
                continue

            img_height, img_width = img.shape[:2]

            # State machine logic
            now = time.time()
            state_elapsed = now - state_start_time

            if state == STATE_PATROL:
                # Move forward for PATROL_DURATION_SEC
                car.move(PATROL_SPEED, "f")
                car.update_motor()
                current_speed = PATROL_SPEED
                
                step += 1
                if step >= PATROL_DURATION_STEPS:
                    # Transition to scanning
                    car.stop()
                    state = STATE_SCANNING
                    state_start_time = now
                    current_pan = SCAN_MIN_PAN
                    scan_direction = 1
                    detected_target = None
                    detected_target_pan = 0
                    step = 0
                    
                    #Turn the car approximately 90 degrees
                    start = time.time()
                    now = time.time()
                    car.turn(1)
                    car.update_motor()
                    print("Turning for scan...")
                    while now - start < 1.7/4:
                        now = time.time()
                        time.sleep(0.02)
                    car.stop()
                        
                    car.set_cam_pan_angle(int(current_pan))
                    await log(text_fifo, "Entering SCANNING mode")

            elif state == STATE_SCANNING:
                # Vehicle stopped, scan camera side-to-side
                car.stop()
                current_speed = 0
                
                detections = fly_yolo.get_detection_centers(
                    img,
                    conf=CONFIDENCE_THRESHOLD,
                    imgsz=INFERENCE_SIZE,
                )
                last_detections = detections
                # Slow down scanning with interval
                await asyncio.sleep(SCAN_INTERVAL_SEC)
                
                # Update camera pan position
                current_pan += scan_direction * SCAN_STEP
                if current_pan >= SCAN_MAX_PAN:
                    current_pan = SCAN_MAX_PAN
                    scan_direction = -1
                elif current_pan <= SCAN_MIN_PAN:
                    current_pan = SCAN_MIN_PAN
                    scan_direction = 1
                
                car.set_cam_pan_angle(int(current_pan))
                
                step += 1
                
                # Check for targets during scan
                target = pick_target(detections, img_width, img_height)
                if target is not None and detected_target is None:
                    detected_target = target
                    detected_target_pan = current_pan  # Remember pan angle at detection
                    
                    # Save detection image
                    detection_count += 1
                    saved_path = state_logger.save_detection_image(data, detection_count)
                    if saved_path:
                        await log(text_fifo, f"Fly detected! Image saved: {saved_path}")
                    else:
                        await log(text_fifo, f"Fly detected at pan={int(current_pan)}° (image save failed)")
                    
                    await log(text_fifo, f"Target acquired at pan={int(current_pan)}°")
                
                # Complete scan when we've gone full sweep (back to start)
                if (scan_direction == 1 and step >= (SCAN_MAX_PAN - SCAN_MIN_PAN) // SCAN_STEP) or detected_target is not None:
                    if detected_target is not None:
                        # Found a target, attack it
                        # state = STATE_ATTACKING
                        # state_start_time = now
                        nod(car, text_fifo)
                        await log(text_fifo, "Target confirmed, entering ATTACKING mode")
                        state = STATE_PATROL
                        step = 0
                        car.set_cam_pan_angle(0)
                        await log(text_fifo, "No target found, resuming patrol")
                        
                        #Turn the car approximately 90 degrees
                        start = time.time()
                        now = time.time()
                        car.turn(-1)
                        car.update_motor()
                        while now - start < 1.7/4:
                            now = time.time()
                            time.sleep(0.02)
                        car.stop()
                    else:
                        # No target found, resume patrol
                        state = STATE_PATROL
                        step = 0
                        car.set_cam_pan_angle(0)
                        await log(text_fifo, "No target found, resuming patrol")
                        
                        #Turn the car approximately 90 degrees
                        start = time.time()
                        now = time.time()
                        car.turn(-1)
                        car.update_motor()
                        while now - start < 1.7/4:
                            now = time.time()
                            time.sleep(0.02)
                        car.stop()



            elif state == STATE_ATTACKING:
                # Attack the detected target
                car.stop()
                target_x = detected_target[0]
                
                # Execute attack with target position and pan angle
                await execute_attack(car, text_fifo, target_x, detected_target_pan, img_width)
                
                # Reset and return to patrol
                state = STATE_PATROL
                step = 0
                detected_target = None
                detected_target_pan = 0
                car.set_cam_pan_angle(0)
                await text_fifo.write_line("Attack complete, resuming patrol")

                #Turn the car approximately 90 degrees
                start = time.time()
                now = time.time()
                car.turn(-1)
                car.update_motor()
                while now - start < 1.7/4:
                    now = time.time()
                    time.sleep(0.02)
                car.stop()


            # Log vehicle state to CSV
            target_detected = detected_target is not None
            state_logger.log_state(
                state=state,
                speed=int(current_speed),
                cam_pan=int(current_pan),
                cam_tilt=CAM_TILT,
                target_detected=target_detected
            )

            # Draw detections on frame
            target = pick_target(detections, img_width, img_height)
            for detection in detections:
                center_x, center_y, conf, x1, y1, x2, y2 = detection
                is_target = target is not None and center_x == target[0] and center_y == target[1]
                color = (0, 0, 255) if is_target else (0, 255, 0)
                thickness = 3 if is_target else 2
                cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
                cv2.circle(img, (int(center_x), int(center_y)), 4, color, -1)
                cv2.putText(
                    img,
                    f"{conf:.2f}",
                    (int(x1), int(y1) - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2,
                )

            cv2.line(img, (img_width // 2 - 20, img_height // 2), (img_width // 2 + 20, img_height // 2), (255, 255, 0), 1)
            cv2.line(img, (img_width // 2, img_height // 2 - 20), (img_width // 2, img_height // 2 + 20), (255, 255, 0), 1)

            _, processed_data = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            await frame_fifo.write_frame(processed_data.tobytes())

            frame_count += 1
            if frame_count % 15 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                await text_fifo.write_line(
                    f"Status: {frame_count} frames, {fps:.1f} fps, detections={len(detections)}, state={state}, pan={int(current_pan)}°"
                )

            await asyncio.sleep(LOOP_DELAY_SEC)

    finally:
        try:
            if state_logger is not None:
                state_logger.close()
        except Exception:
            pass

        try:
            if car is not None:
                car.stop()
                car.set_cam_pan_angle(0)
                car.set_cam_tilt_angle(0)
        except Exception:
            pass

        try:
            if cam is not None:
                cam.release()
        except Exception:
            pass

        try:
            await text_fifo.write_line("Fly hunt worker stopped")
        except Exception:
            pass

        frame_fifo.close()
        text_fifo.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")

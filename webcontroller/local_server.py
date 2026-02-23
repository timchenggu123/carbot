from flask import Flask, Response, render_template, jsonify, request
import subprocess
import signal
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.io import AsyncFrameFIFO, AsyncTextFIFO
from threading import Lock
from driver.adeept4wd import Adeept4WD
car = Adeept4WD()

app = Flask(__name__)

# Global FIFO channels
frame_fifo = AsyncFrameFIFO("camera")
text_fifo = AsyncTextFIFO("camera")
detection_frame_fifo = AsyncFrameFIFO("detection")
detection_text_fifo = AsyncTextFIFO("detection")
test_routine_text_fifo = AsyncTextFIFO("test_routine_worker")

# Start reading tasks
frame_fifo.start_reading()
text_fifo.start_reading()
detection_text_fifo.start_reading()
detection_frame_fifo.start_reading()
test_routine_text_fifo.start_reading()

#Register global variables
detection_process = None
_detection_lock = Lock()

camera_process = None
logs_dict = {}

DEMOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'demos'))

def start_camera():
    """Start the camera worker process"""
    global camera_process
    if camera_process is not None:
        return
    
    # Start the camera worker (async FIFO mode)
    camera_process = subprocess.Popen(
        ["python3", os.path.join(DEMOS_DIR, "camera_worker.py")]
    )
    print("Camera worker started (async FIFO mode)")

def stop_camera():
    """Stop the camera worker process"""
    global camera_process
    if camera_process:
        # Force terminate
        camera_process.send_signal(signal.SIGTERM)
        try:
            camera_process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            camera_process.kill()
        
        camera_process = None
        print("Camera worker stopped")

def start_detection():
    """Start the detection worker process"""
    global detection_process
    with _detection_lock:
        if detection_process is not None:
            return
        detection_process = subprocess.Popen(["python3", os.path.join(DEMOS_DIR, "detection_worker.py")])
        print("Detection worker started")

def stop_detection():
    """Stop the detection worker process"""
    global detection_process
    with _detection_lock:
        if detection_process:
            detection_process.send_signal(signal.SIGTERM)
            try:
                detection_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                detection_process.kill()
            detection_process = None
            print("Detection worker stopped")

def car_move(direction):
    """Move the car in the specified direction"""
    car.move(100, direction)
    car.update_motor()
    
def car_stop():
    """Stop the car"""
    car.stop()

def car_pan(angle):
    """Pan the car's camera to the specified angle"""
    car.set_cam_pan_angle(angle)

def car_tilt(angle):
    """Tilt the car's camera to the specified angle"""
    car.set_cam_tilt_angle(angle)

def gen_frames():
    """Generate frames from async FIFO for HTTP streaming"""
    while True:
        try:
            # Get frame using synchronous wrapper
            frame_data = frame_fifo.get_frame(timeout=1.0)
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + f"{len(frame_data)}".encode() + b'\r\n\r\n' +
                       frame_data + b'\r\n')
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Error getting frame: {e}")
            time.sleep(0.01)

# Detection frames generator
def gen_detection_frames():
    """Generate detection frames from async FIFO for HTTP streaming"""
    while True:
        try:
            frame_data = detection_frame_fifo.get_frame(timeout=1.0)
            if frame_data:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n'
                       b'Content-Length: ' + f"{len(frame_data)}".encode() + b'\r\n\r\n' +
                       frame_data + b'\r\n')
            else:
                time.sleep(0.01)
        except Exception as e:
            print(f"Error getting detection frame: {e}")
            time.sleep(0.01)

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/camera')
def camera_page():
    start_camera()
    return render_template("camera.html")

@app.route('/video')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_camera', methods=['GET', 'POST'])
def stop_camera_route():
    stop_camera()
    return "Camera stopped"

@app.route('/detection')
def detection_route():
    start_detection()
    return render_template("detection.html")


@app.route('/detection/stop', methods=['GET', 'POST'])
def detection_stop_route():
    stop_detection()
    return "Detection stopped"


@app.route('/camera/logs')
def camera_logs():
    """Get recent camera logs from async text FIFO"""
    global logs_dict
    logs = logs_dict.get("camera", [])
    # Read all available text messages (non-blocking)
    for _ in range(10):  # Limit to prevent blocking
        try:
            text = text_fifo.readline(timeout=0.001)
            if text is None:
                break
            logs.append(text)
        except Exception:
            break
    logs_dict["camera"] = logs[-100:]  # Keep last 100 logs
    return jsonify({"logs": logs})

@app.route('/detection/logs')
def detection_logs():
    """Get recent detection logs from async text FIFO"""
    global logs_dict
    logs = logs_dict.get("detection", [])
    # Read available messages (non-blocking)
    for _ in range(50):  # read up to 50 lines
        try:
            text = detection_text_fifo.readline(timeout=0.001)
            if text is None:
                break
            logs.append(text)
        except Exception:
            break
    logs_dict["detection"] = logs[-500:]  # Keep last 500 logs
    return jsonify({"logs": logs})

# Detection video route
@app.route('/detection/video')
def detection_video_feed():
    return Response(gen_detection_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control/move/<direction>')
def control_move(direction):
    car_move(direction)
    return f"Moving {direction}"

@app.route('/control/stop')
def control_stop():
    car_stop()
    return "Car stopped"

@app.route('/control/pan')
def control_pan():
    angle = request.args.get('angle', 0, type=int)
    car_pan(angle)
    return f"Camera pan set to {angle} degrees"

@app.route('/control/tilt')
def control_tilt():
    angle = request.args.get('angle', 0, type=int)
    car_tilt(angle)
    return f"Camera tilt set to {angle} degrees"

@app.route('/test_routine')
def test_routine():
    """Run the test routine worker"""
    # Start the test routine worker (synchronous for simplicity)
    subprocess.Popen(["python3", os.path.join(DEMOS_DIR, "test_routine_worker.py")])
    return render_template("test_routine.html")

@app.route('/test_routine/logs')
def test_routine_logs():
    """Get recent test routine logs from async text FIFO"""
    global logs_dict
    logs = logs_dict.get("test_routine_worker", [])
    # Read available messages (non-blocking)
    for _ in range(50):  # read up to 50 lines
        try:
            text = test_routine_text_fifo.readline(timeout=0.001)
            if text is None:
                break
            logs.append(text)
        except Exception:
            break
    logs_dict["test_routine_worker"] = logs[-500:]  # Keep last 500 logs
    return jsonify({"logs": logs})

if __name__ == '__main__':
    import atexit
    
    def cleanup():
        """Cleanup when server shuts down"""
        stop_camera()
        stop_detection()
        frame_fifo.close()
        text_fifo.close()
        detection_text_fifo.close()
        detection_frame_fifo.close()
        test_routine_text_fifo.close()
    atexit.register(cleanup)
    
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        cleanup()

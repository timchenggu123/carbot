from flask import Flask, Response, render_template
import subprocess
import struct
import threading
import queue
import signal

app = Flask(__name__)

frame_queue = queue.Queue(maxsize=3)
camera_process = None
reader_thread = None
stop_reader = False

def start_camera():
    global camera_process, reader_thread, stop_reader
    if camera_process is not None:
        return

    camera_process = subprocess.Popen(
        ["python3", "demos/camera_worker.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
    stop_reader = False
    reader_thread = threading.Thread(target=read_frames)
    reader_thread.start()
    print("Camera worker started")

def stop_camera():
    global camera_process, stop_reader
    if camera_process:
        stop_reader = True
        camera_process.send_signal(signal.SIGTERM)
        camera_process.wait(timeout=2)
        camera_process = None
        print("Camera worker stopped")

def read_frames():
    global stop_reader
    pipe = camera_process.stdout
    while not stop_reader:
        try:
            header = pipe.read(4)
            if not header:
                break
            (length,) = struct.unpack('>I', header)
            data = pipe.read(length)
            if not data:
                break
            if not frame_queue.full():
                frame_queue.put(data)
        except Exception as e:
            print("Frame read error:", e)
            break

def gen_frames():
    while True:
        frame = frame_queue.get()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + f"{len(frame)}".encode() + b'\r\n\r\n' +
               frame + b'\r\n')

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)

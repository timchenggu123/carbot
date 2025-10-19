# test_camera_stream.py
from flask import Flask, Response
import cv2

app = Flask(__name__)
camera = cv2.VideoCapture(0)  # 0 = first USB webcam

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return '<h2>Camera test</h2><img src="/video" width="640">'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
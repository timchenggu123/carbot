from flask import Flask, render_template, Response
import os


os.environ['FLASK_DEBUG'] = 'development'
app = Flask(__name__)
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/mjpg.jpg')
def getjpg():
    return 

class Server:
    @staticmethod
    def run():
        try:
            app.run(host="0.0.0.0", port=9000, threaded=True, debug=False)
        except Exception as e:
            print(e)

if __name__ == "__main__":
    Server.run()
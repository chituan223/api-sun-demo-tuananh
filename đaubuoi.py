from flask import Flask
from websocket import WebSocketApp

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ API đang hoạt động bình thường!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
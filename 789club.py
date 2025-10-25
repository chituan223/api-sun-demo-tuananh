import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from websocket import WebSocketApp

PORT = 10000

# ================== Biến toàn cục ==================
latestResult = {
    "Ket_qua": "Chưa có kết quả",
    "Phien": 0,
    "Tong": 0,
    "Xuc_xac_1": 0,
    "Xuc_xac_2": 0,
    "Xuc_xac_3": 0,
    "id": "@sg205rika"
}

lastEventId = 19

# ================== WebSocket ==================
WS_URL = "wss://websocket.atpman.net/websocket"
HEADERS = [
    "Host: websocket.atpman.net",
    "Origin: https://play.789club.sx",
    "User-Agent: Mozilla/5.0",
    "Accept-Encoding: gzip, deflate, br, zstd",
    "Accept-Language: vi-VN,vi;q=0.9",
    "Pragma: no-cache",
    "Cache-Control: no-cache"
]

# ----- Đăng nhập bằng tài khoản mới -----
LOGIN_MESSAGE = [
    1,
    "MiniGame",
    "wanglin2019a",        # user mới
    "WangFlang1",          # pass mới
    {
        "info": "{\"ipAddress\":\"113.185.47.3\",\"wsToken\":\"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJnZW5kZXIiOjAsImNhblZpZXdTdGF0IjpmYWxzZSwiZGlzcGxheU5hbWUiOiJ3YW5nbGluOTE5MjkiLCJib3QiOjAsImlzTWVyY2hhbnQiOmZhbHNlLCJ2ZXJpZmllZEJhbmtBY2NvdW50IjpmYWxzZSwicGxheUV2ZW50TG9iYnkiOmZhbHNlLCJjdXN0b21lcklkIjo2MjYwNjIwNSwiYWZmSWQiOiJkZWZhdWx0IiwiYmFubmVkIjpmYWxzZSwiYnJhbmQiOiI3ODkuY2x1YiIsInRpbWVzdGFtcCI6MTc1ODEzMjUzNzYyMywibG9ja0dhbWVzIjpbXSwiYW1vdW50IjowLCJsb2NrQ2hhdCI6ZmFsc2UsInBob25lVmVyaWZpZWQiOmZhbHNlLCJpcEFkZHJlc3MiOiIxMTMuMTg1LjQ3LjMiLCJtdXRlIjpmYWxzZSwiYXZhdGFyIjoiaHR0cHM6Ly9hcGkueGV1aS5pby9pbWFnZXMvYXZhdGFyL2F2YXRhcl8xMy5wbmciLCJwbGF0Zm9ybUlkIjo1LCJ1c2VySWQiOiJjMTQ2ODVlMS1mOGExLTRlYTMtYmEwYS01Y2M4Yjc1NzczNjAiLCJyZWdUaW1lIjoxNzU4MTMyNDcyMDkzLCJwaG9uZSI6IiIsImRlcG9zaXQiOmZhbHNlLCJ1c2VybmFtZSI6IlM4X3dhbmdsaW4yMDE5YSJ9.FEtg0oB1mkGhpzSCPmO3k6q-U5O-MQqVwu4HjrBG1O0\",\"locale\":\"vi\",\"userId\":\"c14685e1-f8a1-4ea3-ba0a-5cc8b7577360\",\"username\":\"S8_wanglin2019a\",\"timestamp\":1758132537623,\"refreshToken\":\"70cb336ff95a46d292f16c4fafe0a973.a46444d78db54b44a0cc4e812f979db2\"}",
        "signature": "261EECD1A140C46175B081A912CFBCCA1C78727084352D38F8A83FF7D9ED132DEA65B76F84C61465218DED52BA5D90C96807DF7FB48C90D8DDE133955A09C9FB09DA617FC9F19C1D9024B4381149BAC7C771379013FE4FF99924B4CCAD128021663FFF4809F9B141CC8B5CE8D5721EF87932805124D0349CFD3F923178156052"
    }
]

SUBSCRIBE_TX_RESULT = [6, "MiniGame", "taixiuUnbalancedPlugin", {"cmd": 2000}]
SUBSCRIBE_LOBBY = [6, "MiniGame", "lobbyPlugin", {"cmd": 10001}]

def on_open(ws):
    print("✅ Đã kết nối WebSocket")
    ws.send(json.dumps(LOGIN_MESSAGE))

    def run():
        time.sleep(1)
        ws.send(json.dumps(SUBSCRIBE_TX_RESULT))
        ws.send(json.dumps(SUBSCRIBE_LOBBY))

        while True:
            time.sleep(10)
            ws.send("2")  # ping
            ws.send(json.dumps(SUBSCRIBE_TX_RESULT))
            ws.send(json.dumps([7, "Simms", lastEventId, 0, {"id": 0}]))

    threading.Thread(target=run, daemon=True).start()

def on_message(ws, message):
    global latestResult, lastEventId
    try:
        data = json.loads(message)

        if isinstance(data, list):
            # cập nhật lastEventId
            if len(data) >= 3 and data[0] == 7 and data[1] == "Simms" and isinstance(data[2], int):
                lastEventId = data[2]

            # dữ liệu kết quả Tài/Xỉu
            if isinstance(data[1], dict) and data[1].get("cmd") == 2006:
                sid = data[1].get("sid")
                d1, d2, d3 = data[1].get("d1"), data[1].get("d2"), data[1].get("d3")
                tong = d1 + d2 + d3
                ketqua = "Tài" if tong >= 11 else "Xỉu"

                latestResult = {
                    "Ket_qua": ketqua,
                    "Phien": sid,
                    "Tong": tong,
                    "Xuc_xac_1": d1,
                    "Xuc_xac_2": d2,
                    "Xuc_xac_3": d3,
                    "id": "@sg205rika"
                }

                print("🎲 Cập nhật:", latestResult)

    except Exception as e:
        print("❌ Lỗi message:", str(e))

def on_close(ws, close_status_code, close_msg):
    print("🔌 WebSocket đóng. Kết nối lại sau 5s...")
    time.sleep(5)
    start_ws()

def on_error(ws, error):
    print("❌ Lỗi WebSocket:", error)

def start_ws():
    ws = WebSocketApp(
        WS_URL,
        header=HEADERS,
        on_open=on_open,
        on_message=on_message,
        on_close=on_close,
        on_error=on_error
    )
    ws.run_forever()

# ================== HTTP SERVER ==================
class MyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/taixiu":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(latestResult).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Khong tim thay")

def start_http():
    server = HTTPServer(("0.0.0.0", PORT), MyHandler)
    print(f"🌐 HTTP Server chạy tại http://localhost:{PORT}/taixiu")
    server.serve_forever()

# ================== RUN ==================
if __name__ == "__main__":
    threading.Thread(target=start_ws, daemon=True).start()
    start_http()
import json
import threading
import time
import os
import logging
import random
from urllib.request import urlopen, Request
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

HOST = '0.0.0.0'
POLL_INTERVAL = 5
RETRY_DELAY = 5
MAX_HISTORY = 50

lock_100 = threading.Lock()
lock_101 = threading.Lock()

latest_result_100 = {
    "Phien": 0, "Xuc_xac_1": 0, "Xuc_xac_2": 0, "Xuc_xac_3": 0,
    "Tong": 0, "Ket_qua": "Chưa có", "Do_tin_cay": 0, "id": "djtuancon"
}
latest_result_101 = {
    "Phien": 0, "Xuc_xac_1": 0, "Xuc_xac_2": 0, "Xuc_xac_3": 0,
    "Tong": 0, "Ket_qua": "Chưa có", "Do_tin_cay": 0, "id": "djtuancon"
}

history_100 = []
history_101 = []

last_sid_100 = None
last_sid_101 = None

# ================= 10 thuật toán cơ bản =================
def algo1_weightedRecent(hist):
    if not hist: return "Tài"
    t = sum((i+1)/len(hist) for i,v in enumerate(hist) if v=="Tài")
    x = sum((i+1)/len(hist) for i,v in enumerate(hist) if v=="Xỉu")
    return "Tài" if t>=x else "Xỉu"

def algo2_expDecay(hist, decay=0.6):
    if not hist: return "Tài"
    t = x = 0
    w = 1
    for v in reversed(hist):
        if v=="Tài": t += w
        else: x += w
        w *= decay
    return "Tài" if t>x else "Xỉu"

def algo3_longChainReverse(hist, k=3):
    if not hist: return "Tài"
    last = hist[-1]
    chain = 1
    for v in reversed(hist[:-1]):
        if v==last: chain += 1
        else: break
    if chain>=k: return "Xỉu" if last=="Tài" else "Tài"
    return last

def algo4_windowMajority(hist, window=5):
    if not hist: return "Tài"
    win = hist[-window:] if len(hist)>=window else hist
    return "Tài" if win.count("Tài")>=len(win)/2 else "Xỉu"

def algo5_alternation(hist):
    if len(hist)<4: return "Tài"
    flips = sum(1 for i in range(1,4) if hist[-i]!=hist[-i-1])
    if flips>=3: return "Xỉu" if hist[-1]=="Tài" else "Tài"
    return hist[-1]

def algo6_patternRepeat(hist):
    L = len(hist)
    if L<4: return "Tài"
    for length in range(2, min(6, L//2)+1):
        a = "".join(hist[-length:])
        b = "".join(hist[-2*length:-length])
        if a==b: return hist[-length]
    return algo4_windowMajority(hist,4)

def algo7_mirror(hist):
    if len(hist)<8: return hist[-1] if hist else "Tài"
    return "Xỉu" if hist[-4:]==hist[-8:-4] and hist[-1]=="Tài" else hist[-1]

def algo8_entropy(hist):
    if not hist: return "Tài"
    t = hist.count("Tài")
    x = len(hist)-t
    diff = abs(t-x)
    if diff<=len(hist)//5: return "Xỉu" if hist[-1]=="Tài" else "Tài"
    return "Xỉu" if t>x else "Tài"

def algo9_momentum(hist):
    if len(hist)<2: return "Tài"
    score = sum(1 if hist[i]==hist[i-1] else -1 for i in range(1,len(hist)))
    return hist[-1] if score>0 else ("Xỉu" if hist[-1]=="Tài" else "Tài")

def algo10_freqRatio(hist):
    if not hist: return "Tài"
    ratio = hist.count("Tài")/len(hist)
    if ratio>0.62: return "Xỉu"
    if ratio<0.38: return "Tài"
    return hist[-1]

algos = [algo1_weightedRecent, algo2_expDecay, algo3_longChainReverse,
         algo4_windowMajority, algo5_alternation, algo6_patternRepeat,
         algo7_mirror, algo8_entropy, algo9_momentum, algo10_freqRatio]

# ================= Hybrid Votes + Confidence =================
def hybrid_predict(hist):
    if not hist: 
        return {"prediction":"Tài","confidence":50}
    
    votes = []
    scoreT = scoreX = 0
    
    for fn in algos:
        v = fn(hist)
        if random.random() < 0.05:  # 5% đổi ngược lại
            v = "Xỉu" if v=="Tài" else "Tài"
        votes.append(v)
        if v=="Tài": scoreT += 1
        else: scoreX += 1
    
    pred = "Tài" if scoreT>=scoreX else "Xỉu"
    conf = int((max(scoreT,scoreX)/len(algos))*100 + random.randint(-5,5))
    conf = max(50, min(conf, 99))
    
    return {"prediction": pred, "confidence": conf, "votes": votes}

# ================= Core Functions =================
def get_tai_xiu(d1, d2, d3):
    total = d1 + d2 + d3
    return "Xỉu" if total <= 10 else "Tài"

def update_result(store, history, lock, result):
    with lock:
        # dự đoán
        past_results = [r['Ket_qua'] for r in history]
        pred_conf = hybrid_predict(past_results)
        result["Du_doan"] = pred_conf["prediction"]
        result["Do_tin_cay"] = pred_conf["confidence"]

        store.clear()
        store.update(result)
        history.insert(0, result.copy())
        if len(history) > MAX_HISTORY:
            history.pop()

# ================= Polling API =================
def poll_api(gid, lock, result_store, history, is_md5):
    global last_sid_100, last_sid_101
    url = f"https://api-agent.gowsazhjo.net/glms/v1/notify/taixiu?platform_id=b5&gid={gid}"
    while True:
        try:
            req = Request(url, headers={'User-Agent': 'Python-Proxy/1.0'})
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if data.get('status') == 'OK' and isinstance(data.get('data'), list):
                for game in data['data']:
                    cmd = game.get("cmd")
                    d1, d2, d3 = game.get("d1"), game.get("d2"), game.get("d3")

                    # --- MD5 bàn ---
                    if is_md5 and cmd == 2006:
                        sid = game.get("sid")
                        md5_val = game.get("md5")
                        rs_val = game.get("rs")
                        if sid and sid != last_sid_101 and None not in (d1,d2,d3):
                            last_sid_101 = sid
                            total = d1+d2+d3
                            ket_qua = get_tai_xiu(d1,d2,d3)
                            result = {
                                "Phien": sid,
                                "Xuc_xac_1": d1,
                                "Xuc_xac_2": d2,
                                "Xuc_xac_3": d3,
                                "Tong": total,
                                "Ket_qua": ket_qua,
                                "md5": md5_val,
                                "rs": rs_val,
                                "id": "djtuancon"
                            }
                            update_result(result_store, history, lock, result)
                            logger.info(f"[MD5] Phiên {sid} - Tổng {total}, KQ {ket_qua}")

                    # --- Bàn thường ---
                    elif not is_md5 and cmd == 1003:
                        sid = None
                        for g in data['data']:
                            if g.get("cmd") == 2007:
                                sid = g.get("sid")
                                break
                        if sid and sid != last_sid_100 and None not in (d1,d2,d3):
                            last_sid_100 = sid
                            total = d1+d2+d3
                            ket_qua = get_tai_xiu(d1,d2,d3)
                            result = {
                                "Phien": sid,
                                "Xuc_xac_1": d1,
                                "Xuc_xac_2": d2,
                                "Xuc_xac_3": d3,
                                "Tong": total,
                                "Ket_qua": ket_qua,
                                "id": "djtuancon"
                            }
                            update_result(result_store, history, lock, result)
                            logger.info(f"[TX] Phiên {sid} - Tổng {total}, KQ {ket_qua}")

        except Exception as e:
            logger.error(f"Lỗi API {gid}: {e}")
            time.sleep(RETRY_DELAY)
        time.sleep(POLL_INTERVAL)

# ================= Flask API =================
app = Flask(__name__)

@app.route("/api/taixiu", methods=["GET"])
def get_taixiu_100():
    with lock_100:
        return jsonify(latest_result_100)

@app.route("/api/taixiumd5", methods=["GET"])
def get_taixiu_101():
    with lock_101:
        return jsonify(latest_result_101)

@app.route("/api/history", methods=["GET"])
def get_history():
    with lock_100, lock_101:
        return jsonify({
            "taixiu": history_100,
            "taixiumd5": history_101
        })

@app.route("/")
def index():
    return "API Server TaiXiu running. Endpoints: /api/taixiu, /api/taixiumd5, /api/history"

# ================= Main =================
if __name__ == "__main__":
    logger.info("Khởi động hệ thống API Tài Xỉu...")
    thread_100 = threading.Thread(target=poll_api,
                                  args=("vgmn_100", lock_100, latest_result_100, history_100, False),
                                  daemon=True)
    thread_101 = threading.Thread(target=poll_api,
                                  args=("vgmn_101", lock_101, latest_result_101, history_101, True),
                                  daemon=True)
    thread_100.start()
    thread_101.start()
    logger.info("Đã bắt đầu polling dữ liệu.")
    port = int(os.environ.get("PORT", 8000))
    app.run(host=HOST, port=port)

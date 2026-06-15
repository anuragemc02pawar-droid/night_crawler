import sys
import time
import threading
import requests
from flask import Flask, request, jsonify
import os
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.consistent_hash import ConsistentHashRing

app = Flask(__name__)
CORS(app)

ring = ConsistentHashRing()
WORKER_PORTS = [5001, 5002, 5003, 5004]
WORKER_STATUS = {}

for port in WORKER_PORTS:
    node_id = f"worker_{port}"
    ring.add_node(node_id)
    WORKER_STATUS[node_id] = {"port": port, "alive": True}

def check_health():
    while True:
        for node_id, info in WORKER_STATUS.items():
            try:
                resp = requests.get(f"http://127.0.0.1:{info['port']}/health", timeout=2)
                if resp.status_code == 200:
                    if not info["alive"]:
                        print(f"{node_id} back online")
                        ring.add_node(node_id)
                    info["alive"] = True
                else:
                    raise Exception("bad status")
            except:
                if info["alive"]:
                    print(f"{node_id} went offline")
                    ring.remove_node(node_id)
                info["alive"] = False
        time.sleep(5)

@app.route('/crawl', methods=['POST'])
def crawl():
    data = request.json
    urls = data.get('urls', [])

    assignments = {}
    for url in urls:
        node_id = ring.get_node(url)
        if node_id is None:
            continue
        assignments.setdefault(node_id, []).append(url)

    all_results = []
    for node_id, node_urls in assignments.items():
        port = WORKER_STATUS[node_id]["port"]
        try:
            resp = requests.post(f"http://127.0.0.1:{port}/scrape", json={"urls": node_urls}, timeout=30)
            all_results.append(resp.json())
        except Exception as e:
            all_results.append({"node": node_id, "error": str(e)})

    return jsonify({"assignments": {k: v for k, v in assignments.items()}, "results": all_results})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "alive_nodes": ring.get_all_nodes(),
        "all_nodes": WORKER_STATUS
    })

if __name__ == "__main__":
    health_thread = threading.Thread(target=check_health, daemon=True)
    health_thread.start()
    print("Coordinator running on port 6000")
    app.run(port=6060, debug=False)
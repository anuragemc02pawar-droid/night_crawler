import sys
import time
import threading
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.consistent_hash import ConsistentHashRing

app = Flask(__name__)
CORS(app)

# Config
WORKER_PORTS = [5001, 5002, 5003, 5004]
HEALTH_CHECK_INTERVAL = 5   # seconds
SCRAPE_TIMEOUT = 30          # seconds
RETRY_ATTEMPTS = 2

ring = ConsistentHashRing()
WORKER_STATUS = {}

for port in WORKER_PORTS:
    node_id = f"worker_{port}"
    ring.add_node(node_id)
    WORKER_STATUS[node_id] = {"port": port, "alive": True}


def check_health():
    while True:
        for node_id, info in WORKER_STATUS.items():
            try:
                resp = requests.get(
                    f"http://127.0.0.1:{info['port']}/health",
                    timeout=2
                )
                if resp.status_code == 200:
                    if not info["alive"]:
                        print(f"[coordinator] {node_id} back online — re-adding to ring")
                        ring.add_node(node_id)
                    info["alive"] = True
                else:
                    raise Exception(f"bad status {resp.status_code}")
            except Exception as e:
                if info["alive"]:
                    print(f"[coordinator] {node_id} went offline: {e}")
                    ring.remove_node(node_id)
                info["alive"] = False

        time.sleep(HEALTH_CHECK_INTERVAL)


def dispatch_to_worker(node_id, urls):
    """Send URLs to a worker with retry logic."""
    port = WORKER_STATUS[node_id]["port"]
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = requests.post(
                f"http://127.0.0.1:{port}/scrape",
                json={"urls": urls},
                timeout=SCRAPE_TIMEOUT
            )
            return resp.json()
        except Exception as e:
            if attempt == RETRY_ATTEMPTS - 1:
                return {"node": node_id, "error": str(e)}
            time.sleep(0.5)


@app.route('/crawl', methods=['POST'])
def crawl():
    data = request.json
    urls = data.get('urls', [])

    # Assign each URL to a node via consistent hashing
    assignments = {}
    skipped = []
    for url in urls:
        node_id = ring.get_node(url)
        if node_id is None:
            skipped.append(url)
            continue
        assignments.setdefault(node_id, []).append(url)

    # Dispatch to workers (threaded for parallelism)
    all_results = []
    threads = []
    lock = threading.Lock()

    def worker_task(node_id, node_urls):
        result = dispatch_to_worker(node_id, node_urls)
        with lock:
            all_results.append(result)

    for node_id, node_urls in assignments.items():
        t = threading.Thread(target=worker_task, args=(node_id, node_urls))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return jsonify({
        "assignments": assignments,
        "skipped": skipped,
        "results": all_results,
    })


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "alive_nodes": ring.get_all_nodes(),
        "all_nodes": WORKER_STATUS,
    })


if __name__ == "__main__":
    health_thread = threading.Thread(target=check_health, daemon=True)
    health_thread.start()
    print("[coordinator] Running on port 6060")
    app.run(port=6060, debug=False)
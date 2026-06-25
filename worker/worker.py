import sys
import json
import os
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import redis
from flask_cors import CORS

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bloom_filter import DistributedBloomFilter

app = Flask(__name__)
CORS(app)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
NODE_ID = f"worker_{PORT}"

r = redis.Redis(host='localhost', port=6379, decode_responses=True, protocol=2)
bf = DistributedBloomFilter()


@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.json
    urls = data.get('urls', [])
    results = []

    for url in urls:
        if bf.might_exist(url):
            continue
        try:
            resp = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(resp.text, 'html.parser')

            title = soup.title.string.strip() if soup.title and soup.title.string else "No title"

            meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
            meta_description = (
                meta_desc_tag['content'].strip()
                if meta_desc_tag and meta_desc_tag.get('content')
                else ""
            )

            headings = [
                h.get_text(strip=True)
                for h in soup.find_all(['h1', 'h2'])
                if h.get_text(strip=True)
            ][:5]

            links = list({a['href'] for a in soup.find_all('a', href=True)})[:10]

            page_data = {
                "title": title,
                "meta_description": meta_description,
                "headings": headings,
                "links": links,
                "status_code": resp.status_code,
            }

            r.set(f"result:{url}", json.dumps(page_data))
            bf.add(url)
            results.append({"url": url, "data": page_data})

        except Exception as e:
            results.append({"url": url, "error": str(e)})

    return jsonify({"node": NODE_ID, "results": results})


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "alive", "node": NODE_ID})


if __name__ == "__main__":
    print(f"Starting {NODE_ID} on port {PORT}")
    app.run(port=PORT, debug=False)
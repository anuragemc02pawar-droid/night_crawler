import sys
import time
import threading 
import requests
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import redis

import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.bloom_filter import DistributedBloomFilter

app=Flask(__name__)

PORT=int(sys.argv[1]) if len(sys.argv)>1 else 5001
NODE_ID=f"worker_{PORT}"

r=redis.Redis(host='localhost',port=6379,decode_responses=True,protocol=2)
bf=DistributedBloomFilter()

@app.route('/scrape',methods=['POST'])
def scrape():
    data=request.json
    urls=data.get('urls',[])
    results=[]

    for url in urls:
        if bf.might_exist(url):
            continue
        try:
            resp=requests.get(url,timeout=5)
            soup=BeautifulSoup(resp.text,'html.parser')
            title=soup.title.string if soup.title else "No title"
            r.set(f"result:{url}",title)
            bf.add(url)
            results.append({"url":url, "title":title})
        except Exception as e:
            results.append({"url":url, "error":str(e)})

    return jsonify({"node":NODE_ID,"results":results})

@app.route('/health',methods=['GET'])
def health():
    return jsonify({"status": "alive", "node": NODE_ID})

if __name__ == "__main__":
    print(f"Starting {NODE_ID} on port {PORT}")
    app.run(port=PORT, debug=False)


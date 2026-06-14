import requests
resp = requests.post("http://127.0.0.1:5001/scrape", json={"urls": ["https://google.com"]})
print(resp.json())
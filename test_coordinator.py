import requests
resp = requests.post("http://127.0.0.1:6000/crawl", json={"urls": [
    "https://example.com",
    "https://google.com",
    "https://github.com",
    "https://wikipedia.org"
]})
print(resp.json())
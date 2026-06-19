# NightCrawler — Fault Tolerant Distributed Web Crawler

A distributed crawling system that splits scraping jobs across multiple worker nodes using consistent hashing, with automatic fault tolerance and deduplication via a distributed Bloom filter.

## Architecture

- **Coordinator** (`coordinator/coordinator.py`) — assigns URLs to worker nodes using consistent hashing, monitors node health via heartbeats, and automatically redistributes work when a node fails.
- **Worker nodes** (`worker/worker.py`) — each node scrapes its assigned URLs, checks a shared Bloom filter to skip already-scraped URLs, extracts page data, and stores results in Redis.
- **Consistent Hash Ring** (`common/consistent_hash.py`) — 150 virtual nodes per worker for even URL distribution. When a node joins or leaves, only a small fraction of URLs are reassigned; everything else stays untouched.
- **Distributed Bloom Filter** (`common/bloom_filter.py`) — Redis-backed, ensures no URL is scraped twice across any node, using roughly 1.2 MB for 1 million URLs at a 1% false positive rate.
- **Dashboard** (`dashboard/index.html`) — live node status and crawl interface in the browser.

## Tech Stack

Python, Flask, Redis, BeautifulSoup, Consistent Hashing, Bloom Filters

## How It Works

1. A crawl request comes in with a list of URLs.
2. The coordinator hashes each URL onto the consistent hash ring and assigns it to a worker node.
3. Each worker checks the shared Bloom filter — if the URL was already scraped by any node, it's skipped.
4. New URLs are fetched, parsed, and key data (title, meta description, headings, links) is extracted and stored in Redis.
5. The coordinator runs a heartbeat health check every 5 seconds. If a worker goes offline, it's removed from the hash ring and its future URL assignments automatically shift to the next available node — no manual reassignment, no data loss.
6. When a worker comes back online, it rejoins the ring and resumes receiving its share of work.

## Setup

1. Install and start Redis (verify with `redis-cli ping`, should return `PONG`)
2. Install dependencies:
   ```bash
   pip install flask flask-cors redis requests beautifulsoup4
   ```
3. Start worker nodes (one per terminal):
   ```bash
   python worker/worker.py 5001
   python worker/worker.py 5002
   python worker/worker.py 5003
   python worker/worker.py 5004
   ```
4. Start the coordinator:
   ```bash
   python coordinator/coordinator.py
   ```
5. Open `dashboard/index.html` in a browser

## Usage

**Via dashboard:** Open `dashboard/index.html`, enter URLs (one per line, with `https://`), click Crawl. Node status updates live every 5 seconds.

**Via API directly:**
```bash
POST http://127.0.0.1:6060/crawl
Content-Type: application/json

{
  "urls": ["https://example.com", "https://github.com"]
}
```

Check node status:
```bash
GET http://127.0.0.1:6060/status
```

## Features Demonstrated

- Distributed URL assignment via consistent hashing (150 virtual nodes per worker)
- Automatic fault tolerance — node failures trigger live redistribution of pending work with zero data loss
- Distributed deduplication via Bloom filter (no URL scraped twice across nodes)
- Health-check based node monitoring (5-second heartbeat)
- Live dashboard for node status and crawl results

## Project Structure

```
NightCrawler/
  coordinator/
    coordinator.py       # Assigns work, health checks, fault tolerance
  worker/
    worker.py            # Scrapes pages, dedupes, stores results
  common/
    consistent_hash.py   # Hash ring implementation
    bloom_filter.py       # Distributed Bloom filter
  dashboard/
    index.html            # Live status + crawl UI
  README.md
```

## Final Statements

> Built a distributed crawling system using consistent hashing for URL distribution across worker nodes, distributed Bloom filters for deduplication, and automatic task redistribution on node failure via heartbeat protocol. Verified zero data loss during simulated node failures across 4 nodes.

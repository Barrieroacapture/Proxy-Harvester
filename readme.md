# 🚀 Async Hybrid Proxy Harvester

An asynchronous, high-concurrency Python script designed to scrape free proxies from multiple public online sources, validate them in real-time, and continuously update a local `proxies.txt` file[cite: 1].

## Features

* **Multi-Source Scraping**: Gathers raw proxies asynchronously from 12+ distinct public endpoints including ProxyScrape, Geonode, and popular GitHub repositories[cite: 1].
* **Intelligent Parsing**: Automatically processes standard text IP:Port lists as well as structured JSON API responses (such as Geonode's endpoint)[cite: 1].
* **High-Concurrency Validation**: Utilizes a `ThreadPoolExecutor` with up to 300 workers paired with optimized persistent HTTP adapters for rapid testing[cite: 1].
* **Live Health Checks**: Tests every scraped node against `https://httpbin.org/ip` with a strict timeout to ensure active status[cite: 1].
* **Automated Output Management**: Cleans, deduplicates, sorts, and writes active HTTP/HTTPS proxies directly to `proxies.txt` on every loop cycle[cite: 1].
* **Continuous Execution Loop**: Runs indefinitely with a 10-second cooldown between cycles, including native Windows Proactor event loop mitigation[cite: 1].

## Requirements

* Python 3.8 or higher[cite: 1]
* Required third-party libraries:
  ```bash
  pip install aiohttp requests urllib3

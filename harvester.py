import time
import re
import os
import sys
import asyncio
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

# Fix Windows Proactor warning/error clutter
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

PROXY_FILE = "proxies.txt"

# Massive multi-source configuration
PROXY_SOURCES = [
    ("ProxyScrape", "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=ipport&format=text&protocol=http"),
    ("Geonode", "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=http"),
    ("Databay API", "https://databay.com/api/v1/proxy-list?protocol=http&format=txt&limit=1000"),
    ("TheSpeedX HTTP", "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt"),
    ("Monosans HTTP", "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"),
    ("ProxyListDownload", "https://www.proxy-list.download/api/v1/get?type=http"),
    ("Proxifly HTTP", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/all/data.txt"),
    ("VPSLab HTTP All", "https://raw.githubusercontent.com/VPSLabCloud/VPSLab-Free-Proxy-List/main/http_all.txt"),
    ("VPSLab HTTP Elite", "https://raw.githubusercontent.com/VPSLabCloud/VPSLab-Free-Proxy-List/main/http_elite.txt"),
    ("Databay Raw HTTP", "https://raw.githubusercontent.com/databay-labs/free-proxy-list/master/http.txt"),
    ("Zedroid HTTP", "https://raw.githubusercontent.com/zedroid/free-proxy-list/main/proxies/http.txt"),
    ("hookzof HTTP", "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt")
]

async def fetch_source(session, name, url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    ip_port_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}\b')
    found_proxies = set()
    
    try:
        async with session.get(url, headers=headers, timeout=6) as resp:
            if resp.status == 200:
                text = await resp.text()
                if "geonode" in url.lower():
                    try:
                        data = await resp.json()
                        for item in data.get("data", []):
                            ip = item.get("ip")
                            port = item.get("port")
                            if ip and port:
                                found_proxies.add(f"{ip}:{port}")
                    except Exception:
                        pass
                else:
                    matches = ip_port_pattern.findall(text)
                    for m in matches:
                        found_proxies.add(m)
    except Exception as e:
        print(f"⚠️ [HARVESTER WARN] Failed from {name}: {e}")
        
    return found_proxies

async def fetch_raw_proxies_async():
    connector = aiohttp.TCPConnector(limit_per_host=15, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_source(session, name, url) for name, url in PROXY_SOURCES]
        results = await asyncio.gather(*tasks)
        raw_proxies = set()
        for res in results:
            raw_proxies.update(res)
        return list(raw_proxies)

# Persistent requests session optimized for high-concurrency validation
def create_requests_session():
    session = requests.Session()
    retries = Retry(total=0, connect=0, read=0)
    session.mount('http://', HTTPAdapter(max_retries=retries, pool_maxsize=400, pool_block=False))
    session.mount('https://', HTTPAdapter(max_retries=retries, pool_maxsize=400, pool_block=False))
    return session

thread_session = create_requests_session()

def test_single_proxy(ip_port):
    clean_ip_port = ip_port.replace("http://", "").strip()
    proxy_url = f"http://{clean_ip_port}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = thread_session.get(
            "https://httpbin.org/ip", 
            headers=headers,
            proxies={"http": proxy_url, "https": proxy_url}, 
            timeout=3.0
        )
        if r.status_code == 200:
            return proxy_url
    except Exception:
        pass
    return None

def validate_batch(raw_list):
    valid_batch = []
    with ThreadPoolExecutor(max_workers=300) as executor:
        results = executor.map(test_single_proxy, raw_list)
        for res in results:
            if res:
                valid_batch.append(res)
    return valid_batch

async def main_loop():
    print(f"[*] Starting Optimized Hybrid Proxy Harvester Engine. Saving live nodes to '{PROXY_FILE}'...")
    
    while True:
        try:
            # 1. Async Fetching
            start_time = time.time()
            raw_list = await fetch_raw_proxies_async()
            fetch_time = time.time() - start_time
            print(f"🔍 [HARVESTER] Fetched {len(raw_list)} raw proxies from {len(PROXY_SOURCES)} sources in {fetch_time:.2f}s. Validating with 300 threads...")
            
            # 2. Thread-pool Validation
            val_start = time.time()
            loop = asyncio.get_running_loop()
            valid_batch = await loop.run_in_executor(None, validate_batch, raw_list)
            val_time = time.time() - val_start
            print(f"⚡ [VALIDATOR] Validation completed in {val_time:.2f}s.")

            # 3. Auto-Clean and Save
            if valid_batch:
                unique_live_proxies = sorted(set(valid_batch))
                with open(PROXY_FILE, "w") as f:
                    for p in unique_live_proxies:
                        f.write(p + "\n")
                print(f"🧹 [CLEANED & SAVED] Active live proxy list updated. Total clean proxies in {PROXY_FILE}: {len(unique_live_proxies)}.\n")
            else:
                print(f"❌ [WARN] No valid proxies found in this batch. Retrying...\n")

            await asyncio.sleep(10)
        except Exception as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            print(f"⚠️ [LOOP WARN] {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[*] Proxy Harvester stopped safely by user.")
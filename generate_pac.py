import requests
import datetime
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import socket

# --- آدرس API ها ---
GEONODE_API_URL = "http://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=speed&sort_type=asc&protocols=http,https,socks5"
PROXYSCRAPE_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=all&timeout=5000&country=all"

TEST_URL = "http://www.google.com/"
MAX_PROXIES_IN_PAC = 50

PAC_TEMPLATE = """
function FindProxyForURL(url, host) {{
    if (isPlainHostName(host) ||
        shExpMatch(host, "*.local") ||
        isInNet(dnsResolve(host), "127.0.0.1", "255.255.255.255") ||
        isInNet(dnsResolve(host), "10.0.0.0", "255.0.0.0") ||
        isInNet(dnsResolve(host), "172.16.0.0", "255.240.0.0") ||
        isInNet(dnsResolve(host), "192.168.0.0", "255.255.0.0")) {{
        return "DIRECT";
    }}

    // Generated automatically on: {generation_date}
    // Number of active proxies: {proxy_count}
    return "{proxy_chain}";
}}
"""

def get_geonode_proxies():
    proxies = set()
    try:
        response = requests.get(GEONODE_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json().get('data', [])
        for proxy in data:
            ip, port = proxy['ip'], proxy['port']
            proxies.add(f"{ip}:{port}")
        print(f"Fetched {len(proxies)} proxies from Geonode.")
    except Exception as e:
        print(f"Error fetching Geonode proxies: {e}")
    return list(proxies)

def get_proxyscrape_proxies():
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_API_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        for line in lines:
            if line:
                proxies.add(line.strip())
        print(f"Fetched {len(proxies)} proxies from ProxyScrape.")
    except Exception as e:
        print(f"Error fetching ProxyScrape proxies: {e}")
    return list(proxies)

def test_proxy_speed(proxy):
    """تست اتصال و اندازه گیری زمان پاسخ"""
    try:
        start = time.time()
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        r = requests.get(TEST_URL, proxies=proxies, timeout=5)
        if r.status_code == 204:
            elapsed = time.time() - start
            return proxy, elapsed
    except Exception:
        pass
    return None

def generate_pac_file():
    all_proxies = list(set(get_geonode_proxies() + get_proxyscrape_proxies()))
    random.shuffle(all_proxies)
    print(f"\nTesting {len(all_proxies)} proxies for speed...")

    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_proxy = {executor.submit(test_proxy_speed, p): p for p in all_proxies}
        for future in as_completed(future_to_proxy):
            res = future.result()
            if res:
                results.append(res)

    if not results:
        print("No active proxies found.")
        proxy_chain_str = "DIRECT"
        final_count = 0
    else:
        # مرتب سازی براساس کمترین زمان پاسخ
        results.sort(key=lambda x: x[1])
        fastest = results[:MAX_PROXIES_IN_PAC]
        final_count = len(fastest)
        proxy_chain_str = "; ".join([f"PROXY {p[0]}" for p in fastest]) + "; DIRECT"

    generation_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pac_content = PAC_TEMPLATE.format(
        generation_date=generation_date,
        proxy_count=final_count,
        proxy_chain=proxy_chain_str
    )

    with open("dynamic.pac", "w") as f:
        f.write(pac_content)

    print(f"\nPAC file generated: {final_count} proxies active.")

if __name__ == "__main__":
    generate_pac_file()

import requests
import datetime
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# --- API های پراکسی ---
GEONODE_API_URL = "http://proxylist.geonode.com/api/proxy-list?limit=100&page=1&sort_by=speed&sort_type=asc&protocols=http,https"
PROXYSCRAPE_HTTP_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all"
PROXYSCRAPE_SOCKS4_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks4&timeout=5000&country=all"
PROXYSCRAPE_SOCKS5_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=5000&country=all"
PROXIFLY_API_URL = "https://api.proxifly.dev/v1/proxies/all"
PUBPROXY_API_URL = "http://pubproxy.com/api/proxy?limit=20&format=json&type=http,socks4,socks5"

TEST_URL = "http://detectportal.firefox.com/success.txt"
MAX_PROXIES_IN_PAC = 200
RETRY_COUNT = 2
TIMEOUT = 20

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
            proxies.add(('http', f"{ip}:{port}"))
        print(f"Fetched {len(proxies)} proxies from Geonode.")
    except Exception as e:
        print(f"Error fetching Geonode proxies: {e}")
    return list(proxies)

def get_proxyscrape_http_proxies():
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_HTTP_API_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        for line in lines:
            if line:
                proxies.add(('http', line.strip()))
        print(f"Fetched {len(proxies)} HTTP proxies from ProxyScrape.")
    except Exception as e:
        print(f"Error fetching ProxyScrape HTTP proxies: {e}")
    return list(proxies)

def get_proxyscrape_socks4_proxies():
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_SOCKS4_API_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        for line in lines:
            if line:
                proxies.add(('socks4', line.strip()))
        print(f"Fetched {len(proxies)} SOCKS4 proxies from ProxyScrape.")
    except Exception as e:
        print(f"Error fetching ProxyScrape SOCKS4 proxies: {e}")
    return list(proxies)

def get_proxyscrape_socks5_proxies():
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_SOCKS5_API_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        for line in lines:
            if line:
                proxies.add(('socks5', line.strip()))
        print(f"Fetched {len(proxies)} SOCKS5 proxies from ProxyScrape.")
    except Exception as e:
        print(f"Error fetching ProxyScrape SOCKS5 proxies: {e}")
    return list(proxies)

def get_proxifly_proxies():
    proxies = set()
    try:
        response = requests.get(PROXIFLY_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        for proxy_info in data:
            ip = proxy_info.get('ip')
            port = proxy_info.get('port')
            protocol = proxy_info.get('protocol', 'http').lower()
            if ip and port:
                proxies.add((protocol, f"{ip}:{port}"))
        print(f"Fetched {len(proxies)} proxies from Proxifly.")
    except Exception as e:
        print(f"Error fetching Proxifly proxies: {e}")
    return list(proxies)

def get_pubproxy_proxies():
    proxies = set()
    try:
        response = requests.get(PUBPROXY_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        for proxy_info in data:
            ip_port = proxy_info.get('ipPort')
            protocol = proxy_info.get('type', 'http').lower()
            if ip_port:
                proxies.add((protocol, ip_port.strip()))
        print(f"Fetched {len(proxies)} proxies from PubProxy.")
    except Exception as e:
        print(f"Error fetching PubProxy proxies: {e}")
    return list(proxies)

def test_proxy(proxy_info):
    protocol, address = proxy_info
    proxy_url_map = {
        'http': f"http://{address}",
        'https': f"http://{address}",
        'socks4': f"socks4://{address}",
        'socks5': f"socks5://{address}",
    }
    if protocol.lower() not in proxy_url_map:
        return None
    proxy_url = proxy_url_map[protocol.lower()]
    proxies_dict = {"http": proxy_url, "https": proxy_url}
    for _ in range(RETRY_COUNT):
        try:
            start_time = time.time()
            r = requests.get(TEST_URL, proxies=proxies_dict, timeout=TIMEOUT)
            if r.status_code == 204:
                elapsed = time.time() - start_time
                return (protocol, address.strip(), elapsed)
        except Exception:
            time.sleep(0.5)
    return None

def generate_pac_file():
    all_proxies = list(set(
        get_geonode_proxies() +
        get_proxyscrape_http_proxies() +
        get_proxyscrape_socks4_proxies() +
        get_proxyscrape_socks5_proxies() +
        get_proxifly_proxies() +
        get_pubproxy_proxies()
    ))
    random.shuffle(all_proxies)
    print(f"\nFound {len(all_proxies)} unique proxies. Testing for speed and availability...")
    results = []
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_proxy = {executor.submit(test_proxy, p): p for p in all_proxies}
        for i, future in enumerate(as_completed(future_to_proxy), 1):
            res = future.result()
            if res:
                results.append(res)
            print(f"\rProgress: {i}/{len(all_proxies)} | Active Found: {len(results)}", end="")
    print("\n")
    if not results:
        print("No active proxies found.")
        proxy_chain_str = "DIRECT"
        final_count = 0
    else:
        results.sort(key=lambda x: x[2])
        fastest = results[:MAX_PROXIES_IN_PAC]
        final_count = len(fastest)
        proxy_parts = []
        for protocol, address, _ in fastest:
            proto_upper = protocol.upper()
            if proto_upper in ['HTTP', 'HTTPS']:
                proxy_parts.append(f"PROXY {address}")
            elif proto_upper == 'SOCKS5':
                proxy_parts.append(f"SOCKS5 {address}")
            elif proto_upper == 'SOCKS4':
                proxy_parts.append(f"SOCKS {address}")
        proxy_chain_str = "; ".join(proxy_parts) + "; DIRECT"
    generation_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    pac_content = PAC_TEMPLATE.format(
        generation_date=generation_date,
        proxy_count=final_count,
        proxy_chain=proxy_chain_str
    )
    with open("dynamic.pac", "w") as f:
        f.write(pac_content)
    print(f"PAC file 'dynamic.pac' generated with {final_count} active proxies.")

if __name__ == "__main__":
    generate_pac_file()

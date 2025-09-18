import requests
import datetime
import random
from concurrent.futures import ThreadPoolExecutor

# --- آدرس API ها (با تعداد محدودتر) ---
GEONODE_API_URL = "http://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=speed&sort_type=asc&protocols=http"
PROXYSCRAPE_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all"

# --- URL برای تست کردن پراکسی ---
TEST_URL = "http://www.google.com/generate_204"
# --- حداکثر تعداد پراکسی در فایل نهایی ---
MAX_PROXIES_IN_PAC = 25


# --- قالب فایل PAC (با curly braces اصلاح شده) ---
PAC_TEMPLATE = """
function FindProxyForURL(url, host) {{
    // Bypass local IPs and direct connections
    if (isPlainHostName(host) ||
        shExpMatch(host, "*.local") ||
        isInNet(dnsResolve(host), "127.0.0.1", "255.255.255.255") ||
        isInNet(dnsResolve(host), "10.0.0.0", "255.0.0.0") ||
        isInNet(dnsResolve(host), "172.16.0.0", "255.240.0.0") ||
        isInNet(dnsResolve(host), "192.168.0.0", "255.255.0.0")) {{
        return "DIRECT";
    }}

    // --- PROXY CHAIN ---
    // Generated automatically on: {generation_date}
    // Number of active proxies: {proxy_count}
    return "{proxy_chain}";
}}
"""

def get_geonode_proxies():
    """پراکسی ها را از Geonode می گیرد"""
    proxies = set()
    try:
        response = requests.get(GEONODE_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json().get('data', [])
        for proxy in data:
            if 'http' in proxy.get('protocols', []):
                proxies.add(f"{proxy['ip']}:{proxy['port']}")
        print(f"Fetched {len(proxies)} proxies from Geonode.")
    except requests.RequestException as e:
        print(f"Error fetching from Geonode: {e}")
    return list(proxies)

def get_proxyscrape_proxies():
    """پراکسی ها را از ProxyScrape می گیرد"""
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_API_URL, timeout=15)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        for line in lines:
            if line:
                proxies.add(line.strip())
        print(f"Fetched {len(proxies)} proxies from ProxyScrape.")
    except requests.RequestException as e:
        print(f"Error fetching from ProxyScrape: {e}")
    return list(proxies)

def test_proxy(proxy_address):
    """یک پراکسی را تست می کند و در صورت فعال بودن آن را برمی گرداند"""
    try:
        proxies = {
            'http': f'http://{proxy_address}',
            'https': f'http://{proxy_address}'
        }
        response = requests.get(TEST_URL, proxies=proxies, timeout=3)
        if response.status_code == 204:
            print(f"  [SUCCESS] {proxy_address} is working.")
            return proxy_address
    except requests.RequestException:
        # print(f"  [FAILED] {proxy_address} is not working.")
        pass
    return None

def generate_pac_file():
    """فایل PAC نهایی را با پراکسی های تست شده تولید می کند"""
    geonode_proxies = get_geonode_proxies()
    proxyscrape_proxies = get_proxyscrape_proxies()

    # از set برای حذف موارد تکراری استفاده می کنیم
    all_proxies_raw = list(set(geonode_proxies + proxyscrape_proxies))
    random.shuffle(all_proxies_raw) # مخلوط کردن برای تست بهتر
    
    print(f"\nTesting {len(all_proxies_raw)} unique proxies...")
    
    # استفاده از تردها برای افزایش سرعت تست پراکسی ها
    active_proxies = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(test_proxy, all_proxies_raw)
        for result in results:
            if result:
                active_proxies.append(f"PROXY {result}")

    if not active_proxies:
        print("\nNo active proxies found. Aborting PAC file update.")
        return

    # محدود کردن تعداد پراکسی های نهایی و مخلوط کردن آنها
    random.shuffle(active_proxies)
    final_proxies = active_proxies[:MAX_PROXIES_IN_PAC]

    # ساخت رشته پراکسی برای فایل PAC
    proxy_chain_str = "; ".join(final_proxies) + "; DIRECT"
    
    generation_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    pac_content = PAC_TEMPLATE.format(
        generation_date=generation_date,
        proxy_count=len(final_proxies),
        proxy_chain=proxy_chain_str
    )
    
    with open("dynamic.pac", "w") as f:
        f.write(pac_content)
    
    print(f"\nSuccessfully generated dynamic.pac with {len(final_proxies)} active proxies.")

if __name__ == "__main__":
    generate_pac_file()

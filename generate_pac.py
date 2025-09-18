import requests
import datetime

# --- آدرس API ها ---
# منبع اول: Geonode (فقط پراکسی های HTTP با سرعت بالا را فیلتر می‌کنیم)
GEONODE_API_URL = "http://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=speed&sort_type=asc&protocols=http"

# منبع دوم: ProxyScrape (پراکسی های HTTP)
PROXYSCRAPE_API_URL = "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all"

# --- قالب فایل PAC ---
# از f-string برای جایگذاری لیست پراکسی‌ها در این قالب استفاده می‌کنیم
PAC_TEMPLATE = """
function FindProxyForURL(url, host) {
    // Bypass local IPs and direct connections
    if (isPlainHostName(host) ||
        shExpMatch(host, "*.local") ||
        isInNet(dnsResolve(host), "127.0.0.1", "255.255.255.255") ||
        isInNet(dnsResolve(host), "10.0.0.0", "255.0.0.0") ||
        isInNet(dnsResolve(host), "172.16.0.0", "255.240.0.0") ||
        isInNet(dnsResolve(host), "192.168.0.0", "255.255.0.0")) {
        return "DIRECT";
    }

    // --- PROXY CHAIN ---
    // Generated automatically on: {generation_date}
    // Proxies will be inserted here by the script.
    return "{proxy_chain}";
}
"""

def get_geonode_proxies():
    """پراکسی ها را از Geonode می گیرد و فرمت می کند"""
    proxies = set()
    try:
        response = requests.get(GEONODE_API_URL, timeout=15)
        response.raise_for_status() # Check for HTTP errors
        data = response.json().get('data', [])
        for proxy in data:
            # فقط پراکسی‌های HTTP را برای سادگی اضافه می‌کنیم
            if 'http' in proxy.get('protocols', []):
                proxies.add(f"PROXY {proxy['ip']}:{proxy['port']}")
        print(f"Successfully fetched {len(proxies)} proxies from Geonode.")
    except requests.RequestException as e:
        print(f"Error fetching from Geonode: {e}")
    return list(proxies)

def get_proxyscrape_proxies():
    """پراکسی ها را از ProxyScrape می گیرد و فرمت می کند"""
    proxies = set()
    try:
        response = requests.get(PROXYSCRAPE_API_URL, timeout=15)
        response.raise_for_status()
        # هر خط یک پراکسی ip:port است
        lines = response.text.strip().split('\\n')
        for line in lines:
            if line:
                proxies.add(f"PROXY {line.strip()}")
        print(f"Successfully fetched {len(proxies)} proxies from ProxyScrape.")
    except requests.RequestException as e:
        print(f"Error fetching from ProxyScrape: {e}")
    return list(proxies)

def generate_pac_file():
    """فایل PAC نهایی را تولید می کند"""
    geonode_proxies = get_geonode_proxies()
    proxyscrape_proxies = get_proxyscrape_proxies()

    all_proxies = geonode_proxies + proxyscrape_proxies
    
    if not all_proxies:
        print("No proxies fetched. Aborting PAC file update.")
        return

    # پراکسی‌ها را با "; " به هم متصل کرده و در انتها DIRECT را به عنوان fallback قرار می‌دهیم
    proxy_chain_str = "; ".join(all_proxies) + "; DIRECT"
    
    # تاریخ و زمان فعلی برای درج در فایل
    generation_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # محتوای نهایی فایل PAC
    pac_content = PAC_TEMPLATE.format(
        generation_date=generation_date,
        proxy_chain=proxy_chain_str
    )
    
    # نوشتن محتوا در فایل
    with open("dynamic.pac", "w") as f:
        f.write(pac_content)
    
    print(f"Successfully generated dynamic.pac with {len(all_proxies)} proxies.")

if __name__ == "__main__":
    generate_pac_file()

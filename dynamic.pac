
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
    // Generated automatically on: 2025-09-18 15:40:07 UTC
    // Number of active proxies: 25
    return "PROXY 157.180.121.252:36429; PROXY 110.76.145.6:8080; PROXY 157.180.121.252:54709; PROXY 27.72.143.112:10007; PROXY 157.180.121.252:22346; PROXY 213.35.105.30:8080; PROXY 64.110.118.98:8080; PROXY 157.180.121.252:29241; PROXY 157.180.121.252:29059; PROXY 157.180.121.252:44567; PROXY 104.238.30.17:54112; PROXY 223.205.71.203:8080; PROXY 185.235.16.12:80; PROXY 139.162.78.109:8080; PROXY 181.78.197.235:999; PROXY 45.22.209.157:8888; PROXY 41.59.90.171:80; PROXY 157.180.121.252:41587; PROXY 157.180.121.252:26969; PROXY 138.68.60.8:80; PROXY 157.180.121.252:21947; PROXY 157.180.121.252:10005; PROXY 157.180.121.252:41679; PROXY 90.162.35.34:80; PROXY 157.180.121.252:33105; DIRECT";
}

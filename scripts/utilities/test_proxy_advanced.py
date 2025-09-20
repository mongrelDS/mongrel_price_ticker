#!/usr/bin/env python3
"""
Advanced proxy testing with different configurations
"""

import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def test_proxy_variations():
    """Test different proxy configurations"""
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    target_url = "https://www.healthyplanetcanada.com/brands"
    
    # Different proxy formats to try
    proxy_formats = [
        # Format 1: Basic auth in URL
        f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
        
        # Format 2: HTTPS proxy
        f"https://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
        
        # Format 3: SOCKS5 (if supported)
        f"socks5://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
        
        # Format 4: HTTP with different port
        f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:8080",
    ]
    
    headers_variations = [
        # Headers 1: Standard Chrome
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        },
        
        # Headers 2: Mobile Chrome
        {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-CA,en;q=0.9',
            'Connection': 'keep-alive'
        },
        
        # Headers 3: Firefox
        {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    ]
    
    print("🔍 Testing different proxy configurations...")
    print("=" * 60)
    
    for i, proxy_url in enumerate(proxy_formats, 1):
        print(f"\n📡 Testing Format {i}: {proxy_url[:50]}...")
        
        for j, headers in enumerate(headers_variations, 1):
            print(f"  Headers {j}: {headers['User-Agent'][:50]}...")
            
            try:
                # Create session with retry strategy
                session = requests.Session()
                retry_strategy = Retry(
                    total=2,
                    backoff_factor=1,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
                adapter = HTTPAdapter(max_retries=retry_strategy)
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                # Configure proxy
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                session.proxies.update(proxies)
                session.headers.update(headers)
                
                # Test with simple URL first
                test_url = "http://httpbin.org/ip"
                response = session.get(test_url, timeout=15)
                
                if response.status_code == 200:
                    print(f"    ✅ Proxy working: {response.text[:100]}")
                    
                    # Now test target URL
                    print(f"    🎯 Testing target URL...")
                    response2 = session.get(target_url, timeout=30)
                    print(f"    📊 Target status: {response2.status_code}")
                    
                    if response2.status_code == 200:
                        print(f"    🎉 SUCCESS! Target URL accessible!")
                        return proxy_url, headers
                    elif response2.status_code == 403:
                        print(f"    ⚠️ Target blocked (DataDome), but proxy works")
                    else:
                        print(f"    ❌ Target failed: {response2.status_code}")
                else:
                    print(f"    ❌ Proxy failed: {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}")
            
            time.sleep(2)  # Be respectful
    
    return None, None

if __name__ == "__main__":
    working_proxy, working_headers = test_proxy_variations()
    
    if working_proxy:
        print(f"\n🎉 Found working configuration!")
        print(f"Proxy: {working_proxy}")
        print(f"Headers: {working_headers}")
    else:
        print(f"\n❌ No working configuration found")
        print("The proxy might not support HTTPS or the target site has very strong protection")

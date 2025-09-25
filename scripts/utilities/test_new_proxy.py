#!/usr/bin/env python3
"""
Test new proxy credentials with session ID
"""

import requests
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def test_new_proxy():
    """Test new proxy credentials"""
    print("🔍 Testing new proxy credentials...")
    
    # New proxy configuration
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    print(f"🌐 Proxy: {proxy_config['host']}:{proxy_config['port']}")
    print(f"👤 Username: {proxy_config['username']}")
    
    # Test URLs
    test_urls = [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip",
        "http://www.google.com",
        "https://www.google.com",
        "https://www.healthyplanetcanada.com"
    ]
    
    # Different proxy formats
    proxy_formats = [
        # Format 1: Basic auth in URL
        f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
        
        # Format 2: Separate auth
        f"http://{proxy_config['host']}:{proxy_config['port']}",
        
        # Format 3: HTTPS proxy
        f"https://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for i, proxy_url in enumerate(proxy_formats, 1):
        print(f"\n📡 Testing Format {i}: {proxy_url[:60]}...")
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        for test_url in test_urls:
            print(f"  Testing: {test_url}")
            try:
                if i == 2:  # Format 2 uses separate auth
                    auth = (proxy_config['username'], proxy_config['password'])
                    response = requests.get(test_url, proxies=proxies, auth=auth, headers=headers, timeout=15)
                else:
                    response = requests.get(test_url, proxies=proxies, headers=headers, timeout=15)
                
                print(f"    ✅ Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    📄 Response: {response.text[:200]}")
                    if "origin" in response.text or "healthyplanet" in response.text.lower():
                        print(f"    🎉 SUCCESS! Format {i} working with {test_url}")
                        return proxy_url, test_url
                else:
                    print(f"    ⚠️ Response: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}")
            
            time.sleep(1)
    
    return None, None

def test_new_proxy_with_session():
    """Test new proxy with session for better connection handling"""
    print("\n🔍 Testing new proxy with session...")
    
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    # Create session with retry strategy
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    })
    
    # Test different proxy configurations
    proxy_configs = [
        {
            'http': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
            'https': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
        },
        {
            'http': f"http://{proxy_config['host']}:{proxy_config['port']}",
            'https': f"http://{proxy_config['host']}:{proxy_config['port']}"
        }
    ]
    
    for i, proxies in enumerate(proxy_configs, 1):
        print(f"\n📡 Session Test {i}: {str(proxies)[:100]}...")
        
        try:
            if i == 2:  # Second config uses separate auth
                auth = (proxy_config['username'], proxy_config['password'])
                response = session.get("http://httpbin.org/ip", proxies=proxies, auth=auth, timeout=20)
            else:
                response = session.get("http://httpbin.org/ip", proxies=proxies, timeout=20)
            
            print(f"    ✅ Status: {response.status_code}")
            print(f"    📄 Response: {response.text[:200]}")
            
            if response.status_code == 200 and "origin" in response.text:
                print(f"    🎉 Session test {i} working!")
                
                # Test Healthy Planet
                print(f"    🌐 Testing Healthy Planet...")
                hp_response = session.get("https://www.healthyplanetcanada.com", proxies=proxies, timeout=30)
                print(f"    📊 HP Status: {hp_response.status_code}")
                
                if hp_response.status_code == 200:
                    print(f"    🎉 Healthy Planet accessible!")
                    return proxies
                else:
                    print(f"    ⚠️ Healthy Planet status: {hp_response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:100]}")
    
    return None

def main():
    """Main test function"""
    print("🚀 New Proxy Credentials Test")
    print("=" * 60)
    
    # Test 1: Basic requests
    print("\n" + "="*60)
    print("TEST 1: Basic Requests")
    print("="*60)
    proxy_url, test_url = test_new_proxy()
    
    if proxy_url:
        print(f"\n✅ Basic test successful!")
        print(f"Working proxy: {proxy_url}")
        print(f"Test URL: {test_url}")
    else:
        print(f"\n❌ Basic test failed")
    
    # Test 2: Session with retry
    print("\n" + "="*60)
    print("TEST 2: Session with Retry")
    print("="*60)
    proxies = test_new_proxy_with_session()
    
    if proxies:
        print(f"\n✅ Session test successful!")
        print(f"Working proxies: {proxies}")
    else:
        print(f"\n❌ Session test failed")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if proxy_url or proxies:
        print("✅ New proxy credentials are working!")
        print("Ready to use for Healthy Planet scraping")
        return True
    else:
        print("❌ New proxy credentials still not working")
        print("Possible issues:")
        print("  - Session ID may be expired")
        print("  - Proxy server configuration")
        print("  - Network connectivity issues")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Ready to create Healthy Planet scraper!")
    else:
        print("\n⚠️ Proxy still needs configuration")

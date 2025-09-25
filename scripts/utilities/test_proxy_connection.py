#!/usr/bin/env python3
"""
Test script to diagnose proxy connection issues
"""

import requests
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def test_proxy_basic():
    """Test basic proxy connection"""
    print("🔍 Testing basic proxy connection...")
    
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    # Test URLs
    test_urls = [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip",
        "http://www.google.com",
        "https://www.google.com"
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
        print(f"\n📡 Testing Format {i}: {proxy_url[:50]}...")
        
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
                    return proxy_url, test_url
                else:
                    print(f"    ⚠️ Response: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}")
            
            time.sleep(1)
    
    return None, None

def test_proxy_with_session():
    """Test proxy with session and retry strategy"""
    print("\n🔍 Testing proxy with session...")
    
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
            
            if response.status_code == 200:
                return proxies, "http://httpbin.org/ip"
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:100]}")
    
    return None, None

def test_proxy_curl_equivalent():
    """Test proxy using curl equivalent approach"""
    print("\n🔍 Testing proxy with curl equivalent...")
    
    import subprocess
    
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    # Test different curl commands
    curl_commands = [
        f"curl -x http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']} http://httpbin.org/ip",
        f"curl --proxy http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']} http://httpbin.org/ip",
        f"curl --proxy-user {proxy_config['username']}:{proxy_config['password']} --proxy {proxy_config['host']}:{proxy_config['port']} http://httpbin.org/ip"
    ]
    
    for i, cmd in enumerate(curl_commands, 1):
        print(f"\n📡 Curl Test {i}: {cmd[:80]}...")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            print(f"    Return code: {result.returncode}")
            print(f"    Output: {result.stdout[:200]}")
            print(f"    Error: {result.stderr[:200]}")
            
            if result.returncode == 0 and "origin" in result.stdout:
                print(f"    ✅ Curl test {i} successful!")
                return cmd
                
        except Exception as e:
            print(f"    ❌ Curl test {i} error: {e}")
    
    return None

def main():
    """Main test function"""
    print("🚀 Proxy Connection Diagnostic Tool")
    print("=" * 60)
    
    # Test 1: Basic requests
    print("\n" + "="*60)
    print("TEST 1: Basic Requests")
    print("="*60)
    proxy_url, test_url = test_proxy_basic()
    
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
    proxies, test_url = test_proxy_with_session()
    
    if proxies:
        print(f"\n✅ Session test successful!")
        print(f"Working proxies: {proxies}")
        print(f"Test URL: {test_url}")
    else:
        print(f"\n❌ Session test failed")
    
    # Test 3: Curl equivalent
    print("\n" + "="*60)
    print("TEST 3: Curl Equivalent")
    print("="*60)
    curl_cmd = test_proxy_curl_equivalent()
    
    if curl_cmd:
        print(f"\n✅ Curl test successful!")
        print(f"Working command: {curl_cmd}")
    else:
        print(f"\n❌ Curl test failed")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if proxy_url or proxies or curl_cmd:
        print("✅ At least one proxy method is working!")
        if proxy_url:
            print(f"  - Basic requests: {proxy_url}")
        if proxies:
            print(f"  - Session: {proxies}")
        if curl_cmd:
            print(f"  - Curl: {curl_cmd}")
    else:
        print("❌ All proxy methods failed")
        print("Possible issues:")
        print("  - Proxy server is down")
        print("  - Incorrect credentials")
        print("  - Network connectivity issues")
        print("  - Proxy doesn't support the requested protocol")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test script for residential proxy connection
"""

import requests
import time

def test_proxy_connection():
    """Test the residential proxy with different methods"""
    
    # Proxy configuration
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    test_url = "https://httpbin.org/ip"  # Simple test URL
    target_url = "https://www.healthyplanetcanada.com/brands"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("🔍 Testing proxy connection...")
    print(f"Proxy: {proxy_config['host']}:{proxy_config['port']}")
    print(f"Username: {proxy_config['username']}")
    print("=" * 50)
    
    # Method 1: Auth in URL
    print("\n📡 Method 1: Authentication in URL")
    try:
        proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        print(f"Testing with: {test_url}")
        response = requests.get(test_url, proxies=proxies, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Test with target URL
        print(f"\nTesting with target URL: {target_url}")
        response2 = requests.get(target_url, proxies=proxies, headers=headers, timeout=30)
        print(f"✅ Target Status: {response2.status_code}")
        if response2.status_code == 200:
            print("🎉 SUCCESS! Proxy is working with target URL!")
            return True
            
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
    
    # Method 2: Auth as tuple
    print("\n📡 Method 2: Authentication as tuple")
    try:
        auth = (proxy_config['username'], proxy_config['password'])
        proxy_url_simple = f"http://{proxy_config['host']}:{proxy_config['port']}"
        proxies_simple = {
            'http': proxy_url_simple,
            'https': proxy_url_simple
        }
        
        print(f"Testing with: {test_url}")
        response = requests.get(test_url, proxies=proxies_simple, auth=auth, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Test with target URL
        print(f"\nTesting with target URL: {target_url}")
        response2 = requests.get(target_url, proxies=proxies_simple, auth=auth, headers=headers, timeout=30)
        print(f"✅ Target Status: {response2.status_code}")
        if response2.status_code == 200:
            print("🎉 SUCCESS! Proxy is working with target URL!")
            return True
            
    except Exception as e:
        print(f"❌ Method 2 failed: {e}")
    
    # Method 3: Direct proxy without auth
    print("\n📡 Method 3: Direct proxy (no auth)")
    try:
        proxy_url_direct = f"http://{proxy_config['host']}:{proxy_config['port']}"
        proxies_direct = {
            'http': proxy_url_direct,
            'https': proxy_url_direct
        }
        
        print(f"Testing with: {test_url}")
        response = requests.get(test_url, proxies=proxies_direct, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Method 3 failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_proxy_connection()
    if not success:
        print("\n❌ All proxy methods failed")
        print("Possible issues:")
        print("- Incorrect proxy credentials")
        print("- Proxy server is down")
        print("- Network connectivity issues")
        print("- Proxy doesn't support HTTPS")
    else:
        print("\n✅ Proxy is working!")

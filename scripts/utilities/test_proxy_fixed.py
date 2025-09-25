#!/usr/bin/env python3
"""
Fixed test script for residential proxy connection
"""

import requests
import os
from requests.auth import HTTPProxyAuth
import time

def test_proxy_connection_fixed():
    """Test the residential proxy with proper 407 authentication"""
    
    # Proxy configuration
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    test_url = "https://httpbin.org/ip"  # Simple test URL
    target_url = "https://www.healthyplanetcanada.com/brands"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("🔍 Testing proxy connection with proper 407 auth...")
    print(f"Proxy: {proxy_config['host']}:{proxy_config['port']}")
    print(f"Username: {proxy_config['username']}")
    print("=" * 50)
    
    # Method 1: Using HTTPProxyAuth (proper 407 handling)
    print("\n📡 Method 1: HTTPProxyAuth (407 handling)")
    try:
        proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Use HTTPProxyAuth for proper 407 handling
        auth = HTTPProxyAuth(proxy_config['username'], proxy_config['password'])
        
        print(f"Testing with: {test_url}")
        response = requests.get(test_url, proxies=proxies, auth=auth, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Test with target URL
        print(f"\nTesting with target URL: {target_url}")
        response2 = requests.get(target_url, proxies=proxies, auth=auth, headers=headers, timeout=30)
        print(f"✅ Target Status: {response2.status_code}")
        if response2.status_code == 200:
            print("🎉 SUCCESS! Proxy is working with target URL!")
            return True
        elif response2.status_code == 403:
            print("⚠️ Target URL blocked (DataDome), but proxy is working!")
            return True
            
    except Exception as e:
        print(f"❌ Method 1 failed: {e}")
    
    # Method 2: Manual 407 handling
    print("\n📡 Method 2: Manual 407 handling")
    try:
        proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Create session for better control
        session = requests.Session()
        session.proxies.update(proxies)
        session.headers.update(headers)
        
        print(f"Testing with: {test_url}")
        response = session.get(test_url, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        # Test with target URL
        print(f"\nTesting with target URL: {target_url}")
        response2 = session.get(target_url, timeout=30)
        print(f"✅ Target Status: {response2.status_code}")
        if response2.status_code == 200:
            print("🎉 SUCCESS! Proxy is working with target URL!")
            return True
        elif response2.status_code == 403:
            print("⚠️ Target URL blocked (DataDome), but proxy is working!")
            return True
            
    except Exception as e:
        print(f"❌ Method 2 failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_proxy_connection_fixed()
    if not success:
        print("\n❌ All proxy methods failed")
        print("Possible issues:")
        print("- Incorrect proxy credentials")
        print("- Proxy server is down")
        print("- Network connectivity issues")
        print("- Proxy doesn't support HTTPS")
    else:
        print("\n✅ Proxy is working!")

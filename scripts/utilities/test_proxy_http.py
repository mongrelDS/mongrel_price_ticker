#!/usr/bin/env python3
"""
Test script for residential proxy with HTTP (not HTTPS)
"""

import requests
import os
from requests.auth import HTTPProxyAuth

def test_proxy_http():
    """Test the residential proxy with HTTP first"""
    
    # Proxy configuration
    proxy_config = {
        'host': os.getenv('PROXY_HOST', 'residential.ipb.cloud'),
        'port': os.getenv('PROXY_PORT', '7777'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    if not proxy_config['username'] or not proxy_config['password']:
        raise ValueError("Set PROXY_USERNAME and PROXY_PASSWORD in environment (no secrets in repo)")
    
    # Test with HTTP first
    test_url_http = "http://httpbin.org/ip"
    test_url_https = "https://httpbin.org/ip"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print("🔍 Testing proxy with HTTP first...")
    print(f"Proxy: {proxy_config['host']}:{proxy_config['port']}")
    print(f"Username: {proxy_config['username']}")
    print("=" * 50)
    
    # Test HTTP
    print("\n📡 Testing HTTP connection...")
    try:
        proxy_url = f"http://{proxy_config['host']}:{proxy_config['port']}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        auth = HTTPProxyAuth(proxy_config['username'], proxy_config['password'])
        
        print(f"Testing with: {test_url_http}")
        response = requests.get(test_url_http, proxies=proxies, auth=auth, headers=headers, timeout=30)
        print(f"✅ HTTP Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("🎉 HTTP proxy is working!")
            
            # Now test HTTPS
            print(f"\nTesting with: {test_url_https}")
            response2 = requests.get(test_url_https, proxies=proxies, auth=auth, headers=headers, timeout=30)
            print(f"✅ HTTPS Status: {response2.status_code}")
            if response2.status_code == 200:
                print("🎉 HTTPS proxy is working!")
                return True
            else:
                print("⚠️ HTTPS failed, but HTTP works")
                return True
        else:
            print("❌ HTTP also failed")
            
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
    
    # Try different proxy formats
    print("\n📡 Trying different proxy formats...")
    
    # Format 1: Username:password@host:port
    try:
        proxy_url_auth = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
        proxies_auth = {
            'http': proxy_url_auth,
            'https': proxy_url_auth
        }
        
        print(f"Format 1: {proxy_url_auth}")
        response = requests.get(test_url_http, proxies=proxies_auth, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Format 1 failed: {e}")
    
    # Format 2: Just host:port with auth
    try:
        proxy_url_simple = f"http://{proxy_config['host']}:{proxy_config['port']}"
        proxies_simple = {
            'http': proxy_url_simple,
            'https': proxy_url_simple
        }
        
        print(f"Format 2: {proxy_url_simple} with auth")
        auth_tuple = (proxy_config['username'], proxy_config['password'])
        response = requests.get(test_url_http, proxies=proxies_simple, auth=auth_tuple, headers=headers, timeout=30)
        print(f"✅ Status: {response.status_code}")
        print(f"Response: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Format 2 failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_proxy_http()
    if not success:
        print("\n❌ All proxy methods failed")
        print("The proxy credentials might be incorrect or the service is down")
    else:
        print("\n✅ Proxy is working!")

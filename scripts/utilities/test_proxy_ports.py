#!/usr/bin/env python3
"""
Test different proxy ports and configurations
"""

import requests
import time

def test_different_ports():
    """Test different proxy ports"""
    print("🔍 Testing different proxy ports...")
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    # Common proxy ports
    ports = [7777, 8080, 3128, 1080, 80, 443]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for port in ports:
        print(f"\n🌐 Testing port {port}...")
        proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{port}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            response = requests.get("http://httpbin.org/ip", proxies=proxies, headers=headers, timeout=10)
            print(f"  ✅ Status: {response.status_code}")
            print(f"  📄 Response: {response.text[:100]}")
            
            if response.status_code == 200 and "origin" in response.text:
                print(f"  🎉 Port {port} working!")
                return port
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
    
    return None

def test_different_auth_methods():
    """Test different authentication methods"""
    print("\n🔍 Testing different auth methods...")
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Different auth methods
    auth_methods = [
        # Method 1: Basic auth in URL
        {
            'proxies': {
                'http': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': None
        },
        # Method 2: Separate auth
        {
            'proxies': {
                'http': f"http://{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': (proxy_config['username'], proxy_config['password'])
        },
        # Method 3: Different format
        {
            'proxies': {
                'http': f"http://{proxy_config['username']}%40{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['username']}%40{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': None
        }
    ]
    
    for i, method in enumerate(auth_methods, 1):
        print(f"\n📡 Testing auth method {i}...")
        try:
            if method['auth']:
                response = requests.get("http://httpbin.org/ip", proxies=method['proxies'], auth=method['auth'], headers=headers, timeout=10)
            else:
                response = requests.get("http://httpbin.org/ip", proxies=method['proxies'], headers=headers, timeout=10)
            
            print(f"  ✅ Status: {response.status_code}")
            print(f"  📄 Response: {response.text[:100]}")
            
            if response.status_code == 200 and "origin" in response.text:
                print(f"  🎉 Auth method {i} working!")
                return method
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:50]}")
    
    return None

def main():
    """Main test function"""
    print("🚀 Proxy Port and Auth Testing")
    print("=" * 60)
    
    # Test different ports
    working_port = test_different_ports()
    
    # Test different auth methods
    working_auth = test_different_auth_methods()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if working_port:
        print(f"✅ Working port found: {working_port}")
    else:
        print("❌ No working port found")
    
    if working_auth:
        print(f"✅ Working auth method found")
    else:
        print("❌ No working auth method found")
    
    if working_port or working_auth:
        print("\n🎉 Proxy configuration found!")
        print("You can now use this configuration for scraping")
    else:
        print("\n❌ All proxy configurations failed")
        print("The proxy service may be down or credentials incorrect")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Test IPBurger proxy configuration
"""

import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def test_ipburger_proxy():
    """Test IPBurger proxy with correct configuration"""
    print("🔍 Testing IPBurger proxy configuration...")
    
    # IPBurger proxy configuration
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507-sessid-PshE-sesstime-30',
        'password': 'xyspgptxmm_J9v'
    }
    
    print(f"🌐 IPBurger Proxy: {proxy_config['host']}:{proxy_config['port']}")
    print(f"👤 Username: {proxy_config['username']}")
    
    # Test different IPBurger configurations
    configurations = [
        # Config 1: Standard HTTP proxy
        {
            'name': 'HTTP Proxy',
            'proxies': {
                'http': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': None
        },
        # Config 2: Separate auth
        {
            'name': 'HTTP Proxy with Separate Auth',
            'proxies': {
                'http': f"http://{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': (proxy_config['username'], proxy_config['password'])
        },
        # Config 3: SOCKS5 proxy
        {
            'name': 'SOCKS5 Proxy',
            'proxies': {
                'http': f"socks5://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
                'https': f"socks5://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': None
        }
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    }
    
    # Test URLs
    test_urls = [
        "http://httpbin.org/ip",
        "https://httpbin.org/ip",
        "https://www.healthyplanetcanada.com"
    ]
    
    for config in configurations:
        print(f"\n📡 Testing {config['name']}...")
        
        for test_url in test_urls:
            print(f"  🌐 Testing: {test_url}")
            try:
                if config['auth']:
                    response = requests.get(test_url, proxies=config['proxies'], auth=config['auth'], headers=headers, timeout=15)
                else:
                    response = requests.get(test_url, proxies=config['proxies'], headers=headers, timeout=15)
                
                print(f"    ✅ Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    📄 Response: {response.text[:200]}")
                    if "origin" in response.text or "healthyplanet" in response.text.lower():
                        print(f"    🎉 SUCCESS! {config['name']} working with {test_url}")
                        return config, test_url
                else:
                    print(f"    ⚠️ Response: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:100]}")
            
            time.sleep(1)
    
    return None, None

def test_ipburger_with_session():
    """Test IPBurger with session for better connection handling"""
    print("\n🔍 Testing IPBurger with session...")
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507-sessid-PshE-sesstime-30',
        'password': 'xyspgptxmm_J9v'
    }
    
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
    
    # Test IPBurger configurations
    proxy_configs = [
        {
            'name': 'HTTP with Session',
            'proxies': {
                'http': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': None
        },
        {
            'name': 'HTTP with Separate Auth',
            'proxies': {
                'http': f"http://{proxy_config['host']}:{proxy_config['port']}",
                'https': f"http://{proxy_config['host']}:{proxy_config['port']}"
            },
            'auth': (proxy_config['username'], proxy_config['password'])
        }
    ]
    
    for config in proxy_configs:
        print(f"\n📡 Testing {config['name']}...")
        
        try:
            if config['auth']:
                response = session.get("http://httpbin.org/ip", proxies=config['proxies'], auth=config['auth'], timeout=20)
            else:
                response = session.get("http://httpbin.org/ip", proxies=config['proxies'], timeout=20)
            
            print(f"    ✅ Status: {response.status_code}")
            print(f"    📄 Response: {response.text[:200]}")
            
            if response.status_code == 200 and "origin" in response.text:
                print(f"    🎉 {config['name']} working!")
                
                # Test Healthy Planet
                print(f"    🌐 Testing Healthy Planet...")
                hp_response = session.get("https://www.healthyplanetcanada.com", proxies=config['proxies'], timeout=30)
                print(f"    📊 HP Status: {hp_response.status_code}")
                
                if hp_response.status_code == 200:
                    print(f"    🎉 Healthy Planet accessible!")
                    return config
                else:
                    print(f"    ⚠️ Healthy Planet status: {hp_response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)[:100]}")
    
    return None

def main():
    """Main test function"""
    print("🚀 IPBurger Proxy Configuration Test")
    print("=" * 60)
    
    # Test 1: Basic configurations
    print("\n" + "="*60)
    print("TEST 1: Basic Configurations")
    print("="*60)
    config, test_url = test_ipburger_proxy()
    
    if config:
        print(f"\n✅ Basic test successful!")
        print(f"Working config: {config['name']}")
        print(f"Test URL: {test_url}")
    else:
        print(f"\n❌ Basic test failed")
    
    # Test 2: Session-based
    print("\n" + "="*60)
    print("TEST 2: Session-based Configuration")
    print("="*60)
    session_config = test_ipburger_with_session()
    
    if session_config:
        print(f"\n✅ Session test successful!")
        print(f"Working config: {session_config['name']}")
    else:
        print(f"\n❌ Session test failed")
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if config or session_config:
        print("✅ IPBurger proxy is working!")
        print("Ready to use for Healthy Planet scraping")
        return True
    else:
        print("❌ IPBurger proxy still not working")
        print("Possible issues:")
        print("  - Session ID may be expired")
        print("  - Account may be suspended")
        print("  - Need to check IPBurger dashboard")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Ready to create Healthy Planet scraper!")
    else:
        print("\n⚠️ Check IPBurger account status")

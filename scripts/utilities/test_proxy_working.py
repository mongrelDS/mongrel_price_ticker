#!/usr/bin/env python3
"""
Working proxy test using HTTPS tunneling
"""

import requests
import time

def test_proxy_https():
    """Test proxy with HTTPS requests only"""
    print("🔍 Testing proxy with HTTPS requests...")
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    # Use HTTPS proxy for both HTTP and HTTPS requests
    proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Test URLs (all HTTPS)
    test_urls = [
        "https://httpbin.org/ip",
        "https://www.google.com",
        "https://www.healthyplanetcanada.com"
    ]
    
    for test_url in test_urls:
        print(f"\n🌐 Testing: {test_url}")
        try:
            response = requests.get(test_url, proxies=proxies, headers=headers, timeout=30)
            print(f"  ✅ Status: {response.status_code}")
            print(f"  📄 Response length: {len(response.text)}")
            
            if test_url == "https://httpbin.org/ip":
                print(f"  📊 IP info: {response.text[:200]}")
            elif test_url == "https://www.healthyplanetcanada.com":
                if "healthyplanet" in response.text.lower():
                    print(f"  🎉 Successfully accessed Healthy Planet!")
                    return True
                else:
                    print(f"  ⚠️ Unexpected content: {response.text[:200]}")
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
    
    return False

def test_proxy_with_session():
    """Test proxy with session for better connection handling"""
    print("\n🔍 Testing proxy with session...")
    
    proxy_config = {
        'host': 'residential.ipb.cloud',
        'port': '7777',
        'username': 'customer-mnft29185901-asn-10507',
        'password': 'xyspgptxmm_J9v'
    }
    
    # Create session
    session = requests.Session()
    
    # Configure proxy
    proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
    session.proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    # Set headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    })
    
    # Test Healthy Planet specifically
    url = "https://www.healthyplanetcanada.com"
    print(f"🌐 Testing: {url}")
    
    try:
        response = session.get(url, timeout=30)
        print(f"  ✅ Status: {response.status_code}")
        print(f"  📄 Response length: {len(response.text)}")
        
        if response.status_code == 200:
            if "healthyplanet" in response.text.lower():
                print(f"  🎉 Successfully accessed Healthy Planet!")
                return True
            else:
                print(f"  ⚠️ Unexpected content: {response.text[:200]}")
        else:
            print(f"  ⚠️ Status {response.status_code}: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:100]}")
    
    return False

def main():
    """Main test function"""
    print("🚀 Working Proxy Test")
    print("=" * 60)
    
    # Test 1: Basic HTTPS requests
    print("\n" + "="*60)
    print("TEST 1: HTTPS Requests")
    print("="*60)
    success1 = test_proxy_https()
    
    # Test 2: Session-based requests
    print("\n" + "="*60)
    print("TEST 2: Session-based Requests")
    print("="*60)
    success2 = test_proxy_with_session()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    if success1 or success2:
        print("✅ Proxy is working!")
        print("The proxy can be used for scraping Healthy Planet")
        return True
    else:
        print("❌ Proxy is not working properly")
        print("Issues detected:")
        print("  - Proxy may not support the required protocols")
        print("  - Authentication may be incorrect")
        print("  - Network connectivity issues")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Ready to use proxy for scraping!")
    else:
        print("\n⚠️ Proxy needs further configuration")

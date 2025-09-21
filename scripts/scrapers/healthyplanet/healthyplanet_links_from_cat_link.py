#!/usr/bin/env python3
"""
Healthy Planet Links from Category Links with Playwright and Proxy Support
Uses Playwright for better anti-bot evasion and the centralized proxy configuration
"""

import pandas as pd
import asyncio
import sys
import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..', '..', '..', 'src')
src_dir_abs = os.path.abspath(src_dir)
sys.path.append(src_dir_abs)

# Import database functions and proxy configuration
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from database_config import get_database_engine
from proxy_config import (
    get_proxy_for_playwright, 
    get_proxy_config, 
    record_proxy_usage, 
    switch_proxy_credential,
    get_proxy_stats,
    test_proxy_connection
)

# Get database engine
db_engine = get_database_engine()

# Read brand links from database
print("Reading brand links from database...")
df_link = read_mysql_to_df(engine=db_engine, table_name='cat_link_list')
# keep only the links that start with https://www.healthyplanetcanada.com
df_link = df_link[df_link['link'].str.startswith('https://www.healthyplanetcanada.com')]
print(f"Found {len(df_link)} Healthy Planet links")

# Sample up to 20 links for testing (reduced for better success rate)
if len(df_link) >= 20:
    df_link = df_link.sample(20)
    print(f"Selected 20 links for processing")
else:
    print(f"Using all {len(df_link)} links for processing")

# CSS selectors for product elements
PRODUCT_SELECTORS = {
    'product_container': 'li.product-item',
    'name_link': 'a.product-item-link',
    'price': 'span.price',
    'image': 'img.product-image-photo'
}

async def test_proxy_connection_async(page, max_retries=3):
    """Test proxy connection with retry logic"""
    for attempt in range(max_retries):
        try:
            print(f"🔍 Testing proxy connection (attempt {attempt + 1}/{max_retries})...")
            test_response = await page.goto("http://httpbin.org/ip", timeout=15000)
            if test_response and test_response.status == 200:
                content = await page.text_content('body')
                print(f"✅ Proxy working! IP: {content}")
                return True
            else:
                print(f"❌ Proxy test failed: {test_response.status if test_response else 'No response'}")
                if attempt < max_retries - 1:
                    print("🔄 Switching proxy credential...")
                    switch_proxy_credential()
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Proxy test error: {e}")
            if attempt < max_retries - 1:
                print("🔄 Switching proxy credential...")
                switch_proxy_credential()
                await asyncio.sleep(2)
    return False

def get_enhanced_headers():
    """Get enhanced headers for better anti-bot evasion"""
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"'
    }

async def scrape_products_from_url_playwright(url, page, max_retries=3):
    """Scrapes all product details using Playwright with retry logic."""
    print(f" Scraping URL: {url}")
    
    page_products = []
    
    for attempt in range(max_retries):
        try:
            # Navigate to the URL
            response = await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Check response status
            if response and response.status == 200:
                # Wait for product containers to load
                try:
                    await page.wait_for_selector(PRODUCT_SELECTORS['product_container'], timeout=10000)
                except:
                    # If no products found, check if page loaded correctly
                    page_content = await page.content()
                    if 'product' in page_content.lower():
                        print(f"  ⚠️ Page loaded but no products found - attempt {attempt + 1}")
                    else:
                        print(f"  ⚠️ Page may be blocked - attempt {attempt + 1}")
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return page_products, "no_products"
                
                # Check for blocking indicators in page content
                page_text = await page.text_content('body')
                blocking_indicators = [
                    'access denied', 'blocked', 'captcha', 'cloudflare',
                    'rate limit', 'too many requests', 'suspicious activity'
                ]
                
                for indicator in blocking_indicators:
                    if indicator in page_text.lower():
                        print(f"  ⚠️ Blocking indicator found: '{indicator}' - attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                        return page_products, "content_blocked"
                
                # Find product containers
                product_containers = await page.query_selector_all(PRODUCT_SELECTORS['product_container'])
                
                for container in product_containers:
                    try:
                        # Extract product details
                        name_element = await container.query_selector(PRODUCT_SELECTORS['name_link'])
                        price_element = await container.query_selector(PRODUCT_SELECTORS['price'])
                        image_element = await container.query_selector(PRODUCT_SELECTORS['image'])
                        
                        if name_element and price_element and image_element:
                            name_text = await name_element.text_content()
                            price_text = await price_element.text_content()
                            link_href = await name_element.get_attribute('href')
                            image_src = await image_element.get_attribute('src')
                            
                            if name_text and price_text and link_href:
                                page_products.append({
                                    'item_name': name_text.strip(),
                                    'price': price_text.strip(),
                                    'link': link_href,
                                    'image_url': image_src or 'N/A'
                                })
                    except Exception as e:
                        print(f"    ⚠️ Error extracting product from container: {e}")
                        continue
                
                print(f"  ✅ Success on attempt {attempt + 1} - Found {len(page_products)} products")
                return page_products, "success"
                
            else:
                status_code = response.status if response else 'No response'
                print(f"  ⚠️ HTTP {status_code} - attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return page_products, f"http_{status_code}"
                
        except Exception as e:
            print(f"  -> Error scraping {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            return page_products, "error"
    
    return page_products, "max_retries_exceeded"

async def scrape_urls_without_proxy(urls):
    """Fallback scraping function without proxy"""
    all_products_data = []
    
    print("🌐 Running without proxy (fallback mode)")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers=get_enhanced_headers()
        )
        page = await context.new_page()
        
        # Set up request interception to block unnecessary resources
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
        
        successful_requests = 0
        failed_requests = 0
        
        for i, url in enumerate(urls, 1):
            print(f"\n📋 Processing link {i}/{len(urls)}: {url}")
            
            try:
                scraped_items, status = await scrape_products_from_url_playwright(url, page)
                
                if status == "success":
                    for item in scraped_items:
                        item['source_url'] = url
                        all_products_data.append(item)
                    print(f"  ✅ Found {len(scraped_items)} products")
                    successful_requests += 1
                else:
                    print(f"  ❌ Request failed: {status}")
                    failed_requests += 1
                
                # Adaptive delay
                delay = random.uniform(3, 6)
                print(f"  ⏱️ Waiting {delay:.1f}s before next request...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                print(f"  ❌ Error processing {url}: {e}")
                failed_requests += 1
                continue
        
        print(f"\n📊 Fallback Scraping Summary:")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Failed requests: {failed_requests}")
        if successful_requests + failed_requests > 0:
            print(f"  Success rate: {successful_requests/(successful_requests+failed_requests)*100:.1f}%")
        
        await browser.close()
    
    return all_products_data

async def scrape_urls_with_playwright(urls):
    """Scrapes multiple URLs using Playwright with enhanced proxy support."""
    all_products_data = []
    
    # Get proxy configuration
    proxy_config = get_proxy_for_playwright()
    print(f"🌐 Using proxy: {proxy_config['server']}")
    
    # Test proxy configuration before starting
    if not test_proxy_connection():
        print("❌ Proxy configuration is invalid!")
        return all_products_data
    
    async with async_playwright() as p:
        # Launch browser with proxy configuration
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers=get_enhanced_headers()
        )
        page = await context.new_page()
        
        # Set up request interception to block unnecessary resources
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
        
        # Test proxy connection with retry logic
        proxy_working = await test_proxy_connection_async(page)
        if not proxy_working:
            print("❌ All proxy credentials failed. Trying without proxy...")
            await browser.close()
            return await scrape_urls_without_proxy(urls)
        
        successful_requests = 0
        failed_requests = 0
        consecutive_failures = 0
        blocking_detected = False
        blocking_indicators_count = 0
        
        # Blocking detection thresholds
        MAX_CONSECUTIVE_FAILURES = 3
        MAX_BLOCKING_INDICATORS = 2
        
        def check_for_blocking(successful, failed, consecutive_fails, blocking_indicators=0):
            """Check if we're likely being blocked based on failure patterns."""
            if consecutive_fails >= MAX_CONSECUTIVE_FAILURES:
                return True, f"Too many consecutive failures ({consecutive_fails})"
            if blocking_indicators >= MAX_BLOCKING_INDICATORS:
                return True, f"Too many blocking indicators detected ({blocking_indicators})"
            return False, ""
        
        print(f"\n🚀 Starting scraping process...")
        print(f"📊 Processing {len(urls)} category links")
        
        for i, url in enumerate(urls, 1):
            # Check for blocking before processing each request
            if blocking_detected:
                print(f"🛑 Blocking detected! Stopping early at request {i}/{len(urls)}")
                break
            
            print(f"\n📋 Processing link {i}/{len(urls)}: {url}")
            
            try:
                scraped_items, status = await scrape_products_from_url_playwright(url, page)
                
                # Handle different response statuses
                if status == "success":
                    if len(scraped_items) == 0:
                        print(f"  ⚠️ No products found - potential blocking indicator")
                        consecutive_failures += 1
                        blocking_indicators_count += 1
                        record_proxy_usage(success=False)  # Record failed usage
                    else:
                        consecutive_failures = 0  # Reset on success
                        record_proxy_usage(success=True)  # Record successful usage
                    
                    for item in scraped_items:
                        item['source_url'] = url
                        all_products_data.append(item)
                    
                    print(f"  ✅ Found {len(scraped_items)} products")
                    successful_requests += 1
                    
                elif status in ["content_blocked", "no_products"]:
                    print(f"  🚨 Blocking indicator detected: {status}")
                    failed_requests += 1
                    consecutive_failures += 1
                    blocking_indicators_count += 1
                    record_proxy_usage(success=False)  # Record failed usage
                    
                elif status in ["http_403", "http_407", "http_429"]:
                    print(f"  🚨 HTTP {status.split('_')[1]} - switching proxy credential...")
                    failed_requests += 1
                    consecutive_failures += 1
                    record_proxy_usage(success=False)  # This will trigger credential switch
                    
                    # Try to get new proxy config and restart browser if needed
                    new_proxy_config = get_proxy_for_playwright()
                    print(f"  🔄 Switched to new proxy: {new_proxy_config['server']}")
                    
                else:
                    print(f"  ❌ Request failed: {status}")
                    failed_requests += 1
                    consecutive_failures += 1
                    record_proxy_usage(success=False)  # Record failed usage
                
                # Check for blocking after each request
                is_blocked, reason = check_for_blocking(successful_requests, failed_requests, consecutive_failures, blocking_indicators_count)
                if is_blocked:
                    blocking_detected = True
                    print(f"🚨 BLOCKING DETECTED: {reason}")
                    print(f"   Success rate: {successful_requests}/{successful_requests + failed_requests} ({successful_requests/(successful_requests + failed_requests)*100:.1f}%)")
                    break
                
                # Adaptive delay based on success rate
                if successful_requests > 0 and failed_requests > 0:
                    success_rate = successful_requests / (successful_requests + failed_requests)
                    if success_rate < 0.3:
                        delay = random.uniform(8, 15)  # Longer delay for low success rate
                    elif success_rate < 0.6:
                        delay = random.uniform(5, 10)  # Medium delay
                    else:
                        delay = random.uniform(3, 6)   # Normal delay
                else:
                    delay = random.uniform(4, 8)
                
                print(f"  ⏱️ Waiting {delay:.1f}s before next request...")
                await asyncio.sleep(delay)
                
            except Exception as e:
                print(f"  ❌ Error processing {url}: {e}")
                failed_requests += 1
                consecutive_failures += 1
                record_proxy_usage(success=False)  # Record failed usage
                
                # Check for blocking after each failed request
                is_blocked, reason = check_for_blocking(successful_requests, failed_requests, consecutive_failures, blocking_indicators_count)
                if is_blocked:
                    blocking_detected = True
                    print(f"🚨 BLOCKING DETECTED: {reason}")
                    break
                
                continue
        
        print(f"\n📊 Scraping Summary:")
        print(f"  Successful requests: {successful_requests}")
        print(f"  Failed requests: {failed_requests}")
        if successful_requests + failed_requests > 0:
            print(f"  Success rate: {successful_requests/(successful_requests+failed_requests)*100:.1f}%")
        print(f"  Consecutive failures: {consecutive_failures}")
        print(f"  Blocking indicators: {blocking_indicators_count}")
        if blocking_detected:
            print(f"  🚨 SCRAPING STOPPED EARLY DUE TO BLOCKING DETECTION")
        
        # Print proxy usage statistics
        print(f"\n🌐 Proxy Usage Statistics:")
        proxy_stats = get_proxy_stats()
        print(f"  Total credentials: {proxy_stats['total_credentials']}")
        print(f"  Active credential: {proxy_stats['active_credential']}")
        print(f"  Blocked credentials: {proxy_stats['blocked_credentials']}")
        for cred_info in proxy_stats['credentials']:
            print(f"    {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
        
        await browser.close()
    
    return all_products_data

def scrape_urls_sync(urls):
    """Synchronous wrapper for the async scraping function."""
    return asyncio.run(scrape_urls_with_playwright(urls))

# --- Main execution block ---
if __name__ == "__main__":
    print("🚀 Healthy Planet Links Scraper with Playwright - Starting...")
    
    # Record start time
    start_time = datetime.now()
    
    # Get URLs to scrape
    urls_to_scrape = df_link['link'].tolist()
    print(f"📊 URLs to scrape: {len(urls_to_scrape)}")
    
    # Scrape URLs
    print("\n🔍 Starting scraping process with Playwright...")
    all_products_data = scrape_urls_sync(urls_to_scrape)
    
    # --- Create DataFrame and Save to Database ---
    if all_products_data:
        df_products = pd.DataFrame(all_products_data)
        # dropna price
        df_products = df_products.dropna(subset=['price'])
        # drop column source_url
        df_products = df_products.drop(columns=['source_url'])
        print(f"\n✅ Total products scraped: {len(df_products)}")
        df_products['date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Import utility functions
        from price_to_float import price_to_float
        from cleanup_links import cleanup_link
        from get_domain import get_domain
        from generate_key import generate_key
        
        # price to float
        df_products['price'] = price_to_float(df_products, price_col='price', currency_marker='$')
        
        # cleanup link
        df_products = cleanup_link(df_products, column_name="link", base_domain=None, add_html_suffix=True)
        
        # get domain
        df_products['domain'] = get_domain(df_products, link_col='link')
        # rename column item_name to title
        df_products = df_products.rename(columns={'item_name': 'title'})
        # rename column image_url to imgurl
        df_products = df_products.rename(columns={'image_url': 'imgurl'})

        df_fixed_fields = df_products[['link','imgurl', 'title', 'domain']].copy()
        # upsert
        upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')

        df_ticker = df_products[['link', 'domain', 'price','date']]
        generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col='key')
        upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')



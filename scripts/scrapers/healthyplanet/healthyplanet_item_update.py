#!/usr/bin/env python3
"""
Healthy Planet Item Update with Enhanced Proxy Support
Uses Playwright for web scraping with automatic proxy credential switching
"""

import asyncio
import pandas as pd
import sys
import os
import datetime
import random
from datetime import date
from dotenv import load_dotenv
from playwright.async_api import async_playwright
load_dotenv()

# Add src directory to path and import centralized functions
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/scripts/analytics')
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql, read_mysql_to_df
from database_config import get_database_engine
from function_extract_volume import extract_volume
from generate_key import generate_key
from get_domain import get_domain
from df_price_30d import get_price_30d
from proxy_config import (
    get_proxy_for_playwright, 
    get_proxy_config, 
    record_proxy_usage, 
    get_proxy_stats,
    switch_proxy_credential
)

# Get database engine
db_engine = get_database_engine()

# duration tracking
df_duration = read_mysql_to_df(engine=db_engine, table_name='duration')
df_duration = df_duration[df_duration['domain'] == 'healthyplanet.ca']
df_duration = df_duration[df_duration['type'] == 'item_update']
df_duration = df_duration.sort_values(by='date', ascending=False)
df_duration = df_duration.head(1)
df_duration['result_per_minute'] = df_duration['result_per_minute'].astype(float)
n_20_minutes = int(df_duration['result_per_minute'].iloc[0] * 20)
print(f"Running {n_20_minutes} products for the next 20 minutes")

# get price 30d
df_link_healthyplanet = get_price_30d(domain='healthyplanetcanada.com')
# select all rows where price_30d_avg is null
df_link_healthyplanet = df_link_healthyplanet[df_link_healthyplanet['price_30d_avg'].isnull()]
# drop rows where [tag] is 'Failed'
df_link_healthyplanet = df_link_healthyplanet[df_link_healthyplanet['tag'] != 'Failed']
# sort date
df_link_healthyplanet = df_link_healthyplanet.sort_values(by='date', ascending=False)

# Read product links from database
print("Reading product links from database...")
df_link = read_mysql_to_df(engine=db_engine, table_name='healthyplanet_product_links')
df_link = df_link[df_link['link'].str.startswith('https://www.healthyplanetcanada.com')]
print(f"Found {len(df_link)} Healthy Planet product links")

# concat df_link and df_link_healthyplanet
df_link = pd.concat([df_link, df_link_healthyplanet])
# drop duplicate rows
df_link = df_link.drop_duplicates(subset='link', keep='first')
# drop rows where link is null
df_link = df_link.dropna(subset=['link'])

df_link = df_link.tail(n_20_minutes)
print(f"Selected {len(df_link)} products for the next 20 minutes")

# A dictionary to hold all our CSS selectors for easy access
SELECTORS = {
    'title': 'h1.page-title',
    'brand': 'span.brand-name a',
    'price': 'span.price',
    'sku': 'div.product.attribute.sku .value',
    'add_to_cart_btn': 'button#product-addtocart-button',
    'keywords': 'div.breadcrumbs li.item',
    'image': 'img#magnifier-item-0'
}

async def scrape_url_async(url, page, max_retries=3):
    """
    Scrapes a single product URL using Playwright with enhanced anti-bot evasion, retry logic and proxy switching.
    """
    print(f"-> Starting: {url}")
    
    product_details = {'link': url}
    
    for attempt in range(max_retries):
        try:
            # Add human-like behavior before navigation
            if attempt > 0:
                # Random mouse movement to simulate human behavior
                await page.mouse.move(
                    random.randint(100, 800), 
                    random.randint(100, 600)
                )
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Navigate to the URL with enhanced options
            response = await page.goto(
                url, 
                timeout=30000,
                wait_until='domcontentloaded'
            )
            
            if response and response.status == 200:
                # Add random delay to simulate human reading
                await asyncio.sleep(random.uniform(1, 3))
                
                # Simulate human scrolling behavior
                await page.evaluate("""
                    window.scrollTo({
                        top: Math.floor(Math.random() * 500),
                        behavior: 'smooth'
                    });
                """)
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
                # Wait for the title element to be present
                try:
                    await page.wait_for_selector(SELECTORS['title'], timeout=10000)
                    
                    # Additional human-like behavior
                    await page.mouse.move(
                        random.randint(200, 600), 
                        random.randint(200, 400)
                    )
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    
                    # Scrape all details with error handling
                    product_details['title'] = await page.text_content(SELECTORS['title']) or 'N/A'
                    product_details['brand'] = await page.text_content(SELECTORS['brand']) or 'N/A'
                    product_details['price'] = await page.text_content(SELECTORS['price']) or 'N/A'
                    product_details['sku'] = await page.text_content(SELECTORS['sku']) or 'N/A'
                    product_details['imgurl'] = await page.get_attribute(SELECTORS['image'], 'src') or 'N/A'
                    
                    # Check if add to cart button is enabled
                    try:
                        add_to_cart_button = await page.query_selector(SELECTORS['add_to_cart_btn'])
                        if add_to_cart_button:
                            is_enabled = await add_to_cart_button.is_enabled()
                            product_details['tag'] = 'In Stock' if is_enabled else 'Out of Stock'
                        else:
                            product_details['tag'] = 'Out of Stock'
                    except Exception:
                        product_details['tag'] = 'Out of Stock'
                    
                    # Get breadcrumb keywords
                    try:
                        breadcrumb_elements = await page.query_selector_all(SELECTORS['keywords'])
                        breadcrumb_texts = []
                        for elem in breadcrumb_elements:
                            text = await elem.text_content()
                            if text:
                                breadcrumb_texts.append(text.strip())
                        product_details['keywords'] = ' > '.join(breadcrumb_texts) if breadcrumb_texts else 'N/A'
                    except Exception:
                        product_details['keywords'] = 'N/A'
                    
                    # Final human-like delay before finishing
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    print(f"   <- Success: {url}")
                    record_proxy_usage(success=True)
                    return product_details
                    
                except Exception as e:
                    print(f"  -> Timeout or error waiting for elements (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        # Enhanced backoff with random jitter
                        backoff_delay = (2 ** attempt) + random.uniform(0, 1)
                        await asyncio.sleep(backoff_delay)
                        continue
                    product_details.update({k: 'Page Timeout' for k in ['title', 'brand', 'price', 'sku', 'tag', 'keywords', 'imgurl']})
            else:
                status_code = response.status if response else 'No response'
                print(f"  -> Failed to load page: {status_code} (attempt {attempt + 1})")
                
                # Check if it's a blocking response
                if status_code in [403, 429, 503]:
                    print(f"  🚫 Blocking detected (HTTP {status_code}) - switching proxy")
                    record_proxy_usage(success=False)
                    # Switch to next proxy credential
                    new_cred = switch_proxy_credential()
                    print(f"  🔄 Switched to {new_cred.city} proxy")
                    
                    # Update page context with new proxy (recreate context)
                    await page.context.close()
                    new_context = await page.context.browser.new_context(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        viewport={'width': 1920, 'height': 1080},
                        extra_http_headers={
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9',
                            'Accept-Encoding': 'gzip, deflate, br',
                            'Connection': 'keep-alive',
                            'Upgrade-Insecure-Requests': '1',
                            'Referer': 'https://www.google.com/',
                        }
                    )
                    page = await new_context.new_page()
                
                if attempt < max_retries - 1:
                    # Enhanced backoff with random jitter
                    backoff_delay = (2 ** attempt) + random.uniform(0, 2)
                    await asyncio.sleep(backoff_delay)
                    continue
                product_details.update({k: 'Page Load Failed' for k in ['title', 'brand', 'price', 'sku', 'tag', 'keywords', 'imgurl']})
                
        except Exception as e:
            print(f"  -> Error scraping {url} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                # Enhanced backoff with random jitter
                backoff_delay = (2 ** attempt) + random.uniform(0, 1.5)
                await asyncio.sleep(backoff_delay)
                continue
            product_details.update({k: 'Scraping Error' for k in ['title', 'brand', 'price', 'sku', 'tag', 'keywords', 'imgurl']})
    
    print(f"   <- Finished: {url}")
    record_proxy_usage(success=False)
    return product_details

async def scrape_urls_async(urls):
    """
    Scrapes multiple URLs using Playwright with enhanced anti-bot evasion and automatic proxy switching.
    """
    scraped_data_list = []
    
    # Get initial proxy configuration
    proxy_config = get_proxy_for_playwright()
    print(f"🌐 Using proxy: {proxy_config['server']}")
    
    async with async_playwright() as p:
        # Launch browser with enhanced anti-bot evasion
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy_config,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',
                '--disable-javascript',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-default-browser-check',
                '--no-pings',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        
        # Create context with enhanced anti-detection measures
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            screen={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York coordinates
            permissions=['geolocation'],
            extra_http_headers={
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
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'DNT': '1',
                'Referer': 'https://www.google.com/',
                'Origin': 'https://www.healthyplanetcanada.com'
            }
        )
        
        # Add stealth scripts to avoid detection
        await context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Mock chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Mock permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        page = await context.new_page()
        
        # Enhanced request interception for better performance and stealth
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot,css,js}", lambda route: route.abort())
        await page.route("**/analytics/**", lambda route: route.abort())
        await page.route("**/tracking/**", lambda route: route.abort())
        await page.route("**/ads/**", lambda route: route.abort())
        await page.route("**/facebook.com/**", lambda route: route.abort())
        await page.route("**/google-analytics.com/**", lambda route: route.abort())
        await page.route("**/googletagmanager.com/**", lambda route: route.abort())
        
        # Test proxy connection
        print("🔍 Testing proxy connection...")
        try:
            test_response = await page.goto("http://httpbin.org/ip", timeout=15000)
            if test_response and test_response.status == 200:
                content = await page.text_content('body')
                print(f"✅ Proxy working! IP: {content}")
            else:
                print(f"❌ Proxy test failed: {test_response.status if test_response else 'No response'}")
        except Exception as e:
            print(f"❌ Proxy test error: {e}")
        
        try:
            for i, url in enumerate(urls, 1):
                print(f"📊 Progress: {i}/{len(urls)} - {url}")
                
                # Check proxy stats periodically
                if i % 5 == 0:
                    stats = get_proxy_stats()
                    current_cred = get_proxy_config().get_current_credential()
                    print(f"  📈 Proxy Stats: {current_cred.city} (usage: {current_cred.usage_count}, blocked: {current_cred.is_blocked})")
                
                result = await scrape_url_async(url, page)
                scraped_data_list.append(result)
                
                # Adaptive delay based on success rate and proxy usage
                if i > 1:
                    # Calculate success rate
                    success_count = sum(1 for item in scraped_data_list[-10:] if item.get('title') not in ['Page Load Failed', 'Page Timeout', 'Scraping Error'])
                    success_rate = success_count / min(10, len(scraped_data_list))
                    
                    # Base delay with success rate adjustment
                    base_delay = 3.0
                    if success_rate < 0.5:
                        delay = base_delay + random.uniform(2, 5)  # Longer delay if struggling
                    elif success_rate > 0.8:
                        delay = base_delay + random.uniform(0.5, 2)  # Shorter delay if doing well
                    else:
                        delay = base_delay + random.uniform(1, 3)  # Normal delay
                    
                    # Add jitter to avoid pattern detection
                    jitter = random.uniform(-0.5, 0.5)
                    final_delay = max(1.0, delay + jitter)
                    
                    print(f"  ⏱️ Adaptive delay: {final_delay:.1f}s (success rate: {success_rate:.1%})")
                    await asyncio.sleep(final_delay)
                else:
                    # Initial delay
                    await asyncio.sleep(random.uniform(2, 4))
                
        finally:
            await browser.close()
    
    return scraped_data_list

def scrape_urls_sync(urls):
    """
    Synchronous wrapper for the async scraping function.
    """
    return asyncio.run(scrape_urls_async(urls))

# --- Main execution block ---
if __name__ == "__main__":
    print("🚀 Healthy Planet Item Update with Enhanced Proxy - Starting...")
    
    # Display initial proxy stats
    print("\n📊 Initial Proxy Configuration:")
    stats = get_proxy_stats()
    for cred_info in stats['credentials']:
        print(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
    
    # Record start time for duration tracking
    timestamp_0 = datetime.datetime.now()
    
    # Get URLs to scrape
    urls_to_scrape = df_link['link'].tolist()
    print(f"📊 URLs to scrape: {len(urls_to_scrape)}")
    
    # Scrape URLs
    print("\n🔍 Starting scraping process with enhanced proxy...")
    scraped_data_list = scrape_urls_sync(urls_to_scrape)
    
    # --- Final Steps ---
    df_product_info = pd.DataFrame(scraped_data_list)
    print(f"\n✅ Scraping complete! Scraped {len(df_product_info)} products")
    
    # Display final proxy stats
    print("\n📊 Final Proxy Statistics:")
    final_stats = get_proxy_stats()
    for cred_info in final_stats['credentials']:
        print(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
    
    # Display sample data
    if not df_product_info.empty:
        print("\n📋 Sample scraped data:")
        print(df_product_info.head())
        
        # Show data quality
        print(f"\n📊 Data quality summary:")
        for col in df_product_info.columns:
            if col != 'link':
                non_na_count = df_product_info[col].notna().sum()
                print(f"  {col}: {non_na_count}/{len(df_product_info)} ({non_na_count/len(df_product_info)*100:.1f}%)")
        
        # Process the data
        print("\n🔧 Processing scraped data...")
        
        try:
            # Extract volume from title
            print("  -> Extracting volume information...")
            df_product_info = extract_volume(df_product_info, vol_col="title", result_col="vol")
            
            # Cleanup price format
            print("  -> Cleaning price format...")
            df_product_info['price'] = df_product_info['price'].fillna('').astype(str).str.replace(r'[$,]', '', regex=True)
            df_product_info['price'] = pd.to_numeric(df_product_info['price'], errors='coerce')
            
            # Set 'price' to NaN where 'title' is 'Page Load Failed'
            df_product_info.loc[df_product_info['title'] == 'Page Load Failed', 'price'] = float('nan')
            df_product_info['date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Drop rows with invalid prices
            df_product_info = df_product_info[df_product_info['price'] != 0]
            df_product_info = df_product_info.dropna(subset=['price'])
            df_product_info['domain'] = get_domain(df_product_info, link_col='link')
            
            print(f"  -> After price cleanup: {len(df_product_info)} products")
            
            # Create fixed_fields DataFrame
            print("  -> Creating fixed_fields data...")
            df_fixed_fields = df_product_info[['link', 'sku', 'imgurl', 'title', 'brand', 'vol', 'keywords', 'domain']].copy()
            df_fixed_fields = df_fixed_fields[~df_fixed_fields['sku'].str.contains('Page Timed Out', na=False)]
            df_fixed_fields = df_fixed_fields[~df_fixed_fields['sku'].str.contains('Failed', na=False)]
            
            print(f"  -> Fixed fields: {len(df_fixed_fields)} products")
            
            # Upload fixed_fields to database
            print("  -> Uploading fixed_fields to database...")
            upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='sku')
            print("  ✅ Fixed fields uploaded successfully!")
            
            # Create df_ticker DataFrame
            print("  -> Creating ticker data...")
            df_ticker = df_product_info[['link', 'sku', 'price', 'tag', 'domain']].copy()
            df_ticker['date'] = date.today()  # date format YYYY-MM-DD
            df_ticker['price'] = pd.to_numeric(df_ticker['price'], errors='coerce')
            df_ticker = df_ticker.dropna(subset=['price'])  # dropna price
            
            # Generate key and remove duplicates
            print("  -> Generating keys and removing duplicates...")
            generate_key(df_ticker, deduplication_columns=['sku', 'date'], key_col='key')
            df_ticker = df_ticker.drop_duplicates(subset=['key'])
            df_ticker = df_ticker[df_ticker['price'] != 0]
            df_ticker = df_ticker.dropna(subset=['price'])
            
            print(f"  -> Ticker data: {len(df_ticker)} products")
            
            # Upload ticker data to database
            print("  -> Uploading ticker data to database...")
            upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
            print("  ✅ Ticker data uploaded successfully!")
            
            print(f"\n🎉 All processing complete!")
            print(f"📊 Final summary:")
            print(f"  - Products scraped: {len(scraped_data_list)}")
            print(f"  - Fixed fields: {len(df_fixed_fields)}")
            print(f"  - Ticker entries: {len(df_ticker)}")
            
            # Duration tracking
            print("\n⏱️ Calculating duration...")
            timestamp_1 = datetime.datetime.now()
            duration = timestamp_1 - timestamp_0
            duration_in_minutes = duration.total_seconds() / 60
            print(f"⏱️ Total duration: {duration_in_minutes:.2f} minutes")
            
            # Create duration tracking data
            df_duration = pd.DataFrame({
                'duration_min': [duration_in_minutes], 
                'date': [datetime.datetime.now()],
                'results': [len(df_ticker)],
                'domain': ['healthyplanetcanada.com'],
                'type': ['item_update']
            })
            df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
            
            print(f"📊 Performance metrics:")
            print(f"  - Duration: {duration_in_minutes:.2f} minutes")
            print(f"  - Results: {len(df_ticker)} products")
            print(f"  - Rate: {df_duration['result_per_minute'].iloc[0]:.2f} products/minute")
            
            # Upload duration data to database
            try:
                print("  -> Uploading duration data to database...")
                upsert_df_to_mysql(
                    df=df_duration, 
                    engine=db_engine, 
                    target_table='duration', 
                    key_col='date'
                )
                print("  ✅ Duration data uploaded successfully!")
            except Exception as e:
                print(f"  ⚠️ Duration data upload failed: {e}")
            
        except Exception as e:
            print(f"❌ Error during data processing: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ No data to process")
    
    print("\n🎉 Process complete!")

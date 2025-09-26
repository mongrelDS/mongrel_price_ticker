# @title Healthy Planet Product Details
# use playwright to scrape the product details
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import time
import sys
import os
from datetime import datetime
import logging
import traceback

# Add src folder to path to import MySQL functions
# Get the project root by going up from the current script location
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..', '..')
project_root = os.path.abspath(project_root)
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from database_config import get_database_engine, get_database_credentials
from price_to_float import price_to_float
from get_domain import get_domain
from function_extract_volume import extract_volume
from generate_key import generate_key

# Add analytics directory to path for get_price_30d import
analytics_dir = os.path.join(project_root, 'scripts', 'analytics')
sys.path.insert(0, analytics_dir)
from df_price_30d import get_price_30d

# Import proxy configuration
from proxy_config import get_proxy_for_playwright, get_proxy_config, record_proxy_usage, switch_proxy_credential, get_proxy_stats, test_proxy_connection, get_proxy_for_requests
import requests

# @title Configuration Constants
DOMAIN = 'healthyplanetcanada.com'
MAX_RECORDS = 100
MAX_RETRIES = 1
REQUEST_DELAY = 1.0  # seconds between requests
PROGRESS_LOG_INTERVAL = 10
PAGE_LOAD_TIMEOUT = 30000  # milliseconds
PAGE_WAIT_TIME = 3000  # milliseconds

# Global variable to store working proxy
WORKING_PROXY = None

# @title item Update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('healthyplanet_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def safe_database_operation(operation_func, *args, **kwargs):
    """Safely execute database operations with error handling and retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"Database operation failed after {max_retries} attempts: {str(e)}")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

def safe_data_processing(processing_func, df, *args, **kwargs):
    """Safely execute data processing functions with error handling"""
    try:
        return processing_func(df, *args, **kwargs)
    except Exception as e:
        logger.error(f"Data processing error in {processing_func.__name__}: {str(e)}")
        logger.error(f"DataFrame shape: {df.shape}")
        logger.error(f"DataFrame columns: {df.columns.tolist()}")
        # Return original DataFrame if processing fails
        return df


def test_proxy_connection_comprehensive():
    """Test proxy connection with actual network requests"""
    logger.info("🔍 Testing proxy connection...")
    
    try:
        # Get proxy configuration
        proxy_config = get_proxy_for_requests()
        logger.info(f"Using proxy: {proxy_config['http'][:50]}...")
        
        # Test URLs to check
        test_urls = [
            "https://httpbin.org/ip",
            "https://api.ipify.org?format=json",
            "https://www.healthyplanetcanada.com"
        ]
        
        session = requests.Session()
        session.proxies.update(proxy_config)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Test each URL
        for i, url in enumerate(test_urls, 1):
            try:
                logger.info(f"Testing URL {i}/{len(test_urls)}: {url}")
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully connected to {url}")
                    if "ipify" in url or "httpbin" in url:
                        try:
                            ip_data = response.json()
                            if 'ip' in ip_data:
                                logger.info(f"🌐 Current IP: {ip_data['ip']}")
                            elif 'origin' in ip_data:
                                logger.info(f"🌐 Current IP: {ip_data['origin']}")
                        except:
                            logger.info(f"📄 Response content: {response.text[:100]}...")
                    return True
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.ProxyError as e:
                logger.error(f"❌ Proxy error for {url}: {str(e)}")
                return False
            except requests.exceptions.Timeout as e:
                logger.error(f"⏰ Timeout for {url}: {str(e)}")
                return False
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Request error for {url}: {str(e)}")
                return False
        
        logger.info("✅ Proxy connection test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Proxy test failed: {str(e)}")
        return False

def test_proxy_with_playwright():
    """Test proxy connection using Playwright"""
    logger.info("🎭 Testing proxy with Playwright...")
    
    async def _test():
        try:
            async with async_playwright() as p:
                # Get proxy configuration
                proxy_config = get_proxy_for_playwright()
                logger.info(f"Using Playwright proxy: {proxy_config['server']}")
                
                # Launch browser with proxy
                browser = await p.chromium.launch(
                    headless=False,
                    proxy=proxy_config
                )
                
                page = await browser.new_page()
                
                # Test navigation to a simple page
                await page.goto("https://httpbin.org/ip", timeout=10000)
                content = await page.content()
                
                if "origin" in content or "ip" in content:
                    logger.info("✅ Playwright proxy test successful!")
                    # Extract IP if possible
                    try:
                        ip_element = await page.query_selector('pre')
                        if ip_element:
                            ip_text = await ip_element.text_content()
                            logger.info(f"🌐 Current IP: {ip_text}")
                    except:
                        pass
                    return True
                else:
                    logger.warning("⚠️ Playwright proxy test - unexpected response")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Playwright proxy test failed: {str(e)}")
            return False
        finally:
            if 'browser' in locals():
                await browser.close()
    
    return asyncio.run(_test())


# Initialize database engine using src folder configuration
try:
    db_engine = get_database_engine()
    logger.info("Database connection established successfully")
except Exception as e:
    logger.error(f"Failed to establish database connection: {str(e)}")
    sys.exit(1)

# Start timing
start_time = time.time()

# @title Proxy Testing
logger.info("=" * 60)
logger.info("🔍 PROXY CONNECTION TESTING")
logger.info("=" * 60)

# Test proxy configuration
proxy_config_valid = test_proxy_connection()
logger.info(f"Proxy configuration valid: {proxy_config_valid}")

if proxy_config_valid:
    # Test with requests library
    requests_test_passed = test_proxy_connection_comprehensive()
    
    if requests_test_passed:
        logger.info("✅ Primary proxy is working correctly!")
        WORKING_PROXY = "primary"
    else:
        logger.error("❌ Primary proxy failed!")
        logger.error("Will attempt to run without proxy...")
        WORKING_PROXY = "none"
else:
    logger.error("❌ Proxy configuration is invalid!")
    logger.error("Will attempt to run without proxy...")
    WORKING_PROXY = "none"

# Display proxy statistics
try:
    proxy_stats = get_proxy_stats()
    logger.info("📊 Proxy Statistics:")
    logger.info(f"  Total credentials: {proxy_stats['total_credentials']}")
    logger.info(f"  Active credential: {proxy_stats['active_credential']}")
    logger.info(f"  Blocked credentials: {proxy_stats['blocked_credentials']}")
    
    for i, cred_info in enumerate(proxy_stats['credentials']):
        status = "🚫 BLOCKED" if cred_info['is_blocked'] else "✅ ACTIVE"
        logger.info(f"  Credential {i+1} ({cred_info['city']}): {status} - Usage: {cred_info['usage_count']}")
        
except Exception as e:
    logger.warning(f"Could not retrieve proxy stats: {e}")

# Summary of proxy status
logger.info("=" * 60)
logger.info("📋 PROXY STATUS SUMMARY")
logger.info("=" * 60)
if WORKING_PROXY == "primary":
    logger.info("✅ Using PRIMARY proxy (IPBurger)")
else:
    logger.info("❌ No proxy available - running direct connection")
logger.info("=" * 60)

# @title Data Retrieval and Preparation
# Get 30-day price data
df_link = get_price_30d(domain=DOMAIN)

# Check if data was retrieved successfully
if df_link is None or df_link.empty:
    logger.error("No data retrieved from get_price_30d function. Exiting.")
    sys.exit(1)

# sort by date descending
df_link = df_link.sort_values(by='date', ascending=False)
df_link = df_link.drop_duplicates(subset='link', keep='first')
df_link = df_link.tail(MAX_RECORDS)

df_link = df_link[['link']]

logger.info(f'Retrieved {len(df_link)} product links for scraping')


# --- Scraper Configuration ---
scraped_data_list = [] # A list to hold dictionaries of scraped data

async def scrape_product_details(url, page, max_retries=MAX_RETRIES):
    """Scrape product details from a single URL using Playwright with retry mechanism"""
    logger.info(f"Scraping: {url}")
    
    for attempt in range(max_retries):
        try:
            # Navigate to the product page with timeout
            await page.goto(url, wait_until='networkidle', timeout=PAGE_LOAD_TIMEOUT)
            await page.wait_for_timeout(PAGE_WAIT_TIME)  # Wait for page to load
            
            # A dictionary to hold data for this single product
            product_details = {'link': url, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            # --- Scrape each field with detailed error handling ---
            try:
                title_element = await page.query_selector('h1.page-title')
                product_details['title'] = await title_element.text_content() if title_element else None
                logger.debug(f"Title scraped: {product_details['title']}")
            except Exception as e:
                logger.warning(f"Failed to scrape title for {url}: {str(e)}")
                product_details['title'] = None

            try:
                brand_element = await page.query_selector('span.brand-name a')
                product_details['brand'] = await brand_element.text_content() if brand_element else None
                logger.debug(f"Brand scraped: {product_details['brand']}")
            except Exception as e:
                logger.warning(f"Failed to scrape brand for {url}: {str(e)}")
                product_details['brand'] = None

            try:
                price_element = await page.query_selector('span.price')
                product_details['price'] = await price_element.text_content() if price_element else None
                logger.debug(f"Price scraped: {product_details['price']}")
            except Exception as e:
                logger.warning(f"Failed to scrape price for {url}: {str(e)}")
                product_details['price'] = None

            try:
                sku_element = await page.query_selector('div.product.attribute.sku .value')
                product_details['sku'] = await sku_element.text_content() if sku_element else None
                logger.debug(f"SKU scraped: {product_details['sku']}")
            except Exception as e:
                logger.warning(f"Failed to scrape SKU for {url}: {str(e)}")
                product_details['sku'] = None

            # --- REVISED: Updated logic for stock availability tag ---
            try:
                # Check for the "Add to Cart" button by its ID.
                add_to_cart_button = await page.query_selector('button#product-addtocart-button')
                if add_to_cart_button:
                    # Check if button is enabled
                    is_disabled = await add_to_cart_button.is_disabled()
                    if not is_disabled:
                        product_details['tag'] = 'In Stock'
                    else:
                        product_details['tag'] = 'Out of Stock'
                else:
                    product_details['tag'] = 'Out of Stock'
                logger.debug(f"Stock status scraped: {product_details['tag']}")
            except Exception as e:
                logger.warning(f"Failed to scrape stock status for {url}: {str(e)}")
                product_details['tag'] = 'Out of Stock'

            # --- Scrape the keywords (breadcrumbs) ---
            try:
                breadcrumb_elements = await page.query_selector_all('div.breadcrumbs li.item')
                breadcrumb_texts = []
                for elem in breadcrumb_elements:
                    text = await elem.text_content()
                    if text:
                        breadcrumb_texts.append(text.strip())
                product_details['keywords'] = ' > '.join(breadcrumb_texts) if breadcrumb_texts else None
                logger.debug(f"Keywords scraped: {product_details['keywords']}")
            except Exception as e:
                logger.warning(f"Failed to scrape keywords for {url}: {str(e)}")
                product_details['keywords'] = None

            logger.info(f"Successfully scraped product: {product_details['title']}")
            return product_details
            
        except Exception as e:
            logger.warning(f"Scraping attempt {attempt + 1}/{max_retries} failed for {url}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"All scraping attempts failed for {url}: {str(e)}")
                return {'link': url, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'title': None, 'brand': None, 'price': None, 'sku': None, 'tag': None, 'keywords': None}
            else:
                # Exponential backoff for retries
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                await page.wait_for_timeout(wait_time * 1000)

async def main():
    """Main async function to run the scraper with comprehensive error handling"""
    browser = None
    try:
        async with async_playwright() as p:
            # Configure browser launch based on working proxy (cron-safe headless mode)
            launch_options = {"headless": True}
            
            if WORKING_PROXY == "primary":
                # Use primary proxy
                proxy_config = get_proxy_for_playwright()
                launch_options["proxy"] = proxy_config
                logger.info("Using primary proxy configuration")
            else:
                logger.info("Running without proxy")
            
            # Launch browser
            browser = await p.chromium.launch(**launch_options)
            page = await browser.new_page()
            
            # Note: No extra HTTP headers are required for proxy; Playwright proxy is configured at launch
            
            # --- Loop Through Each Link in the DataFrame ---
            total_urls = len(df_link)
            successful_scrapes = 0
            failed_scrapes = 0
            consecutive_none_results = 0  # Track consecutive None results
            early_stop_threshold = 5  # Stop if first 5 links return None
            
            logger.info(f"Starting to scrape {total_urls} products")
            
            for i, url in enumerate(df_link['link'], 1):
                try:
                    logger.info(f"Processing product {i}/{total_urls}: {url}")
                    product_details = await scrape_product_details(url, page)
                    scraped_data_list.append(product_details)
                    
                    if product_details['title'] is not None:
                        successful_scrapes += 1
                        consecutive_none_results = 0  # Reset counter on successful scrape
                    else:
                        failed_scrapes += 1
                        consecutive_none_results += 1
                        
                        # Early stopping logic: if first 5 links return None, stop early
                        if i <= early_stop_threshold and consecutive_none_results == early_stop_threshold:
                            logger.warning(f"Early stopping: First {early_stop_threshold} links returned None results. Stopping scraping.")
                            break
                        
                    # Add rate limiting delay between requests
                    if i < total_urls:  # Don't delay after the last request
                        await asyncio.sleep(REQUEST_DELAY)
                        
                    # Progress logging at configured intervals
                    if i % PROGRESS_LOG_INTERVAL == 0:
                        success_rate = (successful_scrapes / i) * 100
                        logger.info(f"Progress: {i}/{total_urls} products processed. Success: {successful_scrapes}, Failed: {failed_scrapes}, Success Rate: {success_rate:.1f}%")
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {str(e)}")
                    failed_scrapes += 1
                    consecutive_none_results += 1
                    
                    # Early stopping logic: if first 5 links return None, stop early
                    if i <= early_stop_threshold and consecutive_none_results == early_stop_threshold:
                        logger.warning(f"Early stopping: First {early_stop_threshold} links returned None results. Stopping scraping.")
                        break
                    
                    # Add empty record to maintain count
                    scraped_data_list.append({
                        'link': url, 
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        'title': None, 
                        'brand': None, 
                        'price': None, 
                        'sku': None, 
                        'tag': None, 
                        'keywords': None
                    })
            
            logger.info(f"Scraping completed. Total: {total_urls}, Successful: {successful_scrapes}, Failed: {failed_scrapes}")
            
    except Exception as e:
        logger.error(f"Critical error in main scraping function: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        if browser:
            try:
                await browser.close()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

# Run the async main function with error handling
try:
    asyncio.run(main())
    logger.info("Main scraping function completed successfully")
except Exception as e:
    logger.error(f"Critical error in main execution: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Convert the list of dictionaries into a new DataFrame
try:
    results_df = pd.DataFrame(scraped_data_list)
    logger.info(f"Created DataFrame with {len(results_df)} products")
    
    if results_df.empty:
        logger.warning("No data was scraped. Exiting.")
        sys.exit(0)
        
except Exception as e:
    logger.error(f"Failed to create DataFrame: {str(e)}")
    sys.exit(1)

# Calculate duration
end_time = time.time()
duration_in_minutes = (end_time - start_time) / 60
logger.info(f"Scraping completed in {duration_in_minutes:.2f} minutes")

# Data processing with error handling
try:
    logger.info("Starting data processing...")
    
    # price to float
    results_df = safe_data_processing(price_to_float, results_df, price_col='price', currency_marker='$')
    logger.info("Price conversion completed")
    
    # domain
    results_df = safe_data_processing(get_domain, results_df, link_col='link')
    logger.info("Domain extraction completed")
    
    # extract vol from title
    results_df = safe_data_processing(extract_volume, results_df, vol_col='title', result_col='vol')
    logger.info("Volume extraction completed")
    
except Exception as e:
    logger.error(f"Data processing failed: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Database operations with error handling
try:
    logger.info("Starting database operations...")
    
    # Prepare fixed_fields data
    df_fixed_fields = results_df[['link', 'title', 'brand', 'sku', 'vol', 'keywords', 'domain']].copy()
    # dropna sku
    df_fixed_fields = df_fixed_fields.dropna(subset=['sku'])
    logger.info(f"Prepared fixed_fields data: {len(df_fixed_fields)} records")
    
    # Upsert to fixed_fields
    safe_database_operation(upsert_df_to_mysql, df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
    logger.info("Successfully updated fixed_fields table")
    
    # Prepare ticker data
    df_ticker = results_df[['link', 'sku', 'price', 'tag', 'domain', 'date']].copy()
    # dropna sku
    df_ticker = df_ticker.dropna(subset=['sku'])
    logger.info(f"Prepared ticker data: {len(df_ticker)} records")
    
    # Generate keys
    df_ticker = safe_data_processing(generate_key, df_ticker, deduplication_columns=['link', 'date'], key_col='key')
    logger.info("Key generation completed")
    
    # Upsert to df_ticker
    safe_database_operation(upsert_df_to_mysql, df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
    logger.info("Successfully updated df_ticker table")
    
    # Prepare duration data
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes], 
        'date': [datetime.now()], 
        'results': [len(df_ticker)], 
        'domain': [DOMAIN], 
        'type': ['item_update']
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    logger.info(f"Prepared duration data: {df_duration['result_per_minute'].iloc[0]:.2f} results per minute")
    
    # Upsert to duration
    safe_database_operation(upsert_df_to_mysql, df=df_duration, engine=db_engine, target_table='duration', key_col='date')
    logger.info("Successfully updated duration table")
    
    logger.info("All database operations completed successfully!")
    
except Exception as e:
    logger.error(f"Database operations failed: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

logger.info("Script execution completed successfully!")
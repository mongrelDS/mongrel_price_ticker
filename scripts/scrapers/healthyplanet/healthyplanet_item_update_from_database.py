# @title Healthy Planet Product Details
# use playwright to scrape the product details
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import time
import concurrent.futures
import sys
import os
from datetime import datetime
import logging
import traceback

# Add src folder to path to import MySQL functions
project_root = '/home/mongreldatalab/mongrel_price_ticker'
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from database_config import get_database_engine, get_database_credentials
from price_to_float import price_to_float
from get_domain import get_domain
from function_extract_volume import extract_volume
from generate_key import generate_key

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

# Initialize database engine using src folder configuration
try:
    db_engine = get_database_engine()
    logger.info("Database connection established successfully")
except Exception as e:
    logger.error(f"Failed to establish database connection: {str(e)}")
    sys.exit(1)

# Start timing
start_time = time.time()

try:
    df_link = safe_database_operation(read_mysql_to_df, engine=db_engine, table_name='fixed_fields')
    logger.info(f"Successfully loaded {len(df_link)} records from fixed_fields table")
except Exception as e:
    logger.error(f"Failed to load data from fixed_fields table: {str(e)}")
    sys.exit(1)
# df_link = df_link  where doain str includes healthyplanetcanada.com
df_link = df_link[df_link['domain'].str.contains('healthyplanetcanada.com')]
# select rows where sku is null
df_link = df_link[df_link['sku'].isnull()]
df_link = df_link.tail(90)

# use proxy_config to get proxy
from proxy_config import get_proxy_for_playwright, get_proxy_config, record_proxy_usage, switch_proxy_credential, get_proxy_stats, test_proxy_connection


# --- Scraper Configuration ---
scraped_data_list = [] # A list to hold dictionaries of scraped data

async def scrape_product_details(url, page, max_retries=3):
    """Scrape product details from a single URL using Playwright with retry mechanism"""
    logger.info(f"Scraping: {url}")
    
    for attempt in range(max_retries):
        try:
            # Navigate to the product page with timeout
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for page to load
            
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
                await page.wait_for_timeout(2000)  # Wait before retry

async def main():
    """Main async function to run the scraper with comprehensive error handling"""
    browser = None
    try:
        async with async_playwright() as p:
            # Launch browser with proxy configuration
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Set up proxy if available
            try:
                proxy_config = get_proxy_for_playwright()
                if proxy_config:
                    await page.context.set_extra_http_headers(proxy_config)
                    logger.info("Proxy configuration applied successfully")
            except Exception as e:
                logger.warning(f"Proxy setup failed: {e}")
            
            # --- Loop Through Each Link in the DataFrame ---
            total_urls = len(df_link)
            successful_scrapes = 0
            failed_scrapes = 0
            
            logger.info(f"Starting to scrape {total_urls} products")
            
            for i, url in enumerate(df_link['link'], 1):
                try:
                    logger.info(f"Processing product {i}/{total_urls}: {url}")
                    product_details = await scrape_product_details(url, page)
                    scraped_data_list.append(product_details)
                    
                    if product_details['title'] is not None:
                        successful_scrapes += 1
                    else:
                        failed_scrapes += 1
                        
                    # Progress logging every 10 products
                    if i % 10 == 0:
                        logger.info(f"Progress: {i}/{total_urls} products processed. Success: {successful_scrapes}, Failed: {failed_scrapes}")
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {str(e)}")
                    failed_scrapes += 1
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
    logger.info(f"Prepared fixed_fields data: {len(df_fixed_fields)} records")
    
    # Upsert to fixed_fields
    safe_database_operation(upsert_df_to_mysql, df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
    logger.info("Successfully updated fixed_fields table")
    
    # Prepare ticker data
    df_ticker = results_df[['link', 'sku', 'price', 'tag', 'domain', 'date']].copy()
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
        'domain': ['healthyplanetcanada.com'], 
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
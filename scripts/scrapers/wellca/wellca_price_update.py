#!/usr/bin/env python3
"""
Well.ca Price Update Script

This script scrapes product information from well.ca URLs and updates the database
with current pricing, availability, and product details. It processes products in
parallel for efficiency and includes comprehensive error handling and logging.

Features:
- Parallel web scraping with configurable thread count
- Database integration with MySQL
- Comprehensive error handling and logging
- Historical performance tracking
- Environment variable configuration for security

Requirements:
- All database credentials must be set in environment variables
- Required packages: pandas, requests, beautifulsoup4, sqlalchemy, python-dotenv
- Custom modules: mySQL_Upsert_Function_with_Batch, generate_key, df_price_30d

Author: Mongrel Data Lab
Date: 2024
"""

import pandas as pd
from datetime import date, datetime
import sys
import os
import logging
from dotenv import load_dotenv
import asyncio
from playwright.async_api import async_playwright, Browser as AsyncBrowser, Page as AsyncPage
import gc

# Establish project root and configure environment/import paths to work from any CWD
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Load environment variables from project root .env
env_path = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path=env_path)

# Add the src directory to the path so we can import our modules
src_path = os.path.join(PROJECT_ROOT, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import proxy configuration at module level
from proxy_config import get_proxy_for_requests, record_proxy_usage, get_proxy_stats, test_proxy_connection

# Configure logging
log_file = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'cron_jobs', 'wellca_price_update.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def get_product_info_async(url, browser: AsyncBrowser):
    """
    Async version of the Playwright scraper for better parallel processing.
    Uses a shared browser instance for efficiency.
    """
    try:
        page = await browser.new_page()
        
        # Set user agent
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        })
        
        # Navigate to the page
        response = await page.goto(url, timeout=60000)
        
        if response and response.status >= 400:
            logger.warning(f"HTTP error {response.status} for {url}")
            await page.close()
            record_proxy_usage(success=False)
            return None, None, None, pd.NA, 'Failed', None, None
        
        # Record successful proxy usage
        record_proxy_usage(success=True)
        
        # Wait for the page to load completely
        await page.wait_for_load_state('networkidle', timeout=15000)

        # --- Initialize variables to default values ---
        title = None
        brand = None
        breadcrumbs = None
        price = pd.NA
        tag = ''
        image_url = None
        size = None

        # -- Scrape Title --
        try:
            title_element = await page.query_selector('h1.product-info__title')
            if title_element:
                title = (await title_element.text_content()).strip()
        except Exception as e:
            logger.debug(f"Error scraping title for {url}: {e}")

        # -- Scrape Brand --
        try:
            brand_element = await page.query_selector('a.product-info__brand')
            if brand_element:
                brand = (await brand_element.text_content()).strip()
        except Exception as e:
            logger.debug(f"Error scraping brand for {url}: {e}")

        # -- Scrape Size --
        try:
            size_element = await page.query_selector('h5.product-info__subtitle span:nth-of-type(2)')
            if size_element:
                size = (await size_element.text_content()).strip()
        except Exception as e:
            logger.debug(f"Error scraping size for {url}: {e}")

        # -- Scrape Breadcrumbs --
        try:
            breadcrumb_elements = await page.query_selector_all('div.bread_crumb_container span[itemprop="name"]')
            if breadcrumb_elements:
                breadcrumb_list = []
                for elem in breadcrumb_elements:
                    text = await elem.text_content()
                    breadcrumb_list.append(text.strip())
                breadcrumbs = " > ".join(breadcrumb_list)
        except Exception as e:
            logger.debug(f"Error scraping breadcrumbs for {url}: {e}")

        # -- Determine Availability Tag --
        try:
            if await page.query_selector('div.product-info__unavailable--discontinued'):
                tag = 'Discontinued'
            elif await page.query_selector('input#add_to_cart_button'):
                tag = 'Add to Cart'
        except Exception as e:
            logger.debug(f"Error determining availability for {url}: {e}")

        # -- Determine Price --
        try:
            price_element = await page.query_selector('span[itemprop="price"]')
            if price_element:
                price_text = (await price_element.text_content()).strip().replace('$', '')
                price = float(price_text)
        except Exception as e:
            logger.debug(f"Error scraping price for {url}: {e}")

        # -- Scrape Image URL --
        try:
            image_element = await page.query_selector('#main-product-image')
            if image_element:
                image_url = await image_element.get_attribute('src')
        except Exception as e:
            logger.debug(f"Error scraping image URL for {url}: {e}")

        await page.close()
        
        # Return all scraped data, including the new size
        return title, brand, breadcrumbs, price, tag, image_url, size

    except Exception as e:
        # Handle any errors during scraping
        logger.error(f"An error occurred for {url}: {e}")
        
        # Record failed proxy usage and switch credentials if needed
        record_proxy_usage(success=False)
        
        # Return Nones for all fields and 'Failed' tag
        return None, None, None, pd.NA, 'Failed', None, None


async def scrape_urls_async(urls):
    """
    Async function to scrape multiple URLs using a shared browser instance.
    More efficient than creating a new browser for each URL.
    """
    proxy_config = get_proxy_for_requests()
    browser_options = {
        'headless': True,
        'timeout': 60000
    }
    
    # Add proxy configuration if available
    if proxy_config and 'http' in proxy_config:
        proxy_url = proxy_config['http']
        browser_options['proxy'] = {'server': proxy_url}
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(**browser_options)
        
        try:
            # Create tasks for all URLs
            tasks = [get_product_info_async(url, browser) for url in urls]
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions that occurred
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Exception for URL {urls[i]}: {result}")
                    processed_results.append((None, None, None, pd.NA, 'Failed', None, None))
                else:
                    processed_results.append(result)
            
            return processed_results
            
        finally:
            await browser.close()


async def scrape_urls_batched_async(urls, batch_size: int = 50, max_concurrency: int = 8):
    """
    Async scraping with a single shared browser and bounded concurrency.
    Processes URLs in batches to control memory usage.
    """
    proxy_config = get_proxy_for_requests()
    browser_options = {
        'headless': True,
        'timeout': 60000
    }

    if proxy_config and 'http' in proxy_config:
        proxy_url = proxy_config['http']
        browser_options['proxy'] = {'server': proxy_url}

    async with async_playwright() as p:
        browser = await p.firefox.launch(**browser_options)
        try:
            semaphore = asyncio.Semaphore(max_concurrency)

            async def bound_fetch(url: str):
                async with semaphore:
                    try:
                        return await get_product_info_async(url, browser)
                    except Exception as e:
                        logger.error(f"Exception during fetch for {url}: {e}")
                        return (None, None, None, pd.NA, 'Failed', None, None)

            all_results = []
            for i in range(0, len(urls), batch_size):
                batch = urls[i:i+batch_size]
                tasks = [asyncio.create_task(bound_fetch(u)) for u in batch]
                results = await asyncio.gather(*tasks, return_exceptions=False)
                all_results.extend(results)

                # Encourage GC between batches
                await asyncio.sleep(0)
            return all_results
        finally:
            await browser.close()


def main():
    """
    Main function to execute the Well.ca price update process
    """
    timestamp_0 = datetime.now() # timestamp_0 = time now
    logger.info(f"Script started at: {timestamp_0}")

    # Import database functions
    from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
    from generate_key import generate_key
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    # Import analytics function with absolute path (works from any CWD)
    analytics_path = os.path.join(PROJECT_ROOT, 'scripts', 'analytics')
    if analytics_path not in sys.path:
        sys.path.insert(0, analytics_path)
    from df_price_30d import get_price_30d

    # Test proxy connection after imports
    if test_proxy_connection():
        logger.info("✅ Proxy configuration validated successfully")
    else:
        logger.warning("⚠️ Proxy configuration validation failed - continuing without proxy")

    # Database connection setup (using environment variables)
    db_host = os.getenv('DB_HOST')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD')
    db_name = os.getenv('DB_NAME')

    # Validate that all required environment variables are set
    required_env_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    # Create database connection string
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

    # Create database engine
    db_engine = create_engine(connection_string, poolclass=NullPool)

    # manage the running duration
    try:
        df_duration = read_mysql_to_df(engine=db_engine, table_name='duration')
        # select rows where domain is well.ca  and type is price_update
        df_duration = df_duration[df_duration['domain'] == 'well.ca']
        df_duration = df_duration[df_duration['type'] == 'price_update']
        
        if len(df_duration) > 0:
            # calculate the average result_per_minute
            df_duration['result_per_minute'] = df_duration['result_per_minute'].astype(float)
            result_per_minute = df_duration['result_per_minute'].mean()
            n_20_minutes = int(result_per_minute * 20)
            
            # Ensure we have a reasonable number of products to process
            if n_20_minutes <= 0:
                n_20_minutes = 100  # Default fallback
                logger.warning("No historical data found, using default of 100 products")
            else:
                logger.info(f"Calculated {n_20_minutes} products based on historical performance")
        else:
            n_20_minutes = 100  # Default fallback
            logger.warning("No historical duration data found, using default of 100 products")
        
        logger.info(f"Running {n_20_minutes} products for the next 20 minutes")
    except Exception as e:
        logger.error(f"Error reading duration data: {e}")
        n_20_minutes = 100  # Default fallback
        logger.info(f"Using default of {n_20_minutes} products")

    # Product Links
    try:
        df_link = read_mysql_to_df(engine=db_engine, table_name='product_links')
        # Normalize to expected column name
        if 'product_url' not in df_link.columns:
            if 'link' in df_link.columns:
                df_link = df_link.rename(columns={'link': 'product_url'})
            elif 'url' in df_link.columns:
                df_link = df_link.rename(columns={'url': 'product_url'})
            else:
                logger.warning("product_links table missing 'product_url' column; creating empty frame")
                df_link = pd.DataFrame(columns=['product_url'])
        
        # keep rows where product_url starts with https://well.ca
        df_link = df_link[df_link['product_url'].str.startswith('https://well.ca')]
        
        if len(df_link) > 0:
            df_link = df_link.sample(min(len(df_link), n_20_minutes))
            logger.info(f"Selected {len(df_link)} product links from database")
        else:
            logger.warning("No product links found in database")
            df_link = pd.DataFrame(columns=['product_url'])
    except Exception as e:
        logger.error(f"Error reading product links: {e}")
        df_link = pd.DataFrame(columns=['product_url'])

    try:
        df_wellca = get_price_30d(domain='well.ca')
        # Only keep columns we need immediately and rename
        df_wellca = df_wellca[['link', 'tag', 'date']].rename(columns={'link': 'product_url'})
        # drop rows where [tag] is 'Failed' and sort by date desc
        df_wellca = df_wellca[df_wellca['tag'] != 'Failed']
        # keep rows where product_url starts with https://well.ca
        df_wellca = df_wellca[df_wellca['product_url'].str.startswith('https://well.ca')]
        df_wellca = df_wellca.sort_values(by='date', ascending=False)

        # Determine how many additional URLs we need to reach n_20_minutes
        needed = max(0, n_20_minutes - len(df_link))
        if needed > 0 and len(df_wellca) > 0:
            df_wellca = df_wellca[['product_url']].head(needed)
            df_link = pd.concat([df_link[['product_url']], df_wellca], ignore_index=True)
            logger.info(f"Added up to {len(df_wellca)} well.ca records to fill target count")
        else:
            logger.info("No additional well.ca records needed from history")
    except Exception as e:
        logger.error(f"Error reading well.ca data: {e}")

    # Clean and deduplicate
    df_link.drop_duplicates(subset='product_url', keep='first', inplace=True)
    df_link = df_link[['product_url']]
    if len(df_link) > n_20_minutes:
        df_link = df_link.tail(n_20_minutes)

    logger.info(f"Processing {len(df_link)} product URLs")

    # --- REVISED PARALLEL SCRAPING LOGIC ---
    logger.info("Scraping product info in parallel using Playwright... (this may take a moment)")

    # Create a list of URLs to process
    urls_to_scrape = df_link['product_url'].tolist()
    results = []

    # Use async Playwright for better performance and JavaScript handling
    try:
        max_concurrency = int(os.getenv('SCRAPE_MAX_CONCURRENCY', '8'))
        batch_size = int(os.getenv('SCRAPE_BATCH_SIZE', '50'))
        logger.info(f"Using async Playwright (Firefox) for parallel scraping (max_concurrency={max_concurrency}, batch_size={batch_size})...")
        results = asyncio.run(scrape_urls_batched_async(urls_to_scrape, batch_size=batch_size, max_concurrency=max_concurrency))
    except Exception as e:
        logger.error(f"Async scraping failed: {e}")
        raise

    # Create a new DataFrame from the results
    results_df = pd.DataFrame(results, columns=['title', 'brand', 'breadcrumbs', 'price', 'tag', 'image_url', 'size'])
    # Optimize dtypes to reduce memory
    if 'price' in results_df.columns:
        results_df['price'] = pd.to_numeric(results_df['price'], errors='coerce').astype('float32')
    if 'tag' in results_df.columns:
        results_df['tag'] = results_df['tag'].astype('category')

    # Reset the index of df_link before assignment to ensure alignment
    df_link = df_link.reset_index(drop=True)

    # Update the original DataFrame
    # We only update columns where the scrape was successful ('tag' is not 'Failed')
    successful_scrapes = results_df['tag'] != 'Failed'
    columns_to_update = ['title', 'brand', 'breadcrumbs', 'price', 'image_url', 'size']

    # Initialize the columns in df_link if they don't exist
    for col in columns_to_update:
        if col not in df_link.columns:
            df_link[col] = None

    # Update only successful scrapes
    df_link.loc[successful_scrapes, columns_to_update] = results_df.loc[successful_scrapes, columns_to_update]

    # Always update the tag and date for all rows
    df_link['tag'] = results_df['tag']
    df_link['date'] = date.today()

    logger.info("Scraping and updating complete.")
    # Free intermediates
    del results_df
    gc.collect()
    logger.info("-" * 50)
    
    # Log proxy usage statistics
    try:
        proxy_stats = get_proxy_stats()
        logger.info("📊 Proxy Usage Statistics:")
        logger.info(f"  Total credentials: {proxy_stats['total_credentials']}")
        logger.info(f"  Active credential: {proxy_stats['active_credential']}")
        logger.info(f"  Blocked credentials: {proxy_stats['blocked_credentials']}")
        for cred_info in proxy_stats['credentials']:
            logger.info(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
    except Exception as e:
        logger.warning(f"Could not retrieve proxy statistics: {e}")

    # Create new columns
    df_link['vol'] = df_link['size']
    df_link['imgurl'] = df_link['image_url']
    df_link['keywords'] = df_link['breadcrumbs']

    # Process URLs and extract SKU
    df_link['product_url'] = df_link['product_url'].str.replace('_', '/')
    df_link['sku'] = df_link['product_url'].str.extract(r'/([^/]+)\.html$')
    df_link['link'] = "https://well.ca/products/" + df_link['sku'].astype(str) + ".html"
    df_link['domain'] = 'well.ca'

    # Drop unnecessary columns
    df_link.drop(['breadcrumbs', 'image_url', 'size', 'product_url'], axis=1, inplace=True)

    # Display the final results
    logger.info("\nFinal results:")
    logger.info(f"DataFrame shape: {df_link.shape}")
    logger.info(f"Columns: {list(df_link.columns)}")

    # Process ticker data
    try:
        df_ticker = df_link[['link', 'sku', 'domain', 'price','date','tag']]
        generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col='key')
        upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
        logger.info(f"Successfully uploaded {len(df_ticker)} records to df_ticker table")
    except Exception as e:
        logger.error(f"Error uploading to df_ticker: {e}")

    # Process fixed fields
    try:
        fixed_fields = df_link[['link', 'imgurl', 'title', 'brand', 'sku', 'vol', 'keywords','domain']].copy()
        fixed_fields = fixed_fields.dropna(subset=['sku']) # dropna sku
        fixed_fields = fixed_fields[fixed_fields['sku'] != 'N/A'] # drop when sku is N/A

        # dropna link
        fixed_fields = fixed_fields.dropna(subset=['link'])

        # deduplicate
        fixed_fields = fixed_fields.drop_duplicates(subset='link', keep='first') # drop duplicate rows

        # upload to database
        upsert_df_to_mysql(df=fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='sku')
        logger.info(f"Successfully uploaded {len(fixed_fields)} records to fixed_fields table")
    except Exception as e:
        logger.error(f"Error uploading to fixed_fields: {e}")

    # @title Duration
    timestamp_1 = datetime.now()
    duration = timestamp_1 - timestamp_0
    duration_in_minutes = duration.total_seconds() / 60

    logger.info(f"The duration is: {duration_in_minutes} minutes")

    df_duration = pd.DataFrame({'duration_min': [duration_in_minutes], 'date': [datetime.now()]})
    df_duration['results'] = len(df_ticker)
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    df_duration['domain'] = 'well.ca'
    df_duration['type'] = 'price_update'

    logger.info(f"Duration DataFrame:\n{df_duration}")

    try:
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        logger.info("Successfully uploaded duration data")
    except Exception as e:
        logger.error(f"Error uploading duration data: {e}")

    logger.info("Script execution completed.")


if __name__ == "__main__":
    main()
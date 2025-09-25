#!/usr/bin/env python3
"""
Goodness Me Brand Links Scraper

This script scrapes all brand links from the Goodness Me website.
It extracts brand URLs from the brands page and upserts them to a MySQL table.
Additionally, it records duration metrics.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Import database configuration and upsert function
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql

# Configuration
DOMAIN = 'goodnessme.ca'
BASE_URL = 'https://goodnessme.ca/'
BRANDS_PATH = '/pages/brands-new'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_url(url):
    """Validate that a URL is properly formatted and from the expected domain."""
    if not url or not isinstance(url, str):
        return False
    return url.startswith('http') and DOMAIN in url


def scrape_brand_links(target_url, max_retries=3, retry_delay=1):
    """
    Scrape brand links from the Goodness Me website.
    
    Args:
        target_url (str): The URL to scrape
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
    
    Returns:
        list: List of brand URLs
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to scrape brand links from: {target_url} (attempt {attempt + 1}/{max_retries})")
            
            # Fetch the page content
            response = requests.get(target_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Strategy 1: Look for anchor tags within a vendor/brand list container
            selectors = [
                'li.vendor-list-item a',
                'a[href*="/collections/vendors?q="]',
                'a[href*="/collections/vendors?constraint="]',
                'a[href*="/collections/brands/"]',
            ]
            link_elements = []
            for selector in selectors:
                found = soup.select(selector)
                if found:
                    link_elements = found
                    break
            
            if not link_elements:
                # Fallback: all anchors under main content if structure changed
                link_elements = soup.select('main a, .main a, #MainContent a')
            
            all_links = []
            for element in link_elements:
                href = element.get('href')
                if not href:
                    continue
                full_url = urljoin(BASE_URL, href)
                if validate_url(full_url):
                    all_links.append(full_url)
            
            # Deduplicate while preserving order
            seen = set()
            unique_links = []
            for link in all_links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            logger.info(f"Successfully scraped {len(unique_links)} brand links")
            return unique_links
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error occurred (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise
    
    return []


def upsert_to_mysql(df_brand, table_name='brand_link_list'):
    """
    Upsert df_brand to MySQL table.
    """
    try:
        engine = get_database_engine()
        upsert_df_to_mysql(
            df=df_brand,
            engine=engine,
            target_table=table_name,
            key_col='brand_url',
            chunksize=1000
        )
        logger.info(f"Successfully upserted {len(df_brand)} brand links to {table_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert data to MySQL table {table_name}: {e}")
        return False


def main():
    """Main function to orchestrate the scraping process."""
    parser = argparse.ArgumentParser(description='Scrape brand links from goodnessme.ca and upsert to MySQL')
    parser.add_argument('-t', '--table', default='brand_link_list',
                       help='MySQL table name (default: brand_link_list)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    target_url = urljoin(BASE_URL, BRANDS_PATH)
    start_ts = time.time()
    
    try:
        # Scrape the brand links
        brand_links = scrape_brand_links(target_url)
        
        if not brand_links:
            logger.error("No brand links were found. Exiting.")
            sys.exit(1)
        
        # Build df_brand
        df_brand = pd.DataFrame(brand_links, columns=['brand_url'])
        logger.info(f"Found {len(df_brand)} brand links")
        logger.info("-" * 50)
        logger.info("Sample of the data:")
        logger.info(f"\n{df_brand.head().to_string(index=False)}")
        logger.info("-" * 50)
        
        # Upsert df_brand
        if not upsert_to_mysql(df_brand, args.table):
            logger.error("❌ Failed to upsert df_brand to MySQL table")
            sys.exit(1)
        
        # Duration metrics
        end_ts = time.time()
        duration_in_minutes = (end_ts - start_ts) / 60.0
        df_duration = pd.DataFrame({
            'duration_min': [duration_in_minutes],
            'date': [datetime.now()],
            'results': [len(df_brand)],
            'domain': [DOMAIN],
            'type': ['brand_crawl'],
        })
        df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
        db_engine = get_database_engine()
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        
        logger.info("✅ Scraping and database upserts completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Nature Santé Brand Links Scraper

This script scrapes all brand links from the Nature Santé website.
It extracts brand URLs from the brands page and upserts them to a MySQL table.
"""

import argparse
import logging
import sys
import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Import database configuration and upsert function
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql

# Configuration
BASE_URL = 'https://naturesante.ca'
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
    return url.startswith('http') and 'naturesante.ca' in url


def scrape_brand_links(target_url, max_retries=3, retry_delay=1):
    """
    Scrape brand links from the Nature Santé website.
    
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
            
            # Find all link elements using the correct CSS selector
            link_elements = soup.select('li.vendor-list-item a')
            
            if not link_elements:
                logger.warning("No links found with the selector 'li.vendor-list-item a'. The website structure may have changed.")
                return []
            
            # Extract the 'href' and create full URLs
            all_links = []
            for element in link_elements:
                href = element.get('href')
                if href:
                    full_url = urljoin(BASE_URL, href)
                    if validate_url(full_url):
                        all_links.append(full_url)
                    else:
                        logger.warning(f"Invalid URL found: {full_url}")
            
            logger.info(f"Successfully scraped {len(all_links)} brand links")
            return all_links
            
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


def upsert_to_mysql(brand_links, table_name='brand_link_list'):
    """
    Upsert brand links to MySQL table.
    
    Args:
        brand_links (list): List of brand URLs to upsert
        table_name (str): Name of the MySQL table
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create DataFrame with brand URLs only (matching existing table structure)
        df = pd.DataFrame(brand_links, columns=['brand_url'])
        
        # Get database engine
        engine = get_database_engine()
        
        # Upsert to MySQL using brand_url as the key
        upsert_df_to_mysql(
            df=df,
            engine=engine,
            target_table=table_name,
            key_col='brand_url',
            chunksize=1000  # Process in batches of 1000
        )
        
        logger.info(f"Successfully upserted {len(brand_links)} brand links to {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to upsert data to MySQL table {table_name}: {e}")
        return False


def main():
    """Main function to orchestrate the scraping process."""
    parser = argparse.ArgumentParser(description='Scrape brand links from Nature Santé website and upsert to MySQL')
    parser.add_argument('-t', '--table', default='brand_link_list',
                       help='MySQL table name (default: brand_link_list)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Construct the target URL
    target_url = urljoin(BASE_URL, '/pages/brands')
    
    try:
        # Scrape the brand links
        brand_links = scrape_brand_links(target_url)
        
        if not brand_links:
            logger.error("No brand links were found. Exiting.")
            sys.exit(1)
        
        # Display sample data
        logger.info(f"Found {len(brand_links)} brand links")
        logger.info("-" * 50)
        logger.info("Sample of the data:")
        sample_df = pd.DataFrame(brand_links[:5], columns=['brand_url'])
        logger.info(f"\n{sample_df.to_string(index=False)}")
        logger.info("-" * 50)
        
        # Upsert to MySQL
        if upsert_to_mysql(brand_links, args.table):
            logger.info("✅ Scraping and database upsert completed successfully!")
        else:
            logger.error("❌ Failed to upsert data to MySQL table")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
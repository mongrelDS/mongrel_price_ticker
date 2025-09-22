#!/usr/bin/env python3
"""
Nature Santé Product Links Scraper

This script scrapes product links from Nature Santé brand pages using Playwright with Firefox.
It extracts product URLs and stores them in the df_product_url table with domain information.
"""

import sys
import os
import pandas as pd
import asyncio
from urllib.parse import urljoin
from tqdm import tqdm
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time

# Add the src directory to the path so we can import our modules
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import database functions and utilities
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from database_config import get_database_engine

# --- Configuration ---
BASE_URL = 'https://naturesante.ca'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

async def scrape_brand_page(page, source_url):
    """
    Scrape product links from a single brand page using Playwright.
    
    Args:
        page: Playwright page object
        source_url (str): URL of the brand page to scrape
        
    Returns:
        list: List of product URLs found on the page
    """
    try:
        # Navigate to the brand page
        await page.goto(source_url, wait_until='domcontentloaded', timeout=30000)
        
        # Wait a bit for JavaScript to load products
        await page.wait_for_timeout(5000)
        
        # Wait for product links to appear
        await page.wait_for_selector('a.product-thumb-href', timeout=10000)
        
        # Get page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find all product links
        product_elements = soup.select('a.product-thumb-href')
        
        # Extract URLs
        product_urls = []
        for element in product_elements:
            relative_path = element.get('href')
            if relative_path:
                full_url = urljoin(BASE_URL, relative_path)
                product_urls.append(full_url)
        
        return product_urls
        
    except Exception as e:
        print(f"⚠️ Could not process {source_url}. Error: {e}")
        return []

async def main():
    """
    Main function to scrape product links from Nature Santé brand pages.
    """
    print("🚀 Starting Nature Santé Product Links Scraper")
    print("=" * 60)
    
    # Database connection
    try:
        db_engine = get_database_engine()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Load brand links from database
    try:
        df_link = read_mysql_to_df(engine=db_engine, table_name='brand_link_list')
        print(f"📊 Total brand links in database: {len(df_link)}")
        
        # Keep only the links that contain naturesante.ca
        df_link = df_link[df_link['brand_url'].str.contains('naturesante.ca', na=False)]
        print(f"📊 Nature Santé brand links found: {len(df_link)}")
        
        if len(df_link) == 0:
            print("❌ No Nature Santé brand links found in database")
            return False
        
        # Sample up to 10 links for testing, or all if less than 10
        sample_size = min(30, len(df_link))
        df_link = df_link.sample(sample_size)
        print(f"✅ Loaded {len(df_link)} brand URLs from database")
    except Exception as e:
        print(f"❌ Failed to load brand links: {e}")
        return False
    
    # Initialize Playwright with Firefox
    all_pdp_links = []
    
    async with async_playwright() as p:
        # Launch Firefox browser
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent=HEADERS['User-Agent']
        )
        page = await context.new_page()
        
        print(f"🔍 Starting to scrape {len(df_link)} brand pages for product links...")
        
        # Scrape each brand page
        for source_url in tqdm(df_link['brand_url'], desc="Scraping Brand Pages"):
            product_urls = await scrape_brand_page(page, source_url)
            all_pdp_links.extend(product_urls)
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        # Close browser
        await browser.close()
    
    # Process results
    unique_pdp_links = list(set(all_pdp_links))
    print(f"\n✅ Scraping complete.")
    print(f"Found {len(unique_pdp_links)} unique product links.")
    
    if not unique_pdp_links:
        print("❌ No product links found. Exiting.")
        return False
    
    # Create DataFrame with links
    df_pdp_links = pd.DataFrame(unique_pdp_links, columns=['link'])
    
    print("\n--- Sample of the resulting DataFrame ---")
    print(df_pdp_links.head())
    print("\n--- DataFrame Info ---")
    print(df_pdp_links.info())
    
    # Upsert to database
    try:
        print("\n💾 Upserting data to  table...")
        upsert_df_to_mysql(
            df=df_pdp_links,
            engine=db_engine,
            target_table='product_links',
            key_col='link'
        )
        print("✅ Successfully upserted data to df_product_url table")
        return True
        
    except Exception as e:
        print(f" Failed to upsert data to database: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        print("\n Script completed successfully!")
    else:
        print("\n Script failed!")
        sys.exit(1)

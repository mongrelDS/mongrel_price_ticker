#!/usr/bin/env python3
"""
Nature Santé Product Data Update Scraper

This script scrapes product data from Nature Santé product URLs and updates the database.
It reads product URLs from the df_product_url table and scrapes detailed product information.
"""

import os
import sys
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Add the src directory to the path so we can import our modules
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import database functions and utilities
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from database_config import get_database_engine
from get_domain import get_domain
from function_extract_volume import extract_volume
from price_to_float import price_to_float
from generate_key import generate_key

# Import the price analysis function
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'analytics'))
from df_price_30d import get_price_30d






def scrape_product_data(url, headers):
    """
    Scrapes product data from a single Nature Sante URL using the correct selectors.
    """
    product_data = {'link': url}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Extract each piece of data ---
        title_element = soup.find('h1', class_='product-item-caption-title -product-page')
        product_data['title'] = title_element.get_text(strip=True) if title_element else 'Not Found'

        # --- THIS IS THE FINAL CORRECTED LOGIC FOR THE BRAND ---
        # We find the 'a' tag whose 'href' attribute starts with the vendor path.
        brand_element = soup.select_one('a[href^="/collections/vendors?q="]')
        product_data['brand'] = brand_element.get_text(strip=True) if brand_element else 'Not Found'

        price_element = soup.find('span', class_='money')
        product_data['price'] = price_element['content'] if price_element and price_element.has_attr('content') else 'Not Found'

        availability_element = soup.find('span', id='AddToCartText-product-template')
        product_data['tag'] = availability_element.get_text(strip=True) if availability_element else 'Not Found'

        img_element = soup.find('img', class_='swiper-thumb-item')
        if img_element and img_element.has_attr('src'):
            src = img_element['src']
            product_data['imgurl'] = 'https:' + src if src.startswith('//') else src
        else:
            product_data['imgurl'] = 'Not Found'

        product_data['item_code'] = os.path.basename(url)

    except requests.exceptions.RequestException as e:
        print(f"\nCould not fetch {url}. Reason: {e}")
        product_data['title'] = 'ERROR: Page not found or could not be fetched.'
        for key in ['brand', 'price', 'tag', 'imgurl', 'item_code']:
            product_data.setdefault(key, 'ERROR')

    return product_data


def main():
    """Main function to orchestrate the product data scraping process."""
    print("🚀 Starting Nature Santé Product Data Update Scraper")
    print("=" * 60)
    
    # Record start time for duration calculation
    start_time = time.time()
    
    # Database connection
    try:
        db_engine = get_database_engine()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # SQL to df_link
    try:
        df_link = get_price_30d(domain='naturesante.ca', table_name='df_ticker', verbose=True)
        print(f"📊 Total product URLs in database: {len(df_link)}")
    except Exception as e:
        print(f"❌ Failed to read from database: {e}")
        return False

    # keep only the rows where the URL contains naturesante.ca
    df_link = df_link[df_link['link'].str.contains('naturesante.ca')]
    df_link = df_link[df_link['tag'] != 'Failed']
    df_link = df_link.sort_values(by='date', ascending=False)

    # reset the index
    df_link = df_link.tail(1200)
    
    print(f"📊 Nature Santé product URLs found: {len(df_link)}")
    
    if len(df_link) == 0:
        print("❌ No Nature Santé product URLs found")
        return False

    # --- Main script execution ---
    request_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    all_products_data = []

    print(f"🔍 Found {len(df_link)} links to scrape...")
    total = len(df_link['link'])
    for i, link in enumerate(df_link['link']):
        scraped_data = scrape_product_data(link, request_headers)
        all_products_data.append(scraped_data)
        print(f"\rProgress: {i+1}/{total} ({(i+1)/total*100:.1f}%)", end='', flush=True)
        time.sleep(1) # Polite delay
    print()  # New line at the end

    print("\n✅ Scraping complete!")

    df_pdp_links = pd.DataFrame(all_products_data)

    # Add domain information using get_domain function
    df_pdp_links = get_domain(df_pdp_links, 'link')
    # extract vol from title - use function from src 
    df_pdp_links = extract_volume(df_pdp_links, vol_col="title", result_col="vol")
    # rename item_code to sku
    df_pdp_links = df_pdp_links.rename(columns={'item_code': 'sku'})
    # add date column
    df_pdp_links['date'] = datetime.now().strftime('%Y-%m-%d')
    
    # Validate required columns exist before processing
    required_columns = ['link', 'imgurl', 'title', 'brand', 'sku', 'vol', 'domain', 'price', 'tag']
    missing_columns = [col for col in required_columns if col not in df_pdp_links.columns]
    if missing_columns:
        print(f"❌ Missing required columns: {missing_columns}")
        return False
       
    df_fixed_fields = df_pdp_links[['link', 'imgurl' , 'title' , 'brand','sku', 'vol', 'domain']]

    # price to float
    df_pdp_links = price_to_float(df_pdp_links, price_col="price", currency_marker="$")
    df_ticker = df_pdp_links[['link', 'sku', 'domain', 'price','date','tag']]
    # generate key using link and date
    df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")


    # upsert to mysql
    try:
        upsert_df_to_mysql(
            df=df_fixed_fields,
            engine=db_engine,
            target_table='fixed_fields',
            key_col='link'
        )
        print("✅ Successfully upserted fixed_fields data to database")
    except Exception as e:
        print(f"❌ Failed to upsert fixed_fields data: {e}")
        return False

    try:
        upsert_df_to_mysql(
            df=df_ticker,
            engine=db_engine,
            target_table='df_ticker',
            key_col='key'
        )
        print("✅ Successfully upserted ticker data to database")
    except Exception as e:
        print(f"❌ Failed to upsert ticker data: {e}")
        return False

    print("✅ All data successfully upserted to database")
    
    # Calculate duration and create duration data
    end_time = time.time()
    duration_in_minutes = (end_time - start_time) / 60
    
    df_duration = pd.DataFrame({'duration_min': [duration_in_minutes], 'date': [datetime.now()]})
    df_duration['results'] = len(df_ticker)
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    df_duration['domain'] = 'naturesante.ca'
    df_duration['type'] = 'product_ticker_data'
    
    # Upsert duration data to database
    try:
        upsert_df_to_mysql(
            df=df_duration,
            engine=db_engine,
            target_table='duration',
            key_col='date'
        )
        print("✅ Successfully upserted duration data to database")
    except Exception as e:
        print(f"❌ Failed to upsert duration data: {e}")
        return False
    
    return True





if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Script completed successfully!")
    else:
        print("\n❌ Script failed!")
        sys.exit(1)
#!/usr/bin/env python3
"""
Well.ca Product Details Scraper
Scrapes product details from well.ca product pages using links from brand_link_list table
"""

import json
import time
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
import requests
from bs4 import BeautifulSoup

# Import required functions from src
import sys
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from get_domain import get_domain
from function_extract_volume import extract_volume
from generate_key import generate_key

def get_wellca_links_from_db() -> List[str]:
    """Read brand_link_list from database, filter for /well.ca/ links, and sample them."""
    print("🔍 Reading brand_link_list from database...")
    
    try:
        # Get database engine
        db_engine = get_database_engine()
        
        # Read brand links from database
        df_links = read_mysql_to_df(engine=db_engine, table_name='brand_link_list')
        
        if df_links is None or df_links.empty:
            print("❌ No links found in brand_link_list table")
            return []
        
        print(f"📊 Total links in database: {len(df_links)}")
        
        # Filter for well.ca links
        wellca_links = df_links[df_links['brand_url'].str.contains('/well.ca/', na=False)]
        print(f"🔗 Found {len(wellca_links)} well.ca links")
        
        if len(wellca_links) == 0:
            print("❌ No well.ca links found in database")
            return []
        
        # Calculate sample size: len() // 20
        sample_size = max(1, len(wellca_links) // 20)
        # max(1, len(wellca_links) // 20)
        print(f"📝 Sample size: {sample_size}")
        
        # Sample the links
        sampled_links = wellca_links.sample(n=min(sample_size, len(wellca_links)), random_state=42)
        
        print(f"✅ Selected {len(sampled_links)} links for scraping")
        return sampled_links['brand_url'].tolist()
        
    except Exception as e:
        print(f"❌ Error reading brand links from database: {e}")
        return []

def scrape_product_details(session: requests.Session, product_url: str) -> Optional[Dict[str, Any]]:
    """Scrape product details from a well.ca product page."""
    try:
        response = session.get(product_url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for JSON-LD structured data
        json_scripts = soup.find_all('script', type='application/ld+json')
        product_data = {}
        
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    product_data.update(data)
                    break
            except (json.JSONDecodeError, AttributeError):
                continue
        
        # If no JSON-LD found, try to extract from page content
        if not product_data:
            # Extract basic product information from HTML
            product_data = extract_from_html(soup, product_url)
        
        return product_data
        
    except Exception as e:
        print(f"⚠️ Error scraping {product_url}: {e}")
        return None

def extract_from_html(soup: BeautifulSoup, product_url: str) -> Dict[str, Any]:
    """Extract product information from HTML when JSON-LD is not available."""
    product_data = {}
    
    # Extract product ID from URL
    product_id_match = re.search(r'/products/(\d+)\.html', product_url)
    if product_id_match:
        product_data['sku'] = product_id_match.group(1)
        product_data['product_id'] = product_id_match.group(1)
    
    # Extract title
    title_elem = soup.find('h1', class_='product-title') or soup.find('h1')
    if title_elem:
        product_data['name'] = title_elem.get_text(strip=True)
    
    # Extract price
    price_elem = soup.find('span', class_='price') or soup.find('div', class_='price')
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        if price_match:
            product_data['price'] = float(price_match.group())
    
    # Extract brand
    brand_elem = soup.find('a', class_='brand-link') or soup.find('span', class_='brand')
    if brand_elem:
        product_data['brand_name'] = brand_elem.get_text(strip=True)
    
    # Extract image
    img_elem = soup.find('img', class_='product-image') or soup.find('img', {'data-src': True})
    if img_elem:
        img_src = img_elem.get('data-src') or img_elem.get('src')
        if img_src:
            if img_src.startswith('//'):
                img_src = 'https:' + img_src
            elif img_src.startswith('/'):
                img_src = 'https://well.ca' + img_src
            product_data['image_url'] = img_src
    
    # Extract weight/size information
    weight_elem = soup.find('span', string=re.compile(r'\d+\s*(kg|g|ml|l|oz|lb)', re.I))
    if weight_elem:
        product_data['weight_kg'] = weight_elem.get_text(strip=True)
    
    # Extract UPC/barcode
    upc_elem = soup.find('span', string=re.compile(r'UPC|Barcode', re.I))
    if upc_elem:
        upc_text = upc_elem.find_next_sibling().get_text(strip=True) if upc_elem.find_next_sibling() else ""
        upc_match = re.search(r'\d{12,14}', upc_text)
        if upc_match:
            product_data['upc'] = upc_match.group()
    
    # Extract breadcrumb
    breadcrumb_elem = soup.find('nav', class_='breadcrumb') or soup.find('ol', class_='breadcrumb')
    if breadcrumb_elem:
        breadcrumb_items = breadcrumb_elem.find_all('a')
        breadcrumb_text = ' > '.join([item.get_text(strip=True) for item in breadcrumb_items])
        product_data['breadcrumb'] = breadcrumb_text
    
    # Check stock status
    stock_elem = soup.find('button', class_='add-to-cart') or soup.find('span', class_='stock-status')
    if stock_elem:
        stock_text = stock_elem.get_text(strip=True).lower()
        product_data['can_checkout'] = 'add to cart' in stock_text or 'in stock' in stock_text
    
    return product_data

def process_product_data(product_data: Dict[str, Any], product_url: str) -> Dict[str, Any]:
    """Process and map product data to required fields."""
    if not product_data:
        return {}
    
    # Extract product ID from URL if not in data
    product_id_match = re.search(r'/products/(\d+)\.html', product_url)
    product_id = product_id_match.group(1) if product_id_match else product_data.get('product_id', '')
    
    # Process weight_kg to size with "kg" suffix
    weight_kg = product_data.get('weight_kg', '')
    if weight_kg and str(weight_kg).strip():
        # If weight_kg is a number, add "kg" suffix
        try:
            weight_value = float(weight_kg)
            size = f"{weight_value}kg"
        except (ValueError, TypeError):
            # If it's already a string with units, use as is
            size = str(weight_kg)
    else:
        size = ''
    
    # Map fields according to requirements
    processed_data = {
        'link': product_url,
        'sku': str(product_id),
        'title': product_data.get('name', ''),
        'brand': product_data.get('brand_name', ''),
        'barcode': product_data.get('upc', ''),
        'imgurl': product_data.get('image_url', ''),
        'keywords': product_data.get('breadcrumb', ''),
        'size': size,  # This will be used for volume extraction
        'price': product_data.get('price', 0.0),
        'tag': 'in stock' if product_data.get('can_checkout', False) else 'out of stock',
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    return processed_data

def main():
    """Main function to orchestrate the scraping process."""
    print("🚀 Starting Well.ca Product Details Scraper...")
    
    # Record start time for duration tracking
    start_time = datetime.now()
    
    # Get well.ca links from database
    product_urls = get_wellca_links_from_db()
    
    if not product_urls:
        print("❌ No URLs to process. Exiting.")
        return
    
    # Create session for requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    })
    
    # Lists to store processed data
    all_products = []
    
    print(f"📦 Processing {len(product_urls)} product URLs...")
    
    for i, url in enumerate(product_urls, 1):
        print(f"Processing {i}/{len(product_urls)}: {url}")
        
        # Scrape product details
        product_data = scrape_product_details(session, url)
        
        if product_data:
            # Process the data
            processed_data = process_product_data(product_data, url)
            if processed_data:
                all_products.append(processed_data)
                print(f"✅ Successfully processed: {processed_data.get('title', 'Unknown')}")
            else:
                print(f"⚠️ No data extracted from: {url}")
        else:
            print(f"❌ Failed to scrape: {url}")
        
        # Rate limiting
        time.sleep(1)
    
    print(f"\n📊 Scraping completed! Processed {len(all_products)} products.")
    
    if not all_products:
        print("❌ No products were successfully scraped. Exiting.")
        return
    
    # Create DataFrames
    df_all = pd.DataFrame(all_products)
    
    # Add domain column
    df_all = get_domain(df_all, link_col='link')
    
    # Create df_fixed_fields with exact columns as specified
    df_fixed_fields = df_all[['link', 'sku', 'domain', 'imgurl', 'title', 'brand', 'barcode', 'size', 'keywords']].copy()
    
    # Extract volume using the extract_volume function
    df_fixed_fields = extract_volume(df_fixed_fields, vol_col="size", result_col="vol")
    
    # Remove the temporary 'size' column after volume extraction
    df_fixed_fields = df_fixed_fields.drop(columns=['size'])
    
    # Reorder columns to match exact specification: link, sku, domain, imgurl, title, brand, barcode, vol, keywords
    df_fixed_fields = df_fixed_fields[['link', 'sku', 'domain', 'imgurl', 'title', 'brand', 'barcode', 'vol', 'keywords']]
    
    # Create df_ticker with exact columns as specified: link, sku, domain, price, tag, date
    df_ticker = df_all[['link', 'sku', 'domain', 'price', 'tag', 'date']].copy()
    
    # Generate key for df_ticker
    df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")
    
    # Create df_duration for performance tracking
    end_time = datetime.now()
    duration_in_minutes = (end_time - start_time).total_seconds() / 60
    
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes],
        'date': [datetime.now()],
        'results': [len(df_ticker)],
        'domain': ['well.ca'],
        'type': ['item_update']
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    
    print(f"\n📋 DataFrames created:")
    print(f"  • df_fixed_fields: {len(df_fixed_fields)} records")
    print(f"  • df_ticker: {len(df_ticker)} records")
    print(f"  • df_duration: {len(df_duration)} records")
    
    # Upsert to database
    print(f"\n💾 Upserting to database...")
    try:
        db_engine = get_database_engine()
        
        # Upsert df_ticker
        print("📤 Upserting df_ticker...")
        upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
        print(f"✅ df_ticker upserted successfully ({len(df_ticker)} records)")
        
        # Upsert df_fixed_fields
        print("📤 Upserting df_fixed_fields...")
        upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
        print(f"✅ df_fixed_fields upserted successfully ({len(df_fixed_fields)} records)")
        
        # Upsert df_duration
        print("📤 Upserting df_duration...")
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        print(f"✅ df_duration upserted successfully ({len(df_duration)} records)")
        print(f"📊 Duration: {duration_in_minutes:.2f} minutes, {len(df_ticker)} results")
        print(f"📊 Results per minute: {df_duration['result_per_minute'].iloc[0]:.2f}")
        
    except Exception as e:
        print(f"❌ Error upserting to database: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n🎉 Well.ca Product Details Scraper completed successfully!")

if __name__ == "__main__":
    main()

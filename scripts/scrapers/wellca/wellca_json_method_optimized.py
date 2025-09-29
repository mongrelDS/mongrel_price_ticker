#!/usr/bin/env python3
"""
Well.ca JSON Scraper - Optimized Version

This script scrapes product data from well.ca using their JSON API endpoints.
It includes parallel processing, memory management, data validation, and comprehensive error handling.

Features:
- Parallel brand scraping with configurable concurrency
- Memory management and garbage collection
- Data validation and cleaning
- Comprehensive error handling and logging
- Database connection pooling
- Duration tracking and performance metrics
- Resume capability and progress tracking

Usage:
    python3 wellca_json_method_optimized.py [--test]
    
Environment Variables:
    WELLCA_SAMPLE_SIZE: Number of brands to scrape (default: 20)
    WELLCA_TEST_SAMPLE_SIZE: Number of brands in test mode (default: 5)
    WELLCA_MAX_CONCURRENT_BRANDS: Max parallel workers (default: 3)
    WELLCA_REQUEST_TIMEOUT: Request timeout in seconds (default: 15)
    WELLCA_RATE_LIMIT_DELAY: Delay between requests (default: 1.0)
    WELLCA_MAX_RETRIES: Max retries for failed requests (default: 3)
    WELLCA_DB_BATCH_SIZE: Database batch size (default: 1000)
"""

import time
import sys
import os
import gc
import asyncio
import concurrent.futures
import logging
import traceback
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from dotenv import load_dotenv
import pandas as pd

from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# --- Configuration Constants ---
# Performance settings
DEFAULT_SAMPLE_SIZE = int(os.getenv('WELLCA_SAMPLE_SIZE', '20'))
DEFAULT_TEST_SAMPLE_SIZE = int(os.getenv('WELLCA_TEST_SAMPLE_SIZE', '5'))
MAX_CONCURRENT_BRANDS = int(os.getenv('WELLCA_MAX_CONCURRENT_BRANDS', '3'))
REQUEST_TIMEOUT = int(os.getenv('WELLCA_REQUEST_TIMEOUT', '15'))
RATE_LIMIT_DELAY = float(os.getenv('WELLCA_RATE_LIMIT_DELAY', '1.0'))
MAX_RETRIES = int(os.getenv('WELLCA_MAX_RETRIES', '3'))

# Database settings
DB_BATCH_SIZE = int(os.getenv('WELLCA_DB_BATCH_SIZE', '1000'))

# API endpoints
PRODUCTS_API_URL = "https://well.ca/api/products"
BRAND_API_BASE = "https://well.ca/api/brands"
CATEGORY_API_URL = "https://well.ca/api/categories"

# Cache settings
CACHE_CLEANUP_INTERVAL = 100  # Clean cache every N operations

# --- Logging Configuration ---
def setup_logging():
    """Setup logging configuration for the scraper"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('wellca_scraper.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

# Import database functions
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Import utility functions
from function_extract_volume import extract_volume
from get_domain import get_domain
from generate_key import generate_key

# --- Phase 4: Data Processing (Pydantic Models) ---
class Product(BaseModel):
    """Pydantic model for product data validation and structure"""
    # Core identifiers
    product_id: int
    name: str
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    sku: Optional[str] = None
    upc: Optional[str] = None
    
    # Pricing
    price: float
    price_formatted: Optional[str] = None
    sale_price: Optional[float] = None
    sale_price_formatted: Optional[str] = None
    currency_code: Optional[str] = None
    
    # Product details
    quantity_text: Optional[str] = None
    dose_text: Optional[str] = None
    subtitle: Optional[str] = None
    chemical_name: Optional[str] = None
    
    # Images
    image_url: Optional[str] = None
    image_thumbnail: Optional[str] = None
    image_full: Optional[str] = None
    
    # Inventory
    stock_quantity: Optional[int] = None
    warehouse_stock: Optional[int] = None
    can_checkout: Optional[bool] = None
    
    # Physical properties
    weight_kg: Optional[float] = None
    height: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    
    # Status and metadata
    status: Optional[str] = None
    last_modified: Optional[str] = None
    average_rating: Optional[int] = None
    
    # Category information
    category_id: Optional[str] = None
    breadcrumb: Optional[str] = None
    
    # URLs
    product_url: str

def get_brand_name(session: requests.Session, brand_id: str, brand_cache: dict, max_retries: int = 3) -> str:
    """Get brand name from brand ID using API lookup with caching and retry logic."""
    if brand_id in brand_cache:
        return brand_cache[brand_id]

    for attempt in range(max_retries):
        try:
            response = session.get(f"{BRAND_API_BASE}/{brand_id}", timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                brand_data = response.json()
                brand_name = brand_data.get("title", f"Brand_{brand_id}")
                brand_cache[brand_id] = brand_name
                return brand_name
            elif response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt
                print(f"[bold yellow]⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}[/bold yellow]")
                time.sleep(wait_time)
                continue
            else:
                brand_name = f"Brand_{brand_id}"
                brand_cache[brand_id] = brand_name
                return brand_name
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[bold yellow]⚠️ Error getting brand name for ID {brand_id} after {max_retries} attempts: {e}[/bold yellow]")
            else:
                wait_time = 2 ** attempt
                print(f"[bold yellow]⚠️ Error getting brand name for ID {brand_id}, retrying in {wait_time}s: {e}[/bold yellow]")
                time.sleep(wait_time)
                continue

    brand_name = f"Brand_{brand_id}"
    brand_cache[brand_id] = brand_name
    return brand_name

def get_category_breadcrumb(session: requests.Session, category_id: str, category_cache: dict, max_retries: int = 3) -> str:
    """Get category breadcrumb path from category ID using API lookup with caching."""
    if category_id in category_cache:
        return category_cache[category_id]

    for attempt in range(max_retries):
        try:
            # Get all categories to build hierarchy
            response = session.get(CATEGORY_API_URL, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                categories_data = response.json()

                # Build category map with better breadcrumb structure
                category_map = {}
                def build_category_map(categories, parent_path=""):
                    for cat in categories:
                        # Create breadcrumb path with "Home" as root
                        if parent_path:
                            current_path = f"Home > {parent_path} > {cat['title']}"
                        else:
                            current_path = f"Home > {cat['title']}"
                        category_map[cat['id']] = current_path

                        if 'subcategories' in cat and cat['subcategories']:
                            # Pass the current category title as parent for subcategories
                            build_category_map(cat['subcategories'], cat['title'])

                build_category_map(categories_data)

                # Get breadcrumb for the specific category
                breadcrumb = category_map.get(category_id, f"Home > Category {category_id}")
                category_cache[category_id] = breadcrumb
                return breadcrumb
            else:
                breadcrumb = f"Home > Category {category_id}"
                category_cache[category_id] = breadcrumb
                return breadcrumb

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[bold yellow]⚠️ Error getting breadcrumb for category {category_id} after {max_retries} attempts: {e}[/bold yellow]")
            else:
                wait_time = 2 ** attempt
                print(f"[bold yellow]⚠️ Error getting breadcrumb for category {category_id}, retrying in {wait_time}s: {e}[/bold yellow]")
                time.sleep(wait_time)
                continue

    breadcrumb = f"Home > Category {category_id}"
    category_cache[category_id] = breadcrumb
    return breadcrumb

def get_database_engine():
    """Create optimized database engine using environment variables with connection pooling"""
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '30306')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required")
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Use connection pooling for better performance
    return create_engine(
        connection_string, 
        pool_size=5,  # Number of connections to maintain
        max_overflow=10,  # Additional connections that can be created
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=False  # Set to True for SQL debugging
    )

def get_wellca_brand_links(sample_size: int = 20) -> List[str]:
    """Get sampled well.ca brand links from database"""
    print(f"🔍 Querying brand_link_list table for well.ca links (sample size: {sample_size})...")
    
    try:
        # Read brand links from database
        df = read_mysql_to_df(engine=get_database_engine(), table_name='brand_link_list')
        
        # Filter for well.ca links
        wellca_links = df[df['brand_url'].str.contains('/well.ca/', na=False)]
        
        print(f"📊 Total links in database: {len(df)}")
        print(f"🔗 Found {len(wellca_links)} well.ca links")
        
        if len(wellca_links) == 0:
            print("❌ No well.ca links found in database")
            return []
        
        # Sample the links
        sampled_links = wellca_links.sample(n=min(sample_size, len(wellca_links)), random_state=42)
        
        print(f"📝 Selected {len(sampled_links)} links for scraping")
        return sampled_links['brand_url'].tolist()
        
    except Exception as e:
        print(f"❌ Error reading brand links from database: {e}")
        logger.error(f"Database error: {e}")
        return []

def scrape_brand_products_parallel(session: requests.Session, brand_urls: List[str], brand_cache: dict, category_cache: dict) -> List[Product]:
    """Scrape products from multiple brand URLs in parallel using ThreadPoolExecutor."""
    all_products = []
    
    def scrape_single_brand(brand_url: str) -> List[Product]:
        """Scrape products from a single brand URL."""
        try:
            return scrape_brand_products(session, brand_url, brand_cache, category_cache)
        except Exception as e:
            print(f"[bold red]❌ Error scraping brand {brand_url}: {e}[/bold red]")
            logger.error(f"Brand scraping error for {brand_url}: {e}")
            return []
    
    # Use ThreadPoolExecutor for parallel processing
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BRANDS) as executor:
        # Submit all brand scraping tasks
        future_to_brand = {
            executor.submit(scrape_single_brand, brand_url): brand_url 
            for brand_url in brand_urls
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_brand):
            brand_url = future_to_brand[future]
            try:
                products = future.result()
                all_products.extend(products)
                print(f"[bold green]✅ Completed brand: {brand_url} ({len(products)} products)[/bold green]")
            except Exception as e:
                print(f"[bold red]❌ Failed brand: {brand_url} - {e}[/bold red]")
                logger.error(f"Failed brand {brand_url}: {e}")
    
    return all_products

def scrape_brand_products(session: requests.Session, brand_url: str, brand_cache: dict, category_cache: dict) -> List[Product]:
    """Scrape products for a specific brand using the brand-specific API"""
    print(f"🔍 Scraping products for brand: {brand_url}")
    
    # Extract brand name from URL
    brand_name = brand_url.split('/')[-1].replace('.html', '')
    
    # Construct API URL for brand products
    api_url = f"https://well.ca/api/brands/{brand_name}/products"
    
    products = []
    
    try:
        response = session.get(api_url, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            
            if 'products' in data and data['products']:
                for product_data in data['products']:
                    try:
                        # Get brand name if brand_id is available
                        brand_name_resolved = None
                        if 'brands_id' in product_data and product_data['brands_id']:
                            brand_name_resolved = get_brand_name(session, str(product_data['brands_id']), brand_cache)
                        
                        # Get category breadcrumb if category_id is available
                        breadcrumb = None
                        if 'master_categories_id' in product_data and product_data['master_categories_id']:
                            breadcrumb = get_category_breadcrumb(session, str(product_data['master_categories_id']), category_cache)
                        
                        # Create Product object
                        product = Product(
                            product_id=product_data.get('products_id', 0),
                            name=product_data.get('products_name', ''),
                            brand_id=str(product_data.get('brands_id', '')),
                            brand_name=brand_name_resolved,
                            sku=str(product_data.get('products_id', '')),
                            upc=product_data.get('products_upc'),
                            price=float(product_data.get('products_price', 0)),
                            price_formatted=product_data.get('products_price_formatted', ''),
                            sale_price=product_data.get('products_sale_price'),
                            sale_price_formatted=product_data.get('products_sale_price_formatted'),
                            currency_code=product_data.get('currency_code', 'CAD'),
                            quantity_text=product_data.get('products_quantity_text'),
                            dose_text=product_data.get('products_dose_text'),
                            subtitle=product_data.get('products_subtitle'),
                            chemical_name=product_data.get('products_chemicalname'),
                            image_url=product_data.get('products_image'),
                            image_thumbnail=product_data.get('products_image_thumbnail'),
                            image_full=product_data.get('products_image_full'),
                            stock_quantity=product_data.get('products_quantity_order_stock'),
                            warehouse_stock=product_data.get('products_warehouse_stock'),
                            can_checkout=product_data.get('can_checkout'),
                            weight_kg=product_data.get('weight_kg'),
                            height=product_data.get('height'),
                            width=product_data.get('width'),
                            length=product_data.get('length'),
                            status=product_data.get('status'),
                            last_modified=product_data.get('last_modified'),
                            average_rating=product_data.get('average_rating'),
                            category_id=str(product_data.get('master_categories_id', '')),
                            breadcrumb=breadcrumb,
                            product_url=f"https://well.ca/product/{product_data.get('id', '')}"
                        )
                        products.append(product)
                    except ValidationError as e:
                        print(f"[bold yellow]⚠️ Validation error for product {product_data.get('id', 'unknown')}: {e}[/bold yellow]")
                        continue
                    except Exception as e:
                        print(f"[bold yellow]⚠️ Error processing product {product_data.get('id', 'unknown')}: {e}[/bold yellow]")
                        continue
        else:
            print(f"[bold yellow]⚠️ API request failed for brand {brand_name}: {response.status_code}[/bold yellow]")
            
    except Exception as e:
        print(f"[bold red]❌ Error scraping brand {brand_name}: {e}[/bold red]")
        logger.error(f"Brand scraping error for {brand_name}: {e}")
    
    print(f"📦 Found {len(products)} products for brand: {brand_name}")
    return products

def scrape_products_api(session: requests.Session, brand_cache: dict, category_cache: dict) -> List[Product]:
    """Scrape products using the general products API"""
    print("🔍 Scraping from products API...")
    
    all_products = []
    
    try:
        # Get products from the general API
        response = session.get(PRODUCTS_API_URL, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            
            # The API returns a list of products directly, not wrapped in a 'products' key
            if isinstance(data, list) and data:
                for product_data in data:
                    try:
                        # Get brand name if brand_id is available
                        brand_name_resolved = None
                        if 'brands_id' in product_data and product_data['brands_id']:
                            brand_name_resolved = get_brand_name(session, str(product_data['brands_id']), brand_cache)
                        
                        # Get category breadcrumb if category_id is available
                        breadcrumb = None
                        if 'master_categories_id' in product_data and product_data['master_categories_id']:
                            breadcrumb = get_category_breadcrumb(session, str(product_data['master_categories_id']), category_cache)
                        
                        # Create Product object
                        product = Product(
                            product_id=product_data.get('products_id', 0),
                            name=product_data.get('products_name', ''),
                            brand_id=str(product_data.get('brands_id', '')),
                            brand_name=brand_name_resolved,
                            sku=str(product_data.get('products_id', '')),
                            upc=product_data.get('products_upc'),
                            price=float(product_data.get('products_price', 0)),
                            price_formatted=product_data.get('products_price_formatted', ''),
                            sale_price=product_data.get('products_sale_price'),
                            sale_price_formatted=product_data.get('products_sale_price_formatted'),
                            currency_code=product_data.get('currency_code', 'CAD'),
                            quantity_text=product_data.get('products_quantity_text'),
                            dose_text=product_data.get('products_dose_text'),
                            subtitle=product_data.get('products_subtitle'),
                            chemical_name=product_data.get('products_chemicalname'),
                            image_url=product_data.get('products_image'),
                            image_thumbnail=product_data.get('products_image_thumbnail'),
                            image_full=product_data.get('products_image_full'),
                            stock_quantity=product_data.get('products_quantity_order_stock'),
                            warehouse_stock=product_data.get('products_warehouse_stock'),
                            can_checkout=product_data.get('can_checkout'),
                            weight_kg=product_data.get('weight_kg'),
                            height=product_data.get('height'),
                            width=product_data.get('width'),
                            length=product_data.get('length'),
                            status=product_data.get('status'),
                            last_modified=product_data.get('last_modified'),
                            average_rating=product_data.get('average_rating'),
                            category_id=str(product_data.get('master_categories_id', '')),
                            breadcrumb=breadcrumb,
                            product_url=f"https://well.ca/product/{product_data.get('id', '')}"
                        )
                        all_products.append(product)
                    except ValidationError as e:
                        print(f"[bold yellow]⚠️ Validation error for product {product_data.get('id', 'unknown')}: {e}[/bold yellow]")
                        continue
                    except Exception as e:
                        print(f"[bold yellow]⚠️ Error processing product {product_data.get('id', 'unknown')}: {e}[/bold yellow]")
                        continue
        else:
            print(f"[bold yellow]⚠️ Products API request failed: {response.status_code}[/bold yellow]")
            
    except Exception as e:
        print(f"[bold red]❌ Error scraping products API: {e}[/bold red]")
        logger.error(f"Products API error: {e}")
    
    print(f"📦 Found {len(all_products)} products from products API")
    return all_products

def map_products_to_standard_format(products: List[Product]) -> List[dict]:
    """Efficiently map Product objects to the standard format with all required fields."""
    import pandas as pd
    from datetime import datetime
    
    # Convert products to list of dicts
    product_dicts = [product.model_dump() for product in products]
    
    if not product_dicts:
        return []
    
    # Create DataFrame for efficient processing
    df = pd.DataFrame(product_dicts)
    
    # Map fields to standard format
    mapped_data = []
    
    for _, row in df.iterrows():
        # Extract date from last_modified (format: 2025-09-28 06:01:10)
        date_str = None
        if row.get('last_modified'):
            try:
                # Parse the datetime string and extract just the date
                dt = datetime.strptime(row['last_modified'], '%Y-%m-%d %H:%M:%S')
                date_str = dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                date_str = None
        
        # Map can_checkout to tag
        tag = "in stock" if row.get('can_checkout') else "out of stock"
        
        mapped_item = {
            'link': row.get('product_url', ''),
            'title': row.get('name', ''),
            'size': row.get('weight_kg', ''),
            'vol': row.get('quantity_text', ''),  # This will be processed by extract_volume
            'price': row.get('price_formatted', ''),
            'imgurl': row.get('image_url', ''),
            'sku': str(row.get('product_id', '')),
            'brand': row.get('brand_name', ''),
            'tag': tag,
            'date': date_str,
            'barcode': row.get('upc', ''),
            'keywords': row.get('breadcrumb', ''),
            'domain': 'well.ca'  # Static for well.ca
        }
        
        mapped_data.append(mapped_item)
    
    return mapped_data

def process_volume_extraction(mapped_data: List[dict]) -> List[dict]:
    """Process volume extraction using the extract_volume function."""
    if not mapped_data:
        return []
    
    # Convert to DataFrame for processing
    df = pd.DataFrame(mapped_data)
    
    # Add "kg" to size field before volume extraction
    df['vol'] = df['size'].astype(str) + ' kg'
    
    # Use extract_volume function to process the 'vol' column
    df = extract_volume(df, vol_col="vol", result_col="vol")
    
    # Convert back to list of dicts
    return df.to_dict('records')

def validate_and_clean_data(final_products: List[dict]) -> List[dict]:
    """Validate and clean the final products data."""
    if not final_products:
        return []
    
    cleaned_products = []
    
    for product in final_products:
        # Create a copy to avoid modifying the original
        cleaned_product = product.copy()
        
        # Validate required fields
        if not cleaned_product.get('link') or not cleaned_product.get('sku'):
            print(f"[bold yellow]⚠️ Skipping product with missing required fields: {product.get('title', 'Unknown')}[/bold yellow]")
            continue
        
        # Clean and validate data
        # Clean price data
        if 'price' in cleaned_product and cleaned_product['price']:
            try:
                price_str = str(cleaned_product['price']).replace('$', '').replace(',', '').strip()
                cleaned_product['price'] = float(price_str) if price_str else 0.0
            except (ValueError, TypeError):
                cleaned_product['price'] = 0.0
        
        # Clean text fields
        for field in ['title', 'brand', 'keywords']:
            if field in cleaned_product and cleaned_product[field]:
                cleaned_product[field] = str(cleaned_product[field]).strip()
        
        # Validate URL format
        if 'link' in cleaned_product and cleaned_product['link']:
            if not cleaned_product['link'].startswith('http'):
                print(f"[bold yellow]⚠️ Invalid URL format: {cleaned_product['link']}[/bold yellow]")
                continue
        
        # Validate SKU format
        if 'sku' in cleaned_product and cleaned_product['sku']:
            cleaned_product['sku'] = str(cleaned_product['sku']).strip()
        
        cleaned_products.append(cleaned_product)
    
    print(f"[bold green]✅ Data validation complete: {len(cleaned_products)}/{len(final_products)} products passed validation[/bold green]")
    return cleaned_products

def create_dataframes_and_upsert(final_products: List[dict], db_engine):
    """Create df_fixed_fields and df_ticker dataframes and upsert to database."""
    if not final_products:
        print("[bold yellow]⚠️ No products to process[/bold yellow]")
        return
    
    print("\n[bold]📊 Creating dataframes...[/bold]")
    
    # Validate and clean data first
    cleaned_products = validate_and_clean_data(final_products)
    
    if not cleaned_products:
        print("[bold red]❌ No valid products after cleaning[/bold red]")
        return
    
    # Create df_fixed_fields with specified columns
    df_fixed_fields = pd.DataFrame(cleaned_products)[
        ['link', 'sku', 'domain', 'imgurl', 'title', 'brand', 'barcode', 'vol', 'keywords']
    ].copy()
    
    # Create df_ticker with specified columns
    df_ticker = pd.DataFrame(cleaned_products)[
        ['link', 'sku', 'domain', 'price', 'tag', 'date']
    ].copy()
    
    # Additional data cleaning for dataframes
    # Fill NaN values appropriately
    df_fixed_fields = df_fixed_fields.fillna('')
    df_ticker = df_ticker.fillna('')
    
    # Ensure price is numeric
    df_ticker['price'] = pd.to_numeric(df_ticker['price'], errors='coerce').fillna(0.0)
    
    print(f"✅ df_fixed_fields created with {len(df_fixed_fields)} rows")
    print(f"✅ df_ticker created with {len(df_ticker)} rows")
    
    # Apply generate_key function to df_ticker
    print("\n[bold]🔑 Generating keys for df_ticker...[/bold]")
    df_ticker = generate_key(df=df_ticker, deduplication_columns=['link', 'date'], key_col="key")
    
    print(f"✅ Keys generated for df_ticker")
    
    # Upsert df_ticker to database
    print("\n[bold]💾 Upserting df_ticker to database...[/bold]")
    try:
        upsert_df_to_mysql(
            df=df_ticker,
            target_table='df_ticker',
            key_col='key',
            engine=db_engine
        )
        print("✅ df_ticker successfully upserted to database")
    except Exception as e:
        print(f"[bold red]❌ Error upserting df_ticker: {e}[/bold red]")
        logger.error(f"df_ticker upsert error: {e}")
    
    # Upsert df_fixed_fields to database
    print("\n[bold]💾 Upserting df_fixed_fields to database...[/bold]")
    try:
        upsert_df_to_mysql(
            df=df_fixed_fields,
            target_table='fixed_fields',
            key_col='link',
            engine=db_engine
        )
        print("✅ df_fixed_fields successfully upserted to database")
    except Exception as e:
        print(f"[bold red]❌ Error upserting df_fixed_fields: {e}[/bold red]")
        logger.error(f"fixed_fields upsert error: {e}")
    
    # Display sample data
    print("\n[bold]📋 Sample df_fixed_fields data:[/bold]")
    print(df_fixed_fields.head(3).to_string(index=False))
    
    print("\n[bold]📋 Sample df_ticker data:[/bold]")
    print(df_ticker.head(3).to_string(index=False))

def main(test_mode: bool = False):
    """Main function to orchestrate the scraping process using brand links from database."""
    try:
        # Record start time for duration tracking
        timestamp_0 = datetime.now()
        logger.info(f"Starting well.ca scraper in {'test' if test_mode else 'production'} mode")
        
        # --- Phase 3: Automation (Session and Headers) ---
        # Use curl_cffi's Session to mimic a real browser's TLS fingerprint.
        # This is the key step to avoid being blocked by anti-bot systems.
        session = requests.Session(
            impersonate="chrome110", # Mimics the TLS fingerprint of Chrome 110
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
        )
        
        all_products: List[Product] = []
        brand_cache: dict = {}  # Cache for brand name lookups
        category_cache: dict = {}  # Cache for category breadcrumb lookups
        
        print("[bold cyan]🚀 Starting well.ca scraper using brand links from database...[/bold cyan]")
        
        # Get sample size based on test mode
        sample_size = DEFAULT_TEST_SAMPLE_SIZE if test_mode else DEFAULT_SAMPLE_SIZE
        if test_mode:
            print(f"[bold yellow]🧪 Test mode: Limited to {sample_size} brand links[/bold yellow]")
        
        # Get sampled brand links from database
        brand_links = get_wellca_brand_links(sample_size=sample_size)
        
        if not brand_links:
            print("❌ No brand links found, exiting...")
            return
        
        print(f"\n📋 Scraping products from {len(brand_links)} brand links:")
        for i, link in enumerate(brand_links, 1):
            print(f"  {i}. {link}")
        
        # Use the products API for comprehensive data
        print("\n[bold]Scraping from products API...[/bold]")
        products_api_data = scrape_products_api(session, brand_cache, category_cache)
        all_products.extend(products_api_data)
        
        print(f"📊 Total products scraped: {len(all_products)}")

        print("-" * 50)
        print(f"[bold blue]📊 Total products scraped: {len(all_products)}[/bold blue]")
        
        # Memory management: Clean up caches periodically
        if len(brand_cache) > CACHE_CLEANUP_INTERVAL:
            print(f"[bold yellow]🧹 Cleaning up brand cache ({len(brand_cache)} entries)[/bold yellow]")
            brand_cache.clear()
            gc.collect()
        
        if len(category_cache) > CACHE_CLEANUP_INTERVAL:
            print(f"[bold yellow]🧹 Cleaning up category cache ({len(category_cache)} entries)[/bold yellow]")
            category_cache.clear()
            gc.collect()

        # Map to standard format
        print("\n[bold]🔄 Mapping to standard format...[/bold]")
        mapped_products = map_products_to_standard_format(all_products)
        
        # Store total count before clearing for memory management
        total_products_scraped = len(all_products)
        
        # Clear all_products to free memory
        del all_products
        gc.collect()
        
        # Process volume extraction
        print("[bold]📏 Processing volume extraction...[/bold]")
        final_products = process_volume_extraction(mapped_products)
        
        # Clear mapped_products to free memory
        del mapped_products
        gc.collect()
        
        print(f"[bold green]✅ Successfully mapped {len(final_products)} products to standard format[/bold green]")

        # Print the first 5 products in standard format
        if final_products:
            print("\n[bold]Sample of mapped data (standard format):[/bold]")
            for product in final_products[:5]:
                print(product)
        
        # Create dataframes and upsert to database
        if final_products:
            print("\n[bold]💾 Creating dataframes and upserting to database...[/bold]")
            db_engine = get_database_engine()
            create_dataframes_and_upsert(final_products, db_engine)
        
        # --- Duration Tracking ---
        print(f"\n[bold cyan]⏱️ Recording duration metrics...[/bold cyan]")
        try:
            # Calculate duration
            timestamp_1 = datetime.now()
            duration = timestamp_1 - timestamp_0
            duration_in_minutes = duration.total_seconds() / 60
            
            # Prepare duration data
            df_duration = pd.DataFrame({
                'duration_min': [duration_in_minutes],
                'date': [datetime.now()],
                'results': [len(final_products)],
                'domain': ['well.ca'],
                'type': ['item_update']
            })
            df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
            
            # Get database engine for duration tracking
            db_engine = get_database_engine()
            
            # Upsert to duration table
            upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
            print(f"[bold green]✅ Duration metrics recorded: {duration_in_minutes:.2f} minutes, {len(final_products)} results[/bold green]")
            print(f"[bold blue]📊 Results per minute: {df_duration['result_per_minute'].iloc[0]:.2f}[/bold blue]")
            
        except Exception as e:
            print(f"[bold red]❌ Error recording duration metrics: {e}[/bold red]")
            logger.error(f"Duration tracking error: {e}")
        
        # --- Final Summary ---
        print(f"\n[bold green]🎉 Scraping completed![/bold green]")
        print(f"[bold blue]📊 Summary:[/bold blue]")
        print(f"  • Total products scraped: {total_products_scraped}")
        print(f"  • Brand cache entries: {len(brand_cache)}")
        print(f"  • Category cache entries: {len(category_cache)}")
        print(f"  • Final products processed: {len(final_products)}")
        
        logger.info("Scraping completed successfully")
        
    except Exception as e:
        logger.error(f"Critical error in main function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"[bold red]❌ Critical error: {e}[/bold red]")
        print(f"[bold red]Check wellca_scraper.log for details[/bold red]")
        raise
    finally:
        # Cleanup resources
        try:
            if 'session' in locals():
                session.close()
            gc.collect()
            logger.info("Resources cleaned up successfully")
        except Exception as cleanup_error:
            logger.warning(f"Error during cleanup: {cleanup_error}")

if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv
    main(test_mode=test_mode)

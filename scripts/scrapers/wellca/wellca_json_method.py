import time
import sys
import os
from typing import List, Optional
from dotenv import load_dotenv

from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Import database functions
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# --- Phase 4: Data Processing (Pydantic Models) ---
# Define a Pydantic model to structure and validate the product data we want.
# This ensures that if the API changes or a product has missing data, our script won't crash.
class Product(BaseModel):
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
    
    # URLs
    product_url: str

def get_brand_name(session: requests.Session, brand_id: str, brand_cache: dict, max_retries: int = 3) -> str:
    """Get brand name from brand ID using API lookup with caching and retry logic."""
    if brand_id in brand_cache:
        return brand_cache[brand_id]

    for attempt in range(max_retries):
        try:
            response = session.get(f"https://well.ca/api/brands/{brand_id}", timeout=10)
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

def get_database_engine():
    """Create database engine using environment variables"""
    db_host = os.getenv('DB_HOST', '127.0.0.1')
    db_port = os.getenv('DB_PORT', '30306')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required")
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    return create_engine(connection_string, poolclass=NullPool)

def get_wellca_brand_links(sample_size: int = 20) -> List[str]:
    """Get sampled well.ca brand links from database"""
    print(f"🔍 Querying brand_link_list table for well.ca links (sample size: {sample_size})...")
    
    db_engine = get_database_engine()
    df_links = read_mysql_to_df(engine=db_engine, table_name='brand_link_list')
    
    if df_links is None or df_links.empty:
        print("❌ No links found in brand_link_list table")
        return []
    
    print(f"📊 Total links in database: {len(df_links)}")
    
    # Filter for well.ca links
    wellca_links = df_links[df_links['brand_url'].astype(str).str.contains('/well.ca/', case=False, na=False)]
    print(f"🔗 Found {len(wellca_links)} well.ca links")
    
    if wellca_links.empty:
        print("❌ No well.ca links found")
        return []
    
    # Sample the links
    sample_size = min(sample_size, len(wellca_links))
    sampled_links = wellca_links.sample(n=sample_size, random_state=42)
    
    print(f"📝 Selected {len(sampled_links)} links for scraping")
    return sampled_links['brand_url'].tolist()

def scrape_brand_products(session: requests.Session, brand_url: str, brand_cache: dict) -> List[Product]:
    """Scrape products for a specific brand using the brand-specific API"""
    print(f"🔍 Scraping products for brand: {brand_url}")
    
    # Extract brand name from URL
    brand_name = brand_url.split('/')[-1].replace('.html', '')
    
    # Try brand-specific API endpoint
    api_url = f"https://well.ca/api/products?brand={brand_name}"
    all_products: List[Product] = []
    
    try:
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        print(f"📦 Found {len(data)} products for brand: {brand_name}")
        
        for item in data:
            try:
                # Get brand name from brand ID
                brand_id = str(item.get("brands_id", "")) if item.get("brands_id") else None
                resolved_brand_name = get_brand_name(session, brand_id, brand_cache) if brand_id else None
                
                product_data = {
                    # Core identifiers
                    "product_id": int(item.get("products_id", 0)),
                    "name": item.get("products_name", ""),
                    "brand_id": brand_id,
                    "brand_name": resolved_brand_name,
                    "sku": str(item.get("products_code", "")) if item.get("products_code") else None,
                    "upc": str(item.get("products_upc", "")) if item.get("products_upc") else None,
                    
                    # Pricing
                    "price": float(item.get("products_price", 0)),
                    "price_formatted": item.get("products_price_formatted"),
                    "sale_price": float(item.get("products_sale_price", 0)) if item.get("products_sale_price") else None,
                    "sale_price_formatted": item.get("products_sale_price_formatted"),
                    "currency_code": item.get("currency_code"),
                    
                    # Product details
                    "quantity_text": item.get("products_quantity_text"),
                    "dose_text": item.get("products_dose_text"),
                    "subtitle": item.get("products_subtitle"),
                    "chemical_name": item.get("products_chemicalname"),
                    
                    # Images
                    "image_url": item.get("products_image"),
                    "image_thumbnail": item.get("products_image_thumbnail"),
                    "image_full": item.get("products_image_full"),
                    
                    # Inventory
                    "stock_quantity": item.get("products_quantity_order_stock"),
                    "warehouse_stock": item.get("products_warehouse_stock"),
                    "can_checkout": item.get("can_checkout"),
                    
                    # Physical properties
                    "weight_kg": float(item.get("products_weight_kg", 0)) if item.get("products_weight_kg") else None,
                    "height": float(item.get("products_height", 0)) if item.get("products_height") else None,
                    "width": float(item.get("products_width", 0)) if item.get("products_width") else None,
                    "length": float(item.get("products_length", 0)) if item.get("products_length") else None,
                    
                    # Status and metadata
                    "status": item.get("products_status"),
                    "last_modified": item.get("products_last_modified"),
                    "average_rating": item.get("products_average_rating"),
                    
                    # URLs
                    "product_url": f"https://well.ca/product/{item.get('products_id', '')}" if item.get("products_id") else ""
                }
                
                product = Product(**product_data)
                all_products.append(product)
            except (ValidationError, ValueError, TypeError) as e:
                print(f"[bold yellow]⚠️ Skipping product due to error:[/bold yellow] {e}")
                continue
                
    except Exception as e:
        print(f"[bold red]❌ Error scraping brand {brand_name}: {e}[/bold red]")
    
    return all_products

def scrape_products_api(session: requests.Session, brand_cache: dict) -> List[Product]:
    """Scrape products using the main products API endpoint"""
    print("🔍 Scraping from products API...")
    
    api_url = "https://well.ca/api/products"
    all_products: List[Product] = []
    
    try:
        response = session.get(api_url)
        response.raise_for_status()
        
        data = response.json()
        print(f"📦 Found {len(data)} products from products API")
        
        for item in data:
            try:
                # Get brand name from brand ID
                brand_id = str(item.get("brands_id", "")) if item.get("brands_id") else None
                resolved_brand_name = get_brand_name(session, brand_id, brand_cache) if brand_id else None
                
                product_data = {
                    # Core identifiers
                    "product_id": int(item.get("products_id", 0)),
                    "name": item.get("products_name", ""),
                    "brand_id": brand_id,
                    "brand_name": resolved_brand_name,
                    "sku": str(item.get("products_code", "")) if item.get("products_code") else None,
                    "upc": str(item.get("products_upc", "")) if item.get("products_upc") else None,
                    
                    # Pricing
                    "price": float(item.get("products_price", 0)),
                    "price_formatted": item.get("products_price_formatted"),
                    "sale_price": float(item.get("products_sale_price", 0)) if item.get("products_sale_price") else None,
                    "sale_price_formatted": item.get("products_sale_price_formatted"),
                    "currency_code": item.get("currency_code"),
                    
                    # Product details
                    "quantity_text": item.get("products_quantity_text"),
                    "dose_text": item.get("products_dose_text"),
                    "subtitle": item.get("products_subtitle"),
                    "chemical_name": item.get("products_chemicalname"),
                    
                    # Images
                    "image_url": item.get("products_image"),
                    "image_thumbnail": item.get("products_image_thumbnail"),
                    "image_full": item.get("products_image_full"),
                    
                    # Inventory
                    "stock_quantity": item.get("products_quantity_order_stock"),
                    "warehouse_stock": item.get("products_warehouse_stock"),
                    "can_checkout": item.get("can_checkout"),
                    
                    # Physical properties
                    "weight_kg": float(item.get("products_weight_kg", 0)) if item.get("products_weight_kg") else None,
                    "height": float(item.get("products_height", 0)) if item.get("products_height") else None,
                    "width": float(item.get("products_width", 0)) if item.get("products_width") else None,
                    "length": float(item.get("products_length", 0)) if item.get("products_length") else None,
                    
                    # Status and metadata
                    "status": item.get("products_status"),
                    "last_modified": item.get("products_last_modified"),
                    "average_rating": item.get("products_average_rating"),
                    
                    # URLs
                    "product_url": f"https://well.ca/product/{item.get('products_id', '')}" if item.get("products_id") else ""
                }
                
                product = Product(**product_data)
                all_products.append(product)
            except (ValidationError, ValueError, TypeError) as e:
                print(f"[bold yellow]⚠️ Skipping product due to error:[/bold yellow] {e}")
                continue
                
    except Exception as e:
        print(f"[bold red]❌ Error scraping products API: {e}[/bold red]")
    
    return all_products

# --- Main Scraping Logic ---
def main(test_mode: bool = False):
    """
    Main function to orchestrate the scraping process using brand links from database.
    
    Args:
        test_mode: If True, only scrape a small sample for testing
    """
    # --- Phase 3: Automation (Session and Headers) ---
    # Use curl_cffi's Session to mimic a real browser's TLS fingerprint.
    # This is the key step to avoid being blocked by anti-bot systems.
    session = requests.Session(
        impersonate="chrome110", # Mimics the TLS fingerprint of Chrome 110
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    )
    
    all_products: List[Product] = []
    brand_cache: dict = {}  # Cache for brand name lookups
    
    print("[bold cyan]🚀 Starting well.ca scraper using brand links from database...[/bold cyan]")
    
    # Get sample size based on test mode
    sample_size = 5 if test_mode else 20
    if test_mode:
        print("[bold yellow]🧪 Test mode: Limited to 5 brand links[/bold yellow]")
    
    # Get sampled brand links from database
    brand_links = get_wellca_brand_links(sample_size=sample_size)
    
    if not brand_links:
        print("❌ No brand links found, exiting...")
        return
    
    print(f"\n📋 Scraping products from {len(brand_links)} brand links:")
    for i, link in enumerate(brand_links, 1):
        print(f"  {i}. {link}")
    
    # Method 1: Use the products API for comprehensive data (optional)
    print("\n[bold]Method 1: Products API (baseline)[/bold]")
    products_api_data = scrape_products_api(session, brand_cache)
    all_products.extend(products_api_data)
    
    # Method 2: Scrape products from each brand link
    print(f"\n[bold]Method 2: Brand-specific scraping ({len(brand_links)} brands)[/bold]")
    
    for i, brand_url in enumerate(brand_links, 1):
        print(f"\n{'='*60}")
        print(f"🔍 Processing brand {i}/{len(brand_links)}: {brand_url}")
        print('='*60)
        
        brand_products = scrape_brand_products(session, brand_url, brand_cache)
        all_products.extend(brand_products)
        
        print(f"📊 Brand {i} results: {len(brand_products)} products")
        
        # Be respectful to the server
        time.sleep(1)

    print("-" * 50)
    print(f"[bold blue]📊 Total products scraped: {len(all_products)}[/bold blue]")

    # Print the first 5 products as an example
    if all_products:
        print("\n[bold]Sample of scraped data:[/bold]")
        for product in all_products[:5]:
            print(product.model_dump())

if __name__ == "__main__":
    import sys
    test_mode = "--test" in sys.argv
    main(test_mode=test_mode)
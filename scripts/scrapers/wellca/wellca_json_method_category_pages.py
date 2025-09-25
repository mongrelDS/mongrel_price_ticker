import time
import json
import os
from typing import List, Optional
from datetime import datetime
import pandas as pd

from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print
from rich.progress import Progress, TaskID

# --- Phase 4: Data Processing (Pydantic Models) ---
# Define a Pydantic model to structure and validate the product data we want.
# This ensures that if the API changes or a product has missing data, our script won't crash.
class Product(BaseModel):
    product_id: int
    name: str
    brand_name: Optional[str] = None
    sku: Optional[str] = None
    price: float
    product_url: str
    
    # Additional valuable fields
    quantity_text: Optional[str] = None  # e.g., "180 Capsules"
    subtitle: Optional[str] = None  # e.g., "250 mg"
    upc: Optional[str] = None  # UPC code
    weight_kg: Optional[float] = None  # Product weight
    image_url: Optional[str] = None  # Product image
    image_thumbnail: Optional[str] = None  # Thumbnail image
    image_full: Optional[str] = None  # Full size image
    sale_price: Optional[float] = None  # Sale price if on sale
    price_formatted: Optional[str] = None  # Formatted price string
    sale_price_formatted: Optional[str] = None  # Formatted sale price
    discount_formatted: Optional[str] = None  # Discount amount
    features: Optional[str] = None  # Product features/benefits
    ingredients: Optional[str] = None  # Product ingredients
    stock_quantity: Optional[int] = None  # Available stock
    can_checkout: Optional[bool] = None  # Whether product can be purchased
    rating: Optional[float] = None  # Average rating
    last_modified: Optional[str] = None  # Last modification date
    category_id: Optional[str] = None  # Category ID
    currency: Optional[str] = None  # Currency code
    source_category: Optional[str] = None  # Source category name
    breadcrumb: Optional[str] = None  # Category breadcrumb path

# --- Category Breadcrumb Resolution ---
def get_category_breadcrumb(session, category_id: str, category_cache: dict, max_retries: int = 3) -> str:
    """
    Get category breadcrumb path from category ID using API lookup with caching.
    """
    if category_id in category_cache:
        return category_cache[category_id]
    
    for attempt in range(max_retries):
        try:
            # Get all categories to build hierarchy
            response = session.get("https://well.ca/api/categories")
            if response.status_code == 200:
                categories_data = response.json()
                
                # Build category map
                category_map = {}
                def build_category_map(categories, parent_path=""):
                    for cat in categories:
                        current_path = f"{parent_path} > {cat['title']}" if parent_path else cat['title']
                        category_map[cat['id']] = current_path
                        
                        if 'subcategories' in cat and cat['subcategories']:
                            build_category_map(cat['subcategories'], current_path)
                
                build_category_map(categories_data)
                
                # Get breadcrumb for the specific category
                breadcrumb = category_map.get(category_id, f"Category {category_id}")
                category_cache[category_id] = breadcrumb
                return breadcrumb
            else:
                breadcrumb = f"Category {category_id}"
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
    
    breadcrumb = f"Category {category_id}"
    category_cache[category_id] = breadcrumb
    return breadcrumb

# --- Brand Name Resolution ---
def get_brand_name(session, brand_id: str, brand_cache: dict, max_retries: int = 3) -> str:
    """
    Get brand name from brand ID using API lookup with caching and retry logic.
    """
    if brand_id in brand_cache:
        return brand_cache[brand_id]
    
    for attempt in range(max_retries):
        try:
            response = session.get(f"https://well.ca/api/brands/{brand_id}")
            if response.status_code == 200:
                brand_data = response.json()
                brand_name = brand_data.get("title", f"Brand_{brand_id}")
                brand_cache[brand_id] = brand_name
                return brand_name
            elif response.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"[bold yellow]⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}[/bold yellow]")
                time.sleep(wait_time)
                continue
            else:
                brand_name = f"Brand_{brand_id}"
                brand_cache[brand_id] = brand_name
                return brand_name
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                print(f"[bold yellow]⚠️ Error getting brand name for ID {brand_id} after {max_retries} attempts: {e}[/bold yellow]")
            else:
                wait_time = 2 ** attempt
                print(f"[bold yellow]⚠️ Error getting brand name for ID {brand_id}, retrying in {wait_time}s: {e}[/bold yellow]")
                time.sleep(wait_time)
    
    brand_name = f"Brand_{brand_id}"
    brand_cache[brand_id] = brand_name
    return brand_name

# --- Data Persistence ---
def save_progress(products: List[Product], successful_queries: List[str], failed_queries: List[str], brand_cache: dict, category_cache: dict, filename: str = "scraping_progress.json"):
    """Save current progress to file for resuming later."""
    progress_data = {
        "timestamp": datetime.now().isoformat(),
        "total_products": len(products),
        "successful_queries": successful_queries,
        "failed_queries": failed_queries,
        "brand_cache": brand_cache,
        "category_cache": category_cache,
        "products": [product.model_dump() for product in products]
    }
    
    with open(filename, 'w') as f:
        json.dump(progress_data, f, indent=2)
    
    print(f"[bold blue]💾 Progress saved to {filename}[/bold blue]")

def load_progress(filename: str = "scraping_progress.json"):
    """Load previous progress if available."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                progress_data = json.load(f)
            
            products = [Product(**product_data) for product_data in progress_data.get("products", [])]
            return (
                products,
                progress_data.get("successful_queries", []),
                progress_data.get("failed_queries", []),
                progress_data.get("brand_cache", {}),
                progress_data.get("category_cache", {})
            )
        except Exception as e:
            print(f"[bold yellow]⚠️ Error loading progress: {e}[/bold yellow]")
    
    return [], [], [], {}, {}

# --- DataFrame Creation ---
def create_product_dataframe(products: List[Product], category_data: List[dict]) -> pd.DataFrame:
    """
    Create a pandas DataFrame from the scraped products with the specified fields.
    """
    data = []
    
    # Create a mapping from category_id to category name
    category_mapping = {cat['id']: cat['name'] for cat in category_data}
    
    # Since products have subcategory IDs, we'll use the main category names
    # based on which category page they were scraped from
    main_categories = {
        '4748': 'Water Bottles',
        '2910': 'Protein Powder Shakes', 
        '1443': 'Condiments Sauces Dressings',
        '698': 'Natural Home Lifestyle'
    }
    
    for product in products:
        # Create tag based on can_checkout value
        tag = "in stock" if product.can_checkout else "out of stock"
        
        # Use the source category from the scraping process
        category = product.source_category if product.source_category else "Unknown Category"
        
        row = {
            'name': product.name,
            'brand': product.brand_name,
            'sku': product.sku,
            'price': product.price,
            'quantity_text': product.quantity_text,
            'upc': product.upc,
            'weight_kg': product.weight_kg,
            'imgurl': product.image_url,
            'sale_price': product.sale_price,
            'tag': tag,
            'category': category,
            'breadcrumb': product.breadcrumb
            # Note: can_checkout column is dropped as requested
        }
        data.append(row)
    
    df_product = pd.DataFrame(data)
    return df_product

# --- Main Scraping Logic ---
def main():
    """
    Main function to orchestrate the scraping process.
    """
    # --- Phase 3: Automation (Session and Headers) ---
    # Use curl_cffi's Session to mimic a real browser's TLS fingerprint.
    # This is the key step to avoid being blocked by anti-bot systems.
    session = requests.Session(
        impersonate="chrome110", # Mimics the TLS fingerprint of Chrome 110
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    )
    
    # --- Phase 2: Inspection (API Endpoint and Parameters) ---
    # This is the backend API endpoint for category products.
    api_url = "https://well.ca/api/products"
    
    # Load previous progress if available
    all_products, successful_queries, failed_queries, brand_cache, category_cache = load_progress()
    
    # Configuration for large-scale scraping
    RATE_LIMIT_DELAY = 2  # Increased delay between requests
    BATCH_SAVE_INTERVAL = 5  # Save progress every N queries
    MAX_RETRIES = 3  # Max retries for failed requests
    
    # Category page URLs to scrape
    category_urls = [
        "https://well.ca/categories/water-bottles_4748.html",
        "https://well.ca/categories/protein-powder-shakes_2910.html", 
        "https://well.ca/categories/condiments-sauces-dressings_1443.html",
        "https://well.ca/categories/natural-home-lifestyle_698.html"
    ]
    
    # Extract category IDs from URLs
    category_data = []
    for url in category_urls:
        # Extract category ID from URL pattern: .../categories/name_id.html
        try:
            category_id = url.split('_')[-1].replace('.html', '')
            category_name = url.split('/')[-1].split('_')[0].replace('-', ' ').title()
            category_data.append({
                'id': category_id,
                'name': category_name,
                'url': url
            })
        except Exception as e:
            print(f"[bold red]❌ Error parsing URL {url}: {e}[/bold red]")
    
    print(f"[bold blue]📋 Found {len(category_data)} categories to process[/bold blue]")
    
    # Filter out already processed categories
    remaining_categories = [cat for cat in category_data if cat['id'] not in successful_queries and cat['id'] not in failed_queries]
    
    print("[bold cyan]🚀 Starting category page scraper for well.ca...[/bold cyan]")
    print(f"[bold blue]📋 Total categories: {len(category_data)} | Remaining: {len(remaining_categories)} | Already processed: {len(successful_queries + failed_queries)}[/bold blue]")
    print(f"[bold green]✅ Previously successful: {len(successful_queries)} | ❌ Previously failed: {len(failed_queries)}[/bold green]")
    print("-" * 80)

    with Progress() as progress:
        task = progress.add_task("[cyan]Processing categories...", total=len(remaining_categories))
        
        for i, category in enumerate(remaining_categories, 1):
            progress.update(task, advance=1, description=f"[cyan]Processing: {category['name'][:30]}...")
            
            # Parameters for the category API
            params = {"category_id": category['id']}
            
            # Retry logic for failed requests
            for attempt in range(MAX_RETRIES):
                try:
                    response = session.get(api_url, params=params)
                    
                    if response.status_code == 429:  # Rate limited
                        wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                        print(f"[bold yellow]⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}[/bold yellow]")
                        time.sleep(wait_time)
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    break
                    
                except requests.errors.RequestsError as e:
                    if attempt == MAX_RETRIES - 1:
                        print(f"[bold red]❌ Failed category '{category['name']}' after {MAX_RETRIES} attempts: {e}[/bold red]")
                        failed_queries.append(category['id'])
                        break
                    else:
                        wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                        print(f"[bold yellow]⚠️ Request error for '{category['name']}', retrying in {wait_time}s: {e}[/bold yellow]")
                        time.sleep(wait_time)
                        continue
                except Exception as e:
                    print(f"[bold red]❌ Unexpected error for category '{category['name']}': {e}[/bold red]")
                    failed_queries.append(category['id'])
                    break
            else:
                # If we get here, all retries failed
                failed_queries.append(category['id'])
                continue
            
            # Process the response
            if not data:
                print(f"[bold yellow]⚠️ No products found for category: {category['name']}[/bold yellow]")
                failed_queries.append(category['id'])
                continue
            
            print(f"📦 Found {len(data)} products for category: {category['name']}")
            successful_queries.append(category['id'])
            
            # Process products
            products_added = 0
            for item in data:
                try:
                    # Get brand name from brand ID
                    brand_id = str(item.get("brands_id", "")) if item.get("brands_id") else None
                    brand_name = get_brand_name(session, brand_id, brand_cache, MAX_RETRIES) if brand_id else None
                    
                    # Get category breadcrumb from category ID
                    category_id = str(item.get("master_categories_id", "")) if item.get("master_categories_id") else None
                    breadcrumb = get_category_breadcrumb(session, category_id, category_cache, MAX_RETRIES) if category_id else None
                    
                    # Map the API response fields to our Pydantic model
                    product_data = {
                        "product_id": int(item.get("products_id", 0)),
                        "name": item.get("products_name", ""),
                        "brand_name": brand_name,
                        "sku": str(item.get("products_id", "")) if item.get("products_id") else None,
                        "price": float(item.get("products_price", 0)),
                        "product_url": f"https://well.ca{item.get('products_url', '')}" if item.get('products_url') else "",
                        
                        # Additional valuable fields
                        "quantity_text": item.get("products_quantity_text"),
                        "subtitle": item.get("products_subtitle"),
                        "upc": item.get("products_upc"),
                        "weight_kg": float(item.get("products_weight_kg", 0)) if item.get("products_weight_kg") else None,
                        "image_url": item.get("products_image"),
                        "image_thumbnail": item.get("products_image_thumbnail"),
                        "image_full": item.get("products_image_full"),
                        "sale_price": float(item.get("products_sale_price", 0)) if item.get("products_sale_price") else None,
                        "price_formatted": item.get("products_price_formatted"),
                        "sale_price_formatted": item.get("products_sale_price_formatted"),
                        "discount_formatted": item.get("products_discount_formatted"),
                        "features": item.get("hybris_features"),
                        "ingredients": item.get("hybris_ingredients"),
                        "stock_quantity": int(item.get("products_quantity_order_stock", 0)) if item.get("products_quantity_order_stock") else None,
                        "can_checkout": item.get("can_checkout"),
                        "rating": float(item.get("products_average_rating", 0)) if item.get("products_average_rating") else None,
                        "last_modified": item.get("products_last_modified"),
                        "category_id": str(item.get("master_categories_id", "")) if item.get("master_categories_id") else None,
                        "currency": item.get("currency_code"),
                        "source_category": category['name'],
                        "breadcrumb": breadcrumb
                    }
                    
                    # Validate the data against our Pydantic model
                    product = Product(**product_data)
                    all_products.append(product)
                    products_added += 1
                    
                except ValidationError as e:
                    print(f"[bold yellow]⚠️ Skipping product due to validation error:[/bold yellow] {e}")
                except (ValueError, TypeError) as e:
                    print(f"[bold yellow]⚠️ Skipping product due to data conversion error:[/bold yellow] {e}")
            
            print(f"✅ Added {products_added} products from category: {category['name']}")
            
            # Save progress periodically
            if i % BATCH_SAVE_INTERVAL == 0:
                save_progress(all_products, successful_queries, failed_queries, brand_cache, category_cache)
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

    # Final progress save
    save_progress(all_products, successful_queries, failed_queries, brand_cache, category_cache)

    print("-" * 80)
    print(f"[bold blue]📊 SCRAPING SUMMARY[/bold blue]")
    print(f"[bold green]✅ Successful categories: {len(successful_queries)}/{len(category_data)}[/bold green]")
    print(f"[bold red]❌ Failed categories: {len(failed_queries)}/{len(category_data)}[/bold red]")
    print(f"[bold blue]📦 Total products scraped: {len(all_products)}[/bold blue]")
    print(f"[bold blue]🏷️ Unique brands discovered: {len(brand_cache)}[/bold blue]")
    
    if successful_queries:
        print(f"\n[bold green]✅ Successful categories:[/bold green]")
        for cat_id in successful_queries:
            category = next((cat for cat in category_data if cat['id'] == cat_id), None)
            if category:
                print(f"  • {category['name']} (ID: {cat_id})")
    
    if failed_queries:
        print(f"\n[bold red]❌ Failed categories:[/bold red]")
        for cat_id in failed_queries:
            category = next((cat for cat in category_data if cat['id'] == cat_id), None)
            if category:
                print(f"  • {category['name']} (ID: {cat_id})")

    # Print brand cache summary
    if brand_cache:
        print(f"\n[bold blue]🏷️ Brands discovered:[/bold blue]")
        for brand_id, brand_name in brand_cache.items():
            print(f"  • {brand_name} (ID: {brand_id})")

    # Print the first 3 products as an example
    if all_products:
        print(f"\n[bold]Sample of scraped data:[/bold]")
        for product in all_products[:3]:
            print(product.model_dump())
    
    # Create DataFrame from scraped products
    print(f"\n[bold cyan]📊 Creating product DataFrame...[/bold cyan]")
    df_product = create_product_dataframe(all_products, category_data)
    
    print(f"[bold green]✅ DataFrame created with {len(df_product)} products and {len(df_product.columns)} columns[/bold green]")
    print(f"[bold blue]📋 DataFrame columns: {list(df_product.columns)}[/bold blue]")
    
    # Display DataFrame info and sample
    print(f"\n[bold]📊 DataFrame Info:[/bold]")
    print(f"Shape: {df_product.shape}")
    print(f"Memory usage: {df_product.memory_usage(deep=True).sum() / 1024:.2f} KB")
    
    print(f"\n[bold]📋 Sample of df_product (first 5 rows):[/bold]")
    print(df_product.head().to_string())
    
    print(f"\n[bold]📈 Data Types:[/bold]")
    print(df_product.dtypes)
    
    # Save DataFrame to CSV
    # csv_filename = f"wellca_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    # df_product.to_csv(csv_filename, index=False)
    print(f"\n[bold green]💾 DataFrame saved to {csv_filename}[/bold green]")
    
    print(f"\n[bold green]💾 Progress saved to scraping_progress.json[/bold green]")
    print(f"[bold blue]🔄 To resume interrupted scraping, run the script again[/bold blue]")

if __name__ == "__main__":
    main()
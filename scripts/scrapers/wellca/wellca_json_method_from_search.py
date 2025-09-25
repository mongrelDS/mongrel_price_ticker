#!/usr/bin/env python3
"""
Well.ca Product Scraper with Database Integration
Scrapes product data from well.ca using search queries from database
"""

import json
import time
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd

# Web scraping and data validation
from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print
from rich.progress import Progress, TaskID

# Import required functions from src
import sys
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from get_domain import get_domain
from function_extract_volume import extract_volume
from generate_key import generate_key

# --- Phase 4: Data Processing (Pydantic Models) ---
class Product(BaseModel):
    product_id: int
    name: str
    brand_name: Optional[str] = None
    sku: Optional[str] = None
    price: float
    product_url: str

    # Additional valuable fields
    quantity_text: Optional[str] = None
    subtitle: Optional[str] = None
    upc: Optional[str] = None
    weight_kg: Optional[float] = None
    image_url: Optional[str] = None
    image_thumbnail: Optional[str] = None
    image_full: Optional[str] = None
    sale_price: Optional[float] = None
    price_formatted: Optional[str] = None
    sale_price_formatted: Optional[str] = None
    discount_formatted: Optional[str] = None
    features: Optional[str] = None
    ingredients: Optional[str] = None
    stock_quantity: Optional[int] = None
    can_checkout: Optional[bool] = None
    rating: Optional[float] = None
    last_modified: Optional[str] = None
    category_id: Optional[str] = None
    currency: Optional[str] = None
    source_category: Optional[str] = None
    breadcrumb: Optional[str] = None

# --- Brand Name Resolution ---
def get_brand_name(session, brand_id: str, brand_cache: dict, max_retries: int = 3) -> str:
    """Get brand name from brand ID using API lookup with caching and retry logic."""
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

# --- Category Breadcrumb Resolution ---
def get_category_breadcrumb(session, category_id: str, category_cache: dict, max_retries: int = 3) -> str:
    """Get category breadcrumb path from category ID using API lookup with caching."""
    if category_id in category_cache:
        return category_cache[category_id]

    for attempt in range(max_retries):
        try:
            # Get all categories to build hierarchy
            response = session.get("https://well.ca/api/categories")
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

# --- Data Persistence ---
def save_progress(products: List[Product], successful_queries: List[str], failed_queries: List[str], brand_cache: dict, category_cache: dict, filename: str = "scraping_progress.json"):
    """Save current progress to file for resuming later."""
    progress_data = {
        "timestamp": datetime.now().isoformat(),
        "products": [product.dict() for product in products],
        "successful_queries": successful_queries,
        "failed_queries": failed_queries,
        "brand_cache": brand_cache,
        "category_cache": category_cache
    }
    
    with open(filename, 'w') as f:
        json.dump(progress_data, f, indent=2)

def load_progress(filename: str = "scraping_progress.json"):
    """Load previous progress from file."""
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
    except FileNotFoundError:
        return [], [], [], {}, {}
    except Exception as e:
        print(f"[bold yellow]⚠️ Error loading progress: {e}[/bold yellow]")
        return [], [], [], {}, {}

# --- DataFrame Creation Functions ---
def create_df_ticker(products: List[Product]) -> pd.DataFrame:
    """Create df_ticker DataFrame with specified columns."""
    data = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    for product in products:
        # Get the lower value between price and sale_price, using nonzero prices
        final_price = product.price
        if product.sale_price and product.sale_price > 0:
            if product.price > 0:
                final_price = min(product.price, product.sale_price)
            else:
                final_price = product.sale_price
        elif product.price <= 0 and product.sale_price and product.sale_price > 0:
            final_price = product.sale_price

        # Create tag based on can_checkout value
        tag = "in stock" if product.can_checkout else "out of stock"

        row = {
            'sku': str(product.product_id),
            'link': f"https://well.ca/products/{product.product_id}.html",
            'price': final_price,
            'tag': tag,
            'date': current_date
        }
        data.append(row)

    df_ticker = pd.DataFrame(data)

    # Add domain column using the get_domain function
    df_ticker = get_domain(df_ticker, link_col='link')
    
    # Generate key using generate_key function
    df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")
    
    return df_ticker

def create_df_fixed_fields(products: List[Product]) -> pd.DataFrame:
    """Create df_fixed_fields DataFrame with specified columns."""
    data = []

    for product in products:
        # Convert weight_kg to string with "kg" unit
        weight_str = f"{product.weight_kg}kg" if product.weight_kg else None

        # Get the lower value between price and sale_price, using nonzero prices
        final_price = product.price
        if product.sale_price and product.sale_price > 0:
            if product.price > 0:
                final_price = min(product.price, product.sale_price)
            else:
                final_price = product.sale_price
        elif product.price <= 0 and product.sale_price and product.sale_price > 0:
            final_price = product.sale_price

        row = {
            'link': f"https://well.ca/products/{product.product_id}.html",
            'imgurl': product.image_url,
            'title': product.name,
            'brand': product.brand_name,
            'sku': str(product.product_id),
            'barcode': product.upc,
            'weight_kg': weight_str,  # Temporary column for volume extraction
            'breadcrumbs': product.breadcrumb
        }
        data.append(row)

    df_fixed_fields = pd.DataFrame(data)

    # Extract volume using the extract_volume function
    df_fixed_fields = extract_volume(df_fixed_fields, vol_col="weight_kg", result_col="vol")
    df_fixed_fields = df_fixed_fields.drop(columns=['weight_kg'])  # Drop the temporary column
    
    # Rename breadcrumbs to keywords
    df_fixed_fields = df_fixed_fields.rename(columns={'breadcrumbs': 'keywords'})
    
    return df_fixed_fields

# --- Main Scraping Logic ---
def main():
    """Main function to orchestrate the scraping process."""
    # Record start time for duration tracking
    start_time = datetime.now()
    
    # --- Phase 3: Automation (Session and Headers) ---
    session = requests.Session(
        impersonate="chrome110",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"}
    )

    # --- Get search queries from database ---
    print("[bold cyan]📊 Getting search queries from database...[/bold cyan]")
    try:
        # Get database engine
        db_engine = get_database_engine()

        # Read product names from database with safer approach
        import pandas as pd
        df_names = pd.read_sql_table('natura_product_table', db_engine)
        
        # Check if 'name' column exists
        if 'name' not in df_names.columns:
            print(f"[bold yellow]⚠️ 'name' column not found. Available columns: {list(df_names.columns)}[/bold yellow]")
            raise ValueError("'name' column not found in database")
        
        # Get a sample of the rows from this table
        sample_size = max(1, len(df_names) // 20)  # Ensure at least 1 row
        df_names = df_names.sample(n=min(sample_size, len(df_names)))
        df_names = df_names[['name']].dropna()  # Remove any null names

        # Create search queries from product names
        search_queries = []
        for name in df_names['name']:
            if pd.notna(name) and str(name).strip():
                words = str(name).split()[:5]  # Get the first 5 words
                search_term = " ".join(words)  # Join with ' '
                search_term = re.sub(r'[^a-zA-Z0-9\s+]+', ' ', search_term)  # Replace non-alphanumeric with spaces
                search_term = re.sub(r'\s+', ' ', search_term)  # Replace multiple spaces with single space
                search_term = search_term.lower().strip()  # Lowercase and trim
                if search_term and len(search_term) > 3:  # Only add meaningful search terms
                    search_queries.append(search_term)

        # Remove duplicates while preserving order
        search_queries = list(dict.fromkeys(search_queries))

        print(f"[bold green]✅ Generated {len(search_queries)} unique search queries from database[/bold green]")
        print(f"[bold blue]📋 Sample queries: {search_queries[:5]}[/bold blue]")

    except Exception as e:
        print(f"[bold red]❌ Error getting search queries from database: {e}[/bold red]")
        print("[bold yellow]⚠️ Using fallback search queries[/bold yellow]")
        # Fallback search queries
        search_queries = [
            "organika sugarfree preworkout",
            "organika organic coconut",
            "woop4 vegan mayo",
            "sprague organic tuscanystyle",
            "madegood crispy light"
        ]

    # --- Phase 5: Scraping Logic ---
    api_url = "https://well.ca/api/search/products"
    
    # Load previous progress if available
    all_products, successful_queries, failed_queries, brand_cache, category_cache = load_progress()

    # Configuration for large-scale scraping
    RATE_LIMIT_DELAY = 2  # Increased delay between requests
    BATCH_SAVE_INTERVAL = 50  # Save progress every 50 queries
    MAX_RETRIES = 3

    # Filter out already processed queries
    remaining_queries = [q for q in search_queries if q not in successful_queries and q not in failed_queries]
    
    print(f"[bold cyan]🚀 Starting targeted product scraper for well.ca...[/bold cyan]")
    print(f"[bold blue]📋 Total queries: {len(search_queries)} | Remaining: {len(remaining_queries)} | Already processed: {len(search_queries) - len(remaining_queries)}[/bold blue]")
    print(f"[bold green]✅ Previously successful: {len(successful_queries)} | ❌ Previously failed: {len(failed_queries)}[/bold green]")
    print("-" * 80)

    with Progress() as progress:
        task = progress.add_task("[green]Scraping products...", total=len(remaining_queries))

        for i, query in enumerate(remaining_queries):
            # Rate limiting
            if i > 0:
                time.sleep(RATE_LIMIT_DELAY)

            # Retry logic for API calls
            data = None
            for attempt in range(MAX_RETRIES):
                try:
                    params = {"query": query}
                    response = session.get(api_url, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        break
                    elif response.status_code == 429:  # Rate limited
                        wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                        print(f"[bold yellow]⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}[/bold yellow]")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"[bold red]❌ HTTP {response.status_code} for query: {query}[/bold red]")
                        if attempt == MAX_RETRIES - 1:
                            failed_queries.append(query)
                            break
                        else:
                            wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                            time.sleep(wait_time)
                            continue

                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        print(f"[bold red]❌ Error for query '{query}' after {MAX_RETRIES} attempts: {e}[/bold red]")
                        failed_queries.append(query)
                        break
                    else:
                        wait_time = RATE_LIMIT_DELAY * (2 ** attempt)
                        print(f"[bold yellow]⚠️ Error for query '{query}', retrying in {wait_time}s: {e}[/bold yellow]")
                        time.sleep(wait_time)
                        continue

            if data is None or len(data) == 0:
                print(f"[bold yellow]⚠️ No products found for query: {query}[/bold yellow]")
                failed_queries.append(query)
                progress.update(task, advance=1)
                continue

            print(f"📦 Found {len(data)} products for query: {query}")
            successful_queries.append(query)
            
            # Process products
            products_added = 0
            for item in data:
                try:
                    # Get brand name from brand ID
                    brand_id = str(item.get("brands_id", "")) if item.get("brands_id") else None
                    brand_name = None
                    if brand_id:
                        brand_name = get_brand_name(session, brand_id, brand_cache)

                    # Get category breadcrumb
                    category_id = str(item.get("master_categories_id", "")) if item.get("master_categories_id") else None
                    breadcrumb = None
                    if category_id:
                        breadcrumb = get_category_breadcrumb(session, category_id, category_cache)

                    # Map the API response to our Product model
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
                        "source_category": query,
                        "breadcrumb": breadcrumb
                    }

                    # Validate the data against our Pydantic model
                    product = Product(**product_data)
                    all_products.append(product)
                    products_added += 1
                    
                except ValidationError as e:
                    print(f"[bold yellow]⚠️ Skipping product due to validation error:[/bold yellow] {e}")
                    continue
                except Exception as e:
                    print(f"[bold yellow]⚠️ Error processing product: {e}[/bold yellow]")
                    continue

            print(f"[bold green]✅ Added {products_added} products from query: {query}[/bold green]")

            # Update progress
            progress.update(task, advance=1)

            # Save progress periodically
            if (i + 1) % BATCH_SAVE_INTERVAL == 0:
                save_progress(all_products, successful_queries, failed_queries, brand_cache, category_cache)
                print(f"[bold blue]💾 Progress saved at query {i + 1}/{len(remaining_queries)}[/bold blue]")

    # --- Create DataFrames ---
    print(f"\n[bold cyan]📊 Creating DataFrames...[/bold cyan]")
    
    # Create df_ticker
    df_ticker = create_df_ticker(all_products)
    print(f"[bold green]✅ df_ticker created: {len(df_ticker)} records[/bold green]")
    
    # Create df_fixed_fields
    df_fixed_fields = create_df_fixed_fields(all_products)
    print(f"[bold green]✅ df_fixed_fields created: {len(df_fixed_fields)} records[/bold green]")

    # --- Save DataFrames to CSV ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ticker_filename = f"wellca_ticker_{timestamp}.csv"
    fixed_fields_filename = f"wellca_fixed_fields_{timestamp}.csv"
    
    df_ticker.to_csv(ticker_filename, index=False)
    df_fixed_fields.to_csv(fixed_fields_filename, index=False)
    
    print(f"\n[bold green]💾 DataFrames saved:[/bold green]")
    print(f"  • df_ticker: {ticker_filename}")
    print(f"  • df_fixed_fields: {fixed_fields_filename}")
    
    # --- Upsert DataFrames to Database ---
    print(f"\n[bold cyan]📊 Upserting DataFrames to database...[/bold cyan]")
    try:
        # Get database engine
        db_engine = get_database_engine()
        
        # Upsert df_ticker to df_ticker table
        print("[bold blue]📤 Upserting df_ticker to database...[/bold blue]")
        upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
        print(f"[bold green]✅ df_ticker upserted successfully ({len(df_ticker)} records)[/bold green]")
        
        # Upsert df_fixed_fields to fixed_fields table
        print("[bold blue]📤 Upserting df_fixed_fields to database...[/bold blue]")
        upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
        print(f"[bold green]✅ df_fixed_fields upserted successfully ({len(df_fixed_fields)} records)[/bold green]")
        
    except Exception as e:
        print(f"[bold red]❌ Error upserting to database: {e}[/bold red]")
        import traceback
        traceback.print_exc()
    
    # --- Duration Tracking ---
    print(f"\n[bold cyan]⏱️ Recording duration metrics...[/bold cyan]")
    try:
        # Calculate duration
        end_time = datetime.now()
        duration_in_minutes = (end_time - start_time).total_seconds() / 60
        
        # Prepare duration data
        DOMAIN = 'well.ca'
        df_duration = pd.DataFrame({
            'duration_min': [duration_in_minutes],
            'date': [datetime.now()],
            'results': [len(df_ticker)],
            'domain': [DOMAIN],
            'type': ['item_update']
        })
        df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
        
        # Upsert to duration table
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        print(f"[bold green]✅ Duration metrics recorded: {duration_in_minutes:.2f} minutes, {len(df_ticker)} results[/bold green]")
        print(f"[bold blue]📊 Results per minute: {df_duration['result_per_minute'].iloc[0]:.2f}[/bold blue]")
        
    except Exception as e:
        print(f"[bold red]❌ Error recording duration metrics: {e}[/bold red]")
    
    # --- Final Summary ---
    print(f"\n[bold green]🎉 Scraping completed![/bold green]")
    print(f"[bold blue]📊 Summary:[/bold blue]")
    print(f"  • Total products scraped: {len(all_products)}")
    print(f"  • Successful queries: {len(successful_queries)}")
    print(f"  • Failed queries: {len(failed_queries)}")
    print(f"  • Brand cache entries: {len(brand_cache)}")
    print(f"  • Category cache entries: {len(category_cache)}")
    print(f"  • df_ticker records: {len(df_ticker)}")
    print(f"  • df_fixed_fields records: {len(df_fixed_fields)}")
    
    # Save final progress
    save_progress(all_products, successful_queries, failed_queries, brand_cache, category_cache)
    print(f"\n[bold green]💾 Progress saved to scraping_progress.json[/bold green]")
    print(f"[bold blue]🔄 To resume interrupted scraping, run the script again[/bold blue]")

if __name__ == "__main__":
    main()
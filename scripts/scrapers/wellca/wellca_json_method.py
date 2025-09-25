import time
from typing import List, Optional

from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print

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
    # This is the backend API endpoint we discovered.
    api_url = "https://well.ca/api/search/products"
    
    all_products: List[Product] = []
    
    # Search queries to get different categories of products
    search_queries = [
        "vitamin", "supplement", "health", "wellness", "beauty", "skincare", 
        "baby", "organic", "natural", "protein", "mineral", "herbal", 
        "probiotic", "omega", "multivitamin", "calcium", "iron", "magnesium",
        "vitamin d", "vitamin c", "b complex", "fish oil", "collagen",
        "antioxidant", "immune", "energy", "sleep", "stress", "digestive"
    ]
    
    print("[bold cyan]🚀 Starting scraper for well.ca...[/bold cyan]")

    for query in search_queries:
        print(f"🔍 Searching for: {query}")
        
        # Parameters for the search API
        params = {
            "query": query
        }

        try:
            response = session.get(api_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            
            data = response.json()
            
            # The API returns a list of products directly
            if not data:
                print(f"[bold yellow]⚠️ No products found for query: {query}[/bold yellow]")
                continue
            
            print(f"📦 Found {len(data)} products for query: {query}")
            
            # Loop through the products returned
            for item in data:
                try:
                    # Map the API response fields to our Pydantic model
                    product_data = {
                        "product_id": int(item.get("products_id", 0)),
                        "name": item.get("products_name", ""),
                        "brand_name": str(item.get("brands_id", "")) if item.get("brands_id") else None,
                        "sku": str(item.get("products_code", "")) if item.get("products_code") else None,
                        "price": float(item.get("products_price", 0)),
                        "product_url": f"https://well.ca{item.get('products_url', '')}" if item.get('products_url') else ""
                    }
                    
                    # Validate the data against our Pydantic model
                    product = Product(**product_data)
                    all_products.append(product)
                except ValidationError as e:
                    print(f"[bold yellow]⚠️ Skipping product due to validation error:[/bold yellow] {e}")
                except (ValueError, TypeError) as e:
                    print(f"[bold yellow]⚠️ Skipping product due to data conversion error:[/bold yellow] {e}")
            
            time.sleep(1) # Be respectful to the server, wait 1 second between requests

        except requests.errors.RequestsError as e:
            print(f"[bold red]❌ An error occurred during the request for query '{query}': {e}[/bold red]")
            continue
        except Exception as e:
            print(f"[bold red]❌ An unexpected error occurred for query '{query}': {e}[/bold red]")
            continue

    print("-" * 50)
    print(f"[bold blue]📊 Total products scraped: {len(all_products)}[/bold blue]")

    # Print the first 5 products as an example
    if all_products:
        print("\n[bold]Sample of scraped data:[/bold]")
        for product in all_products[:5]:
            print(product.model_dump())

if __name__ == "__main__":
    main()
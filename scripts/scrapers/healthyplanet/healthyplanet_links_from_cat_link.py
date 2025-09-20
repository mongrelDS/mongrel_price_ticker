
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import sys
import os
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, '..', '..', '..', 'src')
src_dir_abs = os.path.abspath(src_dir)
sys.path.append(src_dir_abs)

# Import database functions
from mySQL_Upsert_Function import read_mysql_to_df, upsert_df_to_mysql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Database connection setup (using environment variables)
db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
db_password = os.getenv('DB_PASSWORD', 'taan2#IbizaI')
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')

# Create database connection string
connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

# Create database engine
db_engine = create_engine(connection_string, poolclass=NullPool)

# Read brand links from database
print("Reading brand links from database...")
df_link = read_mysql_to_df(engine=db_engine, table_name='cat_link_list')
# keep only the links that start with https://www.healthyplanetcanada.com
df_link = df_link[df_link['link'].str.startswith('https://www.healthyplanetcanada.com')]
print(f"Found {len(df_link)} Healthy Planet links")

# Sample up to 90 links if we have enough, otherwise use all
if len(df_link) >= 90:
    df_link = df_link.sample(90)
    print(f"Selected 90 links for processing")
else:
    print(f"Using all {len(df_link)} links for processing")

# --- Scraping Function ---
def scrape_products_from_url(url, session=None):
    """Scrapes all product details (name, price, link, image) from a given URL."""
    print(f" Scraping URL: {url}")
    
    page_products = []
    try:
        # Use session if provided, otherwise create a new request
        if session:
            response = session.get(url, timeout=15)
        else:
            response = requests.get(url, timeout=15)
        
        # Check for suspicious status codes that might indicate blocking
        if response.status_code == 429:
            print(f"  ⚠️ Rate limited (429) - potential blocking")
            return page_products, "rate_limited"
        elif response.status_code == 403:
            print(f"  ⚠️ Forbidden (403) - potential blocking")
            return page_products, "forbidden"
        elif response.status_code == 503:
            print(f"  ⚠️ Service unavailable (503) - potential blocking")
            return page_products, "service_unavailable"
        
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for blocking indicators in page content
        page_text = soup.get_text().lower()
        blocking_indicators = [
            'access denied', 'blocked', 'captcha', 'cloudflare',
            'rate limit', 'too many requests', 'suspicious activity'
        ]
        
        for indicator in blocking_indicators:
            if indicator in page_text:
                print(f"  ⚠️ Blocking indicator found in content: '{indicator}'")
                return page_products, "content_blocked"

        # Find the main container for each product, which holds both image and info.
        # The class 'product-item' is a common container for this.
        product_containers = soup.find_all('li', class_='product-item')

        for item in product_containers:
            # Find elements within the product container
            name_element = item.find('a', class_='product-item-link')
            price_element = item.find('span', class_='price')
            image_element = item.find('img', class_='product-image-photo') # Find the image tag

            # Ensure all required elements are found
            if name_element and price_element and image_element:
                page_products.append({
                    'item_name': name_element.text.strip(),
                    'price': price_element.text.strip(),
                    'link': name_element.get('href'),
                    'image_url': image_element.get('src') # Get the 'src' attribute
                })
        
        return page_products, "success"
        
    except requests.exceptions.RequestException as e:
        print(f"  -> Error scraping {url}: {e}")
        return page_products, "request_error"

# --- 3. Main Loop and Data Integration ---
all_products_data = []

# Create a session with retry strategy and IPBurger proxy (same as healthyplanet_scraper.py)
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Configure IPBurger proxy (same as healthyplanet_scraper.py)
proxy_config = {
    'host': 'residential.ipb.cloud',
    'port': '7777',
    'username': 'customer-mnft29185901-city-toronto-sessid-oUcO-sesstime-30',
    'password': 'xyspgptxmm_J9v'
}

proxy_url = f"http://{proxy_config['username']}:{proxy_config['password']}@{proxy_config['host']}:{proxy_config['port']}"
session.proxies = {
    'http': proxy_url,
    'https': proxy_url
}

# Set headers to mimic real browser (same as healthyplanet_scraper.py)
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',  # Avoid Brotli compression issues
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
})

# Test proxy connection
print("🔍 Testing proxy connection...")
try:
    test_response = session.get("http://httpbin.org/ip", timeout=15)
    if test_response.status_code == 200 and "origin" in test_response.text:
        print(f"✅ Proxy working! IP: {test_response.text}")
    else:
        print(f"❌ Proxy test failed: {test_response.status_code}")
except Exception as e:
    print(f"❌ Proxy test error: {e}")
    print("⚠️ Continuing with proxy anyway...")

successful_requests = 0
failed_requests = 0
consecutive_failures = 0
blocking_detected = False
blocking_indicators_count = 0

# Blocking detection thresholds
MAX_CONSECUTIVE_FAILURES = 5
MIN_SUCCESS_RATE = 0.3  # 30% success rate minimum
MIN_REQUESTS_FOR_RATE_CHECK = 10
MAX_BLOCKING_INDICATORS = 3  # Max blocking indicators before stopping

def check_for_blocking(successful, failed, consecutive_fails, blocking_indicators=0):
    """Check if we're likely being blocked based on failure patterns."""
    total_requests = successful + failed
    
    # Check consecutive failures
    if consecutive_fails >= MAX_CONSECUTIVE_FAILURES:
        return True, f"Too many consecutive failures ({consecutive_fails})"
    
    # Check for too many blocking indicators
    if blocking_indicators >= MAX_BLOCKING_INDICATORS:
        return True, f"Too many blocking indicators detected ({blocking_indicators})"
    
    # Check success rate (only after minimum requests)
    if total_requests >= MIN_REQUESTS_FOR_RATE_CHECK:
        success_rate = successful / total_requests
        if success_rate < MIN_SUCCESS_RATE:
            return True, f"Success rate too low ({success_rate:.1%})"
    
    return False, ""

for index, row in df_link.iterrows():
    # Check for blocking before processing each request
    if blocking_detected:
        print(f"🛑 Blocking detected! Stopping early at request {index + 1}/{len(df_link)}")
        break
    
    link_url = row['link']
    print(f"Processing link {index + 1}/{len(df_link)}: {link_url}")
    
    try:
        scraped_items, status = scrape_products_from_url(link_url, session)
        
        # Handle different response statuses
        if status == "success":
            # Check if we got suspiciously few products (potential blocking)
            if len(scraped_items) == 0:
                print(f"  ⚠️ No products found - potential blocking indicator")
                consecutive_failures += 1
                blocking_indicators_count += 1
            else:
                consecutive_failures = 0  # Reset on success
            
            for item in scraped_items:
                # Add the source URL to track where the product came from
                item['source_url'] = link_url
                all_products_data.append(item)
            
            print(f"  Found {len(scraped_items)} products")
            successful_requests += 1
            
        elif status in ["rate_limited", "forbidden", "service_unavailable", "content_blocked"]:
            print(f"  🚨 Blocking indicator detected: {status}")
            failed_requests += 1
            consecutive_failures += 1
            blocking_indicators_count += 1
            
        else:  # request_error or other errors
            failed_requests += 1
            consecutive_failures += 1
        
        # Check for blocking after each request
        is_blocked, reason = check_for_blocking(successful_requests, failed_requests, consecutive_failures, blocking_indicators_count)
        if is_blocked:
            blocking_detected = True
            print(f"🚨 BLOCKING DETECTED: {reason}")
            print(f"   Success rate: {successful_requests}/{successful_requests + failed_requests} ({successful_requests/(successful_requests + failed_requests)*100:.1f}%)")
            print(f"   Consecutive failures: {consecutive_failures}")
            print(f"   Blocking indicators: {blocking_indicators_count}")
            break
        
        # Longer delay to be more respectful and avoid rate limiting
        time.sleep(random.uniform(2, 5))
        
    except Exception as e:
        print(f"  Error processing {link_url}: {e}")
        failed_requests += 1
        consecutive_failures += 1
        
        # Check for blocking after each failed request
        is_blocked, reason = check_for_blocking(successful_requests, failed_requests, consecutive_failures, blocking_indicators_count)
        if is_blocked:
            blocking_detected = True
            print(f"🚨 BLOCKING DETECTED: {reason}")
            print(f"   Success rate: {successful_requests}/{successful_requests + failed_requests} ({successful_requests/(successful_requests + failed_requests)*100:.1f}%)")
            print(f"   Consecutive failures: {consecutive_failures}")
            print(f"   Blocking indicators: {blocking_indicators_count}")
            break
        
        continue

print(f"\nScraping Summary:")
print(f"  Successful requests: {successful_requests}")
print(f"  Failed requests: {failed_requests}")
if successful_requests + failed_requests > 0:
    print(f"  Success rate: {successful_requests/(successful_requests+failed_requests)*100:.1f}%")
print(f"  Consecutive failures: {consecutive_failures}")
print(f"  Blocking indicators: {blocking_indicators_count}")
if blocking_detected:
    print(f"  🚨 SCRAPING STOPPED EARLY DUE TO BLOCKING DETECTION")
    print(f"  💡 Consider:")
    print(f"     - Waiting longer before retrying")
    print(f"     - Using a different proxy")
    print(f"     - Reducing request frequency")
    print(f"     - Checking if the website structure has changed")

# --- Create DataFrame and Save to Database ---
if all_products_data:
    df_products = pd.DataFrame(all_products_data)
    # dropna price
    df_products = df_products.dropna(subset=['price'])
    # drop column source_url
    df_products = df_products.drop(columns=['source_url'])
    print(f"\nTotal products scraped: {len(df_products)}")
    
    
    
    # Upload to database
    print("\nUploading to database...")
    try:
        upsert_df_to_mysql(df=df_products, engine=db_engine, target_table='healthyplanet_product_links', key_col='link')
        print("✅ Database upload complete!")
    except Exception as e:
        print(f"❌ Database upload failed: {e}")
else:
    print("No products were scraped.")
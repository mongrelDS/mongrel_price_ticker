# @title Healthy Planet Product Details
# use playwright to scrape the product details
from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import time
import concurrent.futures
import sys
import os
import random
from datetime import datetime
import logging
import traceback

# Add src folder to path to import MySQL functions
# Get the project root by going up from the current script location
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..', '..', '..')
project_root = os.path.abspath(project_root)
src_dir = os.path.join(project_root, 'src')

# Add both project root and src directory to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Debug: Print paths for troubleshooting
print(f"Current script directory: {current_dir}")
print(f"Project root: {project_root}")
print(f"Source directory: {src_dir}")
print(f"Python path: {sys.path[:3]}")  # Show first 3 entries

# Import with error handling
try:
    from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
    print("✅ Successfully imported mySQL_Upsert_Function_with_Batch")
except ImportError as e:
    print(f"❌ Failed to import mySQL_Upsert_Function_with_Batch: {e}")
    sys.exit(1)

try:
    from database_config import get_database_engine, get_database_credentials
    print("✅ Successfully imported database_config")
except ImportError as e:
    print(f"❌ Failed to import database_config: {e}")
    sys.exit(1)

try:
    from price_to_float import price_to_float
    print("✅ Successfully imported price_to_float")
except ImportError as e:
    print(f"❌ Failed to import price_to_float: {e}")
    sys.exit(1)

try:
    from get_domain import get_domain
    print("✅ Successfully imported get_domain")
except ImportError as e:
    print(f"❌ Failed to import get_domain: {e}")
    sys.exit(1)

try:
    from function_extract_volume import extract_volume
    print("✅ Successfully imported function_extract_volume")
except ImportError as e:
    print(f"❌ Failed to import function_extract_volume: {e}")
    sys.exit(1)

try:
    from generate_key import generate_key
    print("✅ Successfully imported generate_key")
except ImportError as e:
    print(f"❌ Failed to import generate_key: {e}")
    sys.exit(1)

from playwright_stealth.stealth import Stealth


# @title Configuration
# Auto-detect headless mode based on environment
import os
HEADLESS_MODE = not os.environ.get('DISPLAY')  # Auto-detect: headless if no display available

# Log the detected mode
if HEADLESS_MODE:
    print("🖥️  No display detected - running in headless mode")
else:
    print("🖥️  Display detected - running in GUI mode")

# @title item Update

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('healthyplanet_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def safe_database_operation(operation_func, *args, **kwargs):
    """Safely execute database operations with error handling and retries"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"Database operation failed after {max_retries} attempts: {str(e)}")
                raise
            time.sleep(2 ** attempt)  # Exponential backoff

def safe_data_processing(processing_func, df, *args, **kwargs):
    """Safely execute data processing functions with error handling"""
    try:
        return processing_func(df, *args, **kwargs)
    except Exception as e:
        logger.error(f"Data processing error in {processing_func.__name__}: {str(e)}")
        logger.error(f"DataFrame shape: {df.shape}")
        logger.error(f"DataFrame columns: {df.columns.tolist()}")
        # Return original DataFrame if processing fails
        return df

# Initialize database engine using src folder configuration
try:
    db_engine = get_database_engine()
    logger.info("Database connection established successfully")
except Exception as e:
    logger.error(f"Failed to establish database connection: {str(e)}")
    sys.exit(1)

# Start timing
start_time = time.time()

try:
    df_link = safe_database_operation(read_mysql_to_df, engine=db_engine, table_name='fixed_fields')
    logger.info(f"Successfully loaded {len(df_link)} records from fixed_fields table")
except Exception as e:
    logger.error(f"Failed to load data from fixed_fields table: {str(e)}")
    sys.exit(1)
# df_link = df_link  where doain str includes healthyplanetcanada.com
df_link = df_link[df_link['domain'].str.contains('healthyplanetcanada.com')]
# select rows where sku is null  or brand is null
df_link = df_link[df_link['sku'].isnull() | df_link['brand'].isnull()]
df_link = df_link.head(30)  

# use proxy_config to get proxy
try:
    from proxy_config import get_proxy_for_playwright, get_proxy_config, record_proxy_usage, switch_proxy_credential, get_proxy_stats, test_proxy_connection
    print("✅ Successfully imported proxy_config")
except ImportError as e:
    print(f"❌ Failed to import proxy_config: {e}")
    sys.exit(1)


# --- Scraper Configuration ---
scraped_data_list = [] # A list to hold dictionaries of scraped data

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
]

async def warm_up_session(page):
    """Perform warm-up activities to appear more human and bypass protection."""
    logger.info("Warming up session...")
    try:
        # Start with homepage to establish session
        await page.goto('https://www.healthyplanetcanada.com/', wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(random.uniform(3000, 5000))

        # Simulate human behavior - scroll and move mouse
        await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
        await page.evaluate(f"window.scrollTo(0, {random.randint(100, 500)})")
        await page.wait_for_timeout(random.uniform(1000, 2000))

        # Try to find and click the cookie consent button
        cookie_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("I Accept")',
            'button:has-text("Agree")',
            '#cookie-accept',
            '.cookie-accept',
            '[data-testid="cookie-accept"]'
        ]
        
        for selector in cookie_selectors:
            try:
                cookie_button = await page.query_selector(selector)
                if cookie_button:
                    await cookie_button.click()
                    logger.info(f"Clicked cookie consent button using selector: {selector}")
                    await page.wait_for_timeout(random.uniform(1000, 2000))
                    break
            except:
                continue
        
        # Additional warm-up: visit a category page
        try:
            await page.goto('https://www.healthyplanetcanada.com/vitamins-supplements.html', wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(random.uniform(2000, 4000))
            
            # Simulate browsing behavior
            await page.mouse.move(random.randint(200, 1000), random.randint(200, 800))
            await page.evaluate(f"window.scrollTo(0, {random.randint(200, 800)})")
            await page.wait_for_timeout(random.uniform(1500, 3000))
        except Exception as e:
            logger.warning(f"Category page warm-up failed: {e}")
        
        logger.info("Session warm-up complete.")
    except Exception as e:
        logger.warning(f"Error during session warm-up: {e}")


async def scrape_product_details(url, page, max_retries=1):
    """Scrape product details from a single URL using Playwright with retry mechanism"""
    logger.info(f"Scraping: {url}")
    
    for attempt in range(max_retries):
        try:
            # Navigate to the product page with timeout
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for page to load
            
            # Add human-like behavior
            try:
                # Random mouse movement
                await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
                await page.wait_for_timeout(random.randint(500, 1500))
                
                # Random scroll
                await page.evaluate(f"window.scrollTo(0, {random.randint(100, 500)})")
                await page.wait_for_timeout(random.randint(1000, 2000))
            except Exception as e:
                logger.debug(f"Human-like behavior simulation failed: {e}")
            
            # Check if we're on a verification/CAPTCHA page or blocked
            page_content = await page.content()
            page_url = page.url
            
            # Check for various blocking indicators
            blocking_indicators = [
                'verification required', 'captcha', 'unusual activity', 'bot activity',
                'access denied', 'forbidden', 'blocked', 'datadome', 'cloudflare',
                'please verify', 'security check', 'robot', 'automated'
            ]
            
            is_blocked = (
                any(keyword in page_content.lower() for keyword in blocking_indicators) or
                '403' in page_content or
                'datadome' in page_content.lower() or
                len(page_content) < 5000  # Very short content usually indicates blocking
            )
            
            if is_blocked:
                logger.warning(f"Detected blocking/protection page for {url}, attempt {attempt + 1}")
                logger.warning(f"Page URL: {page_url}")
                logger.warning(f"Content length: {len(page_content)}")
                
                # Take a screenshot for debugging
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_path = f"blocked_page_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                logger.info(f"Screenshot of blocked page saved to {screenshot_path}")
                
                # Save HTML for debugging
                html_path = f"blocked_page_{timestamp}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(page_content)
                logger.info(f"HTML of blocked page saved to {html_path}")
                
                if attempt < max_retries - 1:
                    # Wait longer and try again with different approach
                    wait_time = 15000 + (attempt * 10000)  # Increasing wait time
                    logger.info(f"Waiting {wait_time/1000} seconds before retry...")
                    await page.wait_for_timeout(wait_time)
                    
                    # Try to refresh the page
                    try:
                        await page.reload(wait_until='networkidle', timeout=30000)
                        await page.wait_for_timeout(3000)
                    except:
                        pass
                    continue
                else:
                    logger.error(f"Blocked page detected for {url} after {max_retries} attempts")
                    return {'link': url, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'title': None, 'brand': None, 'price': None, 'sku': None, 'tag': None, 'keywords': None, 'blocked': True}
            
            # A dictionary to hold data for this single product
            product_details = {'link': url, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

            # --- Scrape each field with multiple selector fallbacks ---
            
            # Title scraping with multiple selectors
            title_selectors = [
                'h1.page-title',
                'h1.product-name',
                'h1',
                '.page-title',
                '.product-title',
                '[data-testid="product-title"]',
                '.product-name',
                'h1[class*="title"]'
            ]
            
            product_details['title'] = None
            for selector in title_selectors:
                try:
                    title_element = await page.query_selector(selector)
                    if title_element:
                        title_text = await title_element.text_content()
                        if title_text and title_text.strip():
                            product_details['title'] = title_text.strip()
                            logger.debug(f"Title scraped using '{selector}': {product_details['title']}")
                            break
                except Exception as e:
                    logger.debug(f"Title selector '{selector}' failed: {str(e)}")
                    continue
            
            if not product_details['title']:
                logger.warning(f"Failed to scrape title for {url} with any selector")

            # Brand scraping with multiple selectors
            brand_selectors = [
                'span.brand-name a',
                '.brand-name a',
                '.brand a',
                '[data-testid="brand"]',
                '.product-brand',
                'span[class*="brand"] a',
                '.manufacturer a',
                'a[href*="brand"]'
            ]
            
            product_details['brand'] = None
            for selector in brand_selectors:
                try:
                    brand_element = await page.query_selector(selector)
                    if brand_element:
                        brand_text = await brand_element.text_content()
                        if brand_text and brand_text.strip():
                            product_details['brand'] = brand_text.strip()
                            logger.debug(f"Brand scraped using '{selector}': {product_details['brand']}")
                            break
                except Exception as e:
                    logger.debug(f"Brand selector '{selector}' failed: {str(e)}")
                    continue
            
            if not product_details['brand']:
                logger.warning(f"Failed to scrape brand for {url} with any selector")

            # Price scraping with multiple selectors
            price_selectors = [
                'span.price',
                '.price',
                '[data-testid="price"]',
                '.product-price',
                '.price-current',
                '.current-price',
                'span[class*="price"]',
                '.price-box .price',
                '.price-wrapper .price'
            ]
            
            product_details['price'] = None
            for selector in price_selectors:
                try:
                    price_element = await page.query_selector(selector)
                    if price_element:
                        price_text = await price_element.text_content()
                        if price_text and price_text.strip():
                            product_details['price'] = price_text.strip()
                            logger.debug(f"Price scraped using '{selector}': {product_details['price']}")
                            break
                except Exception as e:
                    logger.debug(f"Price selector '{selector}' failed: {str(e)}")
                    continue
            
            if not product_details['price']:
                logger.warning(f"Failed to scrape price for {url} with any selector")

            # SKU scraping with multiple selectors
            sku_selectors = [
                'div.product.attribute.sku .value',
                '.product-attribute.sku .value',
                '.sku .value',
                '[data-testid="sku"]',
                '.product-sku',
                'span[class*="sku"]',
                '.product-code',
                '.item-number'
            ]
            
            product_details['sku'] = None
            for selector in sku_selectors:
                try:
                    sku_element = await page.query_selector(selector)
                    if sku_element:
                        sku_text = await sku_element.text_content()
                        if sku_text and sku_text.strip():
                            product_details['sku'] = sku_text.strip()
                            logger.debug(f"SKU scraped using '{selector}': {product_details['sku']}")
                            break
                except Exception as e:
                    logger.debug(f"SKU selector '{selector}' failed: {str(e)}")
                    continue
            
            if not product_details['sku']:
                logger.warning(f"Failed to scrape SKU for {url} with any selector")

            # --- Stock availability with multiple detection methods ---
            stock_selectors = [
                'button#product-addtocart-button',
                'button[data-testid="add-to-cart"]',
                '.add-to-cart-button',
                'button:has-text("Add to Cart")',
                'button:has-text("Add to Bag")',
                '.product-addtocart-button'
            ]
            
            product_details['tag'] = 'Out of Stock'  # Default
            
            for selector in stock_selectors:
                try:
                    add_to_cart_button = await page.query_selector(selector)
                    if add_to_cart_button:
                        is_disabled = await add_to_cart_button.is_disabled()
                        if not is_disabled:
                            product_details['tag'] = 'In Stock'
                            logger.debug(f"Stock status: In Stock (using selector: {selector})")
                        else:
                            product_details['tag'] = 'Out of Stock'
                            logger.debug(f"Stock status: Out of Stock (button disabled, selector: {selector})")
                        break
                except Exception as e:
                    logger.debug(f"Stock selector '{selector}' failed: {str(e)}")
                    continue
            
            # Additional stock detection methods
            if product_details['tag'] == 'Out of Stock':
                # Check for out of stock indicators
                out_of_stock_indicators = [
                    'out of stock',
                    'sold out',
                    'unavailable',
                    'temporarily unavailable',
                    'backorder'
                ]
                
                try:
                    page_text = await page.text_content('body')
                    if any(indicator in page_text.lower() for indicator in out_of_stock_indicators):
                        product_details['tag'] = 'Out of Stock'
                        logger.debug("Stock status: Out of Stock (text indicators found)")
                except:
                    pass
            
            logger.debug(f"Final stock status: {product_details['tag']}")

            # --- Keywords (breadcrumbs) with multiple selectors ---
            breadcrumb_selectors = [
                'div.breadcrumbs li.item',
                '.breadcrumbs li',
                '.breadcrumb li',
                'nav[aria-label="Breadcrumb"] li',
                'ol.breadcrumb li',
                '.breadcrumb-nav li',
                'nav.breadcrumb li'
            ]
            
            product_details['keywords'] = None
            
            for selector in breadcrumb_selectors:
                try:
                    breadcrumb_elements = await page.query_selector_all(selector)
                    if breadcrumb_elements:
                        breadcrumb_texts = []
                        for elem in breadcrumb_elements:
                            text = await elem.text_content()
                            if text and text.strip():
                                breadcrumb_texts.append(text.strip())
                        
                        if breadcrumb_texts:
                            product_details['keywords'] = ' > '.join(breadcrumb_texts)
                            logger.debug(f"Keywords scraped using '{selector}': {product_details['keywords']}")
                            break
                except Exception as e:
                    logger.debug(f"Breadcrumb selector '{selector}' failed: {str(e)}")
                    continue
            
            if not product_details['keywords']:
                logger.warning(f"Failed to scrape keywords for {url} with any selector")

            # Log successful scraping with details
            success_fields = []
            if product_details['title']:
                success_fields.append('title')
            if product_details['brand']:
                success_fields.append('brand')
            if product_details['price']:
                success_fields.append('price')
            if product_details['sku']:
                success_fields.append('sku')
            if product_details['tag']:
                success_fields.append('tag')
            if product_details['keywords']:
                success_fields.append('keywords')
            
            logger.info(f"Successfully scraped product: {product_details['title'] or 'Unknown'} (Fields: {', '.join(success_fields)})")
            return product_details
            
        except Exception as e:
            logger.warning(f"Scraping attempt {attempt + 1}/{max_retries} failed for {url}: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"All scraping attempts failed for {url}: {str(e)}")
                return {'link': url, 'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'title': None, 'brand': None, 'price': None, 'sku': None, 'tag': None, 'keywords': None}
            else:
                await page.wait_for_timeout(2000)  # Wait before retry

async def main():
    """Main async function to run the scraper with comprehensive error handling"""
    browser = None
    try:
        async with async_playwright() as p:
            # Launch browser with enhanced stealth configuration for DataDome bypass
            # Try to launch with detected mode, fallback to headless if it fails
            try:
                browser = await p.firefox.launch(
                    headless=HEADLESS_MODE,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-web-security',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-hang-monitor',
                    '--disable-client-side-phishing-detection',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-logging',
                    '--disable-gpu-logging',
                    '--silent',
                    '--log-level=3'
                ]
            )
            except Exception as e:
                if not HEADLESS_MODE:
                    logger.warning(f"Failed to launch in GUI mode: {e}")
                    logger.info("Falling back to headless mode...")
                    browser = await p.firefox.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-blink-features=AutomationControlled',
                            '--disable-dev-shm-usage',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor',
                            '--disable-extensions',
                            '--disable-plugins',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-features=TranslateUI',
                            '--disable-ipc-flooding-protection',
                            '--no-first-run',
                            '--disable-default-apps',
                            '--disable-popup-blocking',
                            '--disable-prompt-on-repost',
                            '--disable-hang-monitor',
                            '--disable-client-side-phishing-detection',
                            '--disable-sync',
                            '--disable-translate',
                            '--disable-logging',
                            '--disable-gpu-logging',
                            '--silent',
                            '--log-level=3'
                        ]
                    )
                else:
                    raise
            
            user_agent = random.choice(USER_AGENTS)
            logger.info(f"Using User-Agent: {user_agent}")

            # Create context with enhanced stealth settings for DataDome bypass
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=user_agent,
                locale='en-US',
                timezone_id='America/New_York',
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0',
                    'sec-ch-ua': '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'Sec-Ch-Ua-Platform-Version': '"15.0.0"',
                    'Sec-Ch-Ua-Arch': '"x86"',
                    'Sec-Ch-Ua-Model': '""',
                    'Sec-Ch-Ua-Full-Version-List': '"Google Chrome";v="119.0.6045.105", "Chromium";v="119.0.6045.105", "Not?A_Brand";v="24.0.0.0"'
                },
                java_script_enabled=True,
                bypass_csp=True,
                ignore_https_errors=True
            )
            
            page = await context.new_page()
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            await warm_up_session(page)

            # Set up proxy if available and test it
            try:
                proxy_config_to_test = get_proxy_config()
                if proxy_config_to_test:
                    logger.info("Testing proxy connection...")
                    if test_proxy_connection():
                        logger.info("Proxy connection successful.")
                        proxy_headers = get_proxy_for_playwright()
                        if proxy_headers:
                            await page.context.set_extra_http_headers(proxy_headers)
                            logger.info("Proxy configuration applied successfully.")
                    else:
                        logger.error("Proxy connection test failed. Exiting script.")
                        sys.exit(1)
                else:
                    logger.info("No proxy configured to test.")
            except Exception as e:
                logger.warning(f"Proxy setup failed: {e}")

            # --- Loop Through Each Link in the DataFrame ---
            total_urls = len(df_link)
            successful_scrapes = 0
            failed_scrapes = 0
            consecutive_failures = 0

            logger.info(f"Starting to scrape {total_urls} products")
            
            for i, url in enumerate(df_link['link'], 1):
                try:
                    logger.info(f"Processing product {i}/{total_urls}: {url}")
                    product_details = await scrape_product_details(url, page, max_retries=3)
                    scraped_data_list.append(product_details)
                    
                    if product_details.get('blocked'):
                        logger.warning("Stopping early because the scraper was blocked.")
                        break
                    
                    if product_details['title'] is not None:
                        successful_scrapes += 1
                        consecutive_failures = 0
                    else:
                        failed_scrapes += 1
                        consecutive_failures += 1
                        
                    if consecutive_failures >= 5:
                        logger.warning("Stopping early due to 5 consecutive failed scrapes.")
                        break
                        
                    # Add random delay between requests to avoid detection
                    if i < total_urls:  # Don't delay after the last request
                        # Base delay with some variation
                        base_delay = random.uniform(8, 15)  # Increased base delay
                        logger.debug(f"Waiting {base_delay:.1f} seconds before next request...")
                        await asyncio.sleep(base_delay)
                        
                        # Occasionally add longer delays to appear more human
                        if random.random() < 0.3:  # 30% chance for extra delay
                            extra_delay = random.uniform(15, 30)
                            logger.debug(f"Adding extra human-like delay: {extra_delay:.1f} seconds")
                            await asyncio.sleep(extra_delay)
                        
                        # Simulate human behavior between requests
                        try:
                            # Random mouse movement
                            await page.mouse.move(random.randint(100, 1800), random.randint(100, 1000))
                            await page.wait_for_timeout(random.randint(500, 1500))
                            
                            # Random scroll
                            await page.evaluate(f"window.scrollTo(0, {random.randint(100, 800)})")
                            await page.wait_for_timeout(random.randint(1000, 2000))
                        except Exception as e:
                            logger.debug(f"Human behavior simulation failed: {e}")
                        
                    # Progress logging every 10 products
                    if i % 10 == 0:
                        logger.info(f"Progress: {i}/{total_urls} products processed. Success: {successful_scrapes}, Failed: {failed_scrapes}")
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {str(e)}")
                    failed_scrapes += 1
                    # Add empty record to maintain count
                    scraped_data_list.append({
                        'link': url, 
                        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
                        'title': None, 
                        'brand': None, 
                        'price': None, 
                        'sku': None, 
                        'tag': None, 
                        'keywords': None
                    })
            
            logger.info(f"Scraping completed. Total: {total_urls}, Successful: {successful_scrapes}, Failed: {failed_scrapes}")
            
    except Exception as e:
        logger.error(f"Critical error in main scraping function: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        if browser:
            try:
                await browser.close()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")

# Run the async main function with error handling
try:
    asyncio.run(main())
    logger.info("Main scraping function completed successfully")
except Exception as e:
    logger.error(f"Critical error in main execution: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Convert the list of dictionaries into a new DataFrame
try:
    results_df = pd.DataFrame(scraped_data_list)
    logger.info(f"Created DataFrame with {len(results_df)} products")
    # dropna sku
    results_df = results_df.dropna(subset=['sku'])
    logger.info(f"Removed rows with missing SKU. {len(results_df)} records remaining.")
    
    if results_df.empty:
        logger.warning("No data was scraped. Exiting.")
        sys.exit(0)
        
except Exception as e:
    logger.error(f"Failed to create DataFrame: {str(e)}")
    sys.exit(1)

# Calculate duration
end_time = time.time()
duration_in_minutes = (end_time - start_time) / 60
logger.info(f"Scraping completed in {duration_in_minutes:.2f} minutes")

# Data processing with error handling
try:
    logger.info("Starting data processing...")
    
    # price to float
    results_df = safe_data_processing(price_to_float, results_df, price_col='price', currency_marker='$')
    logger.info("Price conversion completed")
    
    # domain
    results_df = safe_data_processing(get_domain, results_df, link_col='link')
    logger.info("Domain extraction completed")
    
    # extract vol from title
    results_df = safe_data_processing(extract_volume, results_df, vol_col='title', result_col='vol')
    logger.info("Volume extraction completed")
    
except Exception as e:
    logger.error(f"Data processing failed: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Database operations with error handling
try:
    logger.info("Starting database operations...")
    
    # Prepare fixed_fields data
    df_fixed_fields = results_df[['link', 'title', 'brand', 'sku', 'vol', 'keywords', 'domain']].copy()
    logger.info(f"Prepared fixed_fields data: {len(df_fixed_fields)} records")
    
    # Upsert to fixed_fields
    safe_database_operation(upsert_df_to_mysql, df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
    logger.info("Successfully updated fixed_fields table")
    
    # Prepare ticker data
    df_ticker = results_df[['link', 'sku', 'price', 'tag', 'domain', 'date']].copy()
    logger.info(f"Prepared ticker data: {len(df_ticker)} records")
    
    # Generate keys
    df_ticker = safe_data_processing(generate_key, df_ticker, deduplication_columns=['link', 'date'], key_col='key')
    logger.info("Key generation completed")
    
    # Upsert to df_ticker
    safe_database_operation(upsert_df_to_mysql, df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
    logger.info("Successfully updated df_ticker table")
    
    # Prepare duration data
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes], 
        'date': [datetime.now()], 
        'results': [len(df_ticker)], 
        'domain': ['healthyplanetcanada.com'], 
        'type': ['item_update']
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    logger.info(f"Prepared duration data: {df_duration['result_per_minute'].iloc[0]:.2f} results per minute")
    
    # Upsert to duration
    safe_database_operation(upsert_df_to_mysql, df=df_duration, engine=db_engine, target_table='duration', key_col='date')
    logger.info("Successfully updated duration table")
    
    logger.info("All database operations completed successfully!")
    
except Exception as e:
    logger.error(f"Database operations failed: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1)

# Final summary report
logger.info("=" * 60)
logger.info("SCRAPING SUMMARY REPORT")
logger.info("=" * 60)
logger.info(f"Total records processed: {len(scraped_data_list)}")
logger.info(f"Successful scrapes: {successful_scrapes}")
logger.info(f"Failed scrapes: {failed_scrapes}")
logger.info(f"Success rate: {(successful_scrapes / len(scraped_data_list) * 100):.1f}%" if scraped_data_list else "N/A")
logger.info(f"Duration: {duration_in_minutes:.2f} minutes")
logger.info(f"Records per minute: {len(scraped_data_list) / duration_in_minutes:.2f}" if duration_in_minutes > 0 else "N/A")
logger.info("=" * 60)

# Check for blocked pages
blocked_count = sum(1 for item in scraped_data_list if item.get('blocked', False))
if blocked_count > 0:
    logger.warning(f"⚠️  {blocked_count} pages were blocked by DataDome protection")
    logger.warning("Consider using different proxy credentials or increasing delays")

logger.info("Script execution completed successfully!")
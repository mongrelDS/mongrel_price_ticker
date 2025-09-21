#!/usr/bin/env python3
"""
Healthy Planet Canada Scraper with Enhanced Proxy Support
Complete pipeline to scrape, filter, and clean URLs from Healthy Planet using multiple proxy credentials
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys
import os
from datetime import datetime

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import database functions using the same approach as original script
# Load database_config using exec
db_config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'database_config.py')
db_config_path = os.path.abspath(db_config_path)

with open(db_config_path, 'r') as f:
    db_config_code = f.read()

db_config_globals = {}
exec(db_config_code, db_config_globals)
get_database_engine = db_config_globals['get_database_engine']
get_database_credentials = db_config_globals['get_database_credentials']

# Use exec to load the upsert function
upsert_file_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'mySQL_Upsert_Function_with_Batch.py')
upsert_file_path = os.path.abspath(upsert_file_path)

# Read and execute the upsert file
with open(upsert_file_path, 'r') as f:
    upsert_code = f.read()

# Replace the import statement in the upsert code
upsert_code = upsert_code.replace(
    "from database_config import get_database_engine, get_database_credentials",
    "# database_config functions provided by parent module"
)

# Create a namespace for the upsert module with database_config available
upsert_globals = {
    'get_database_engine': get_database_engine,
    'get_database_credentials': get_database_credentials
}
exec(upsert_code, upsert_globals)
upsert_df_to_mysql = upsert_globals['upsert_df_to_mysql']

# Import enhanced proxy configuration
proxy_config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src', 'proxy_config.py')
proxy_config_path = os.path.abspath(proxy_config_path)

with open(proxy_config_path, 'r') as f:
    proxy_config_code = f.read()

proxy_config_globals = {}
exec(proxy_config_code, proxy_config_globals)
get_proxy_for_requests = proxy_config_globals['get_proxy_for_requests']
get_proxy_config = proxy_config_globals['get_proxy_config']
record_proxy_usage = proxy_config_globals['record_proxy_usage']
get_proxy_stats = proxy_config_globals['get_proxy_stats']
switch_proxy_credential = proxy_config_globals['switch_proxy_credential']

class HealthyPlanetScraper:
    """Enhanced scraper class for Healthy Planet Canada with multiple proxy support"""
    
    def __init__(self):
        """Initialize the scraper with enhanced proxy configuration"""
        self.proxy_config = get_proxy_config()
        self.session = None
        self.successful_requests = 0
        self.failed_requests = 0
        self.consecutive_failures = 0
        self.blocking_detected = False
        
    def create_session(self):
        """Create session with enhanced proxy configuration and automatic switching"""
        
        # Create session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Configure proxy using enhanced configuration
        proxy_dict = get_proxy_for_requests()
        self.session.proxies = proxy_dict
        
        # Set enhanced headers to mimic real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        })
        
        return self.session
    
    def test_proxy_connection(self):
        """Test if proxy is working and display current credential info"""
        try:
            current_cred = self.proxy_config.get_current_credential()
            print(f"🔍 Testing proxy connection with {current_cred.city}...")
            
            response = self.session.get("http://httpbin.org/ip", timeout=15)
            if response.status_code == 200 and "origin" in response.text:
                print(f"✅ Proxy working! IP: {response.text}")
                record_proxy_usage(success=True)
                return True
            else:
                print(f"❌ Proxy test failed: {response.status_code}")
                record_proxy_usage(success=False)
                return False
        except Exception as e:
            print(f"❌ Proxy test error: {e}")
            record_proxy_usage(success=False)
            return False
    
    def handle_request_error(self, url, error, max_retries=3):
        """Handle request errors with proxy switching and retry logic"""
        
        for attempt in range(max_retries):
            try:
                print(f"  -> Retry {attempt + 1}/{max_retries} for {url}")
                
                # Check if we should switch proxy
                if attempt > 0:
                    current_cred = self.proxy_config.get_current_credential()
                    print(f"  🔄 Switching from {current_cred.city} proxy...")
                    new_cred = switch_proxy_credential()
                    print(f"  ✅ Switched to {new_cred.city} proxy")
                    
                    # Update session with new proxy
                    proxy_dict = get_proxy_for_requests()
                    self.session.proxies = proxy_dict
                
                # Make the request
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    record_proxy_usage(success=True)
                    self.successful_requests += 1
                    self.consecutive_failures = 0
                    return response
                elif response.status_code in [403, 429, 503]:
                    print(f"  🚫 Blocking detected (HTTP {response.status_code})")
                    record_proxy_usage(success=False)
                    self.failed_requests += 1
                    self.consecutive_failures += 1
                    
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        return None
                else:
                    print(f"  ⚠️ HTTP {response.status_code} - attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        record_proxy_usage(success=False)
                        self.failed_requests += 1
                        self.consecutive_failures += 1
                        return None
                        
            except Exception as e:
                print(f"  -> Error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    record_proxy_usage(success=False)
                    self.failed_requests += 1
                    self.consecutive_failures += 1
                    return None
        
        return None
    
    def scrape_page_links(self, url, page_name):
        """Scrape a specific page and collect all links with enhanced error handling"""
        
        print(f"🚀 Scraping {page_name}...")
        
        all_links = []
        
        try:
            print(f"🌐 Navigating to: {url}")
            
            # Add random delay to appear human
            delay = random.uniform(2, 5)
            print(f"  ⏱️ Waiting {delay:.1f}s...")
            time.sleep(delay)
            
            # Make request with error handling
            response = self.handle_request_error(url, None)
            
            if response is None:
                print(f"❌ Failed to load {page_name} after all retries")
                return all_links
            
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Successfully loaded {page_name}!")
                
                # Check if content is readable
                if response.text.startswith('<!DOCTYPE') or response.text.startswith('<html'):
                    print("✅ Content is readable HTML")
                else:
                    print("⚠️ Content appears to be compressed or encoded")
                    if 'healthyplanet' in response.text.lower():
                        print("✅ Found 'healthyplanet' in content")
                    else:
                        print("❌ No readable content found")
                        return all_links
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all links
                links = soup.find_all('a', href=True)
                print(f"🔍 Found {len(links)} total links")
                
                # Process links
                seen_links = set()
                for link in links:
                    try:
                        href = link.get('href')
                        if href:
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                href = f"https://www.healthyplanetcanada.com{href}"
                            elif href.startswith('#'):
                                continue  # Skip anchor links
                            elif not href.startswith('http'):
                                continue  # Skip invalid links
                            
                            # Only add unique links
                            if href not in seen_links:
                                all_links.append(href)
                                seen_links.add(href)
                                
                    except Exception as e:
                        continue
                
                print(f"✅ Processed {len(all_links)} unique links from {page_name}")
                
            else:
                print(f"❌ Failed to load {page_name}: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error during scraping {page_name}: {e}")
            record_proxy_usage(success=False)
            self.failed_requests += 1
            self.consecutive_failures += 1
        
        return all_links
    
    def scrape_all_pages(self):
        """Scrape both front page and sitemap to collect all links with enhanced monitoring"""
        
        print("🚀 Scraping Healthy Planet pages with enhanced proxy...")
        
        all_links = []
        
        # URLs to scrape
        pages_to_scrape = [
            ("https://www.healthyplanetcanada.com/", "front page"),
            ("https://www.healthyplanetcanada.com/sitemap", "sitemap page")
        ]
        
        for i, (url, page_name) in enumerate(pages_to_scrape, 1):
            print(f"\n{'='*60}")
            print(f"SCRAPING: {page_name.upper()} ({i}/{len(pages_to_scrape)})")
            print(f"{'='*60}")
            
            # Display current proxy stats
            current_cred = self.proxy_config.get_current_credential()
            print(f"🌐 Using {current_cred.city} proxy (usage: {current_cred.usage_count})")
            
            page_links = self.scrape_page_links(url, page_name)
            all_links.extend(page_links)
            
            # Check for blocking
            if self.consecutive_failures >= 3:
                print("🚨 Too many consecutive failures - potential blocking detected")
                self.blocking_detected = True
                break
            
            # Add delay between pages
            if i < len(pages_to_scrape):  # Don't delay after the last page
                delay = random.uniform(3, 7)
                print(f"⏱️ Waiting {delay:.1f}s before next page...")
                time.sleep(delay)
        
        # Remove duplicates across all pages
        unique_links = list(set(all_links))
        duplicates_removed = len(all_links) - len(unique_links)
        
        print(f"\n{'='*60}")
        print("COMBINED RESULTS")
        print(f"{'='*60}")
        print(f"📊 Total links collected: {len(all_links)}")
        print(f"📊 Unique links after deduplication: {len(unique_links)}")
        print(f"📊 Duplicates removed: {duplicates_removed}")
        print(f"📊 Successful requests: {self.successful_requests}")
        print(f"📊 Failed requests: {self.failed_requests}")
        if self.successful_requests + self.failed_requests > 0:
            success_rate = self.successful_requests / (self.successful_requests + self.failed_requests) * 100
            print(f"📊 Success rate: {success_rate:.1f}%")
        
        return unique_links
    
    def create_dataframe(self, links):
        """Create DataFrame with links"""
        
        if not links:
            print("❌ No links found")
            return None
        
        print("📊 Creating DataFrame...")
        
        # Create DataFrame with just the link column
        df_links = pd.DataFrame({'link': links})
        
        return df_links
    
    def filter_internal_links(self, df_links):
        """Filter to keep only internal links"""
        
        print("🔍 Filtering to internal links only...")
        
        if df_links is None or df_links.empty:
            return None
        
        # Filter to keep only internal links (Healthy Planet domain)
        df_filtered = df_links[df_links['link'].str.contains('healthyplanetcanada.com', case=False, na=False)].copy()
        print(f"📊 After filtering internal links: {len(df_filtered)} links")
        print(f"📊 Final data: {len(df_filtered)} links with 1 column")
        
        return df_filtered
    
    def clean_url(self, url):
        """Clean up a single URL by removing unnecessary parameters and normalizing"""
        
        try:
            # Parse the URL
            parsed = urlparse(url)
            
            # Remove common tracking parameters
            tracking_params = [
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'gclid', 'fbclid', 'ref', 'source', 'campaign', 'affiliate',
                'uenc', '___store', '___from_store', '___sid', '___from',
                'SID', 'PHPSESSID', 'sessionid', 'jsessionid',
                'v', 'version', 'timestamp', 't', 'time',
                'redirect', 'return', 'next', 'continue',
                'fb_action_ids', 'fb_action_types', 'fb_source',
                'mc_cid', 'mc_eid', 'hsCtaTracking',
                'hsCtaTrackingId', 'hsCtaTrackingData'
            ]
            
            # Parse query parameters
            query_params = parse_qs(parsed.query)
            
            # Remove tracking parameters
            cleaned_params = {}
            for key, value in query_params.items():
                if key.lower() not in [param.lower() for param in tracking_params]:
                    cleaned_params[key] = value[0] if len(value) == 1 else value
            
            # Rebuild query string
            if cleaned_params:
                cleaned_query = urlencode(cleaned_params, doseq=True)
            else:
                cleaned_query = ''
            
            # Remove fragment (everything after #)
            cleaned_fragment = ''
            
            # Clean up path - remove duplicate slashes and normalize
            cleaned_path = re.sub(r'/+', '/', parsed.path)
            # Remove trailing slash unless it's the root path
            if cleaned_path.endswith('/') and len(cleaned_path) > 1:
                cleaned_path = cleaned_path.rstrip('/')
            # Special case: remove trailing slash from root path too
            elif cleaned_path == '/':
                cleaned_path = ''
            
            # Rebuild the URL
            cleaned_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                cleaned_path,
                parsed.params,
                cleaned_query,
                cleaned_fragment
            ))
            
            return cleaned_url
            
        except Exception as e:
            print(f"⚠️ Error cleaning URL {url}: {e}")
            return url
    
    def cleanup_urls(self, df_links):
        """Clean up URLs and remove duplicates"""
        
        print("🧹 Cleaning up URLs...")
        
        if df_links is None:
            return None
        
        # Clean up URLs
        df_links['link'] = df_links['link'].apply(self.clean_url)
        
        # Remove duplicates after cleaning
        original_count = len(df_links)
        df_links = df_links.drop_duplicates(subset=['link'])
        cleaned_count = len(df_links)
        duplicates_removed = original_count - cleaned_count
        
        print(f"📊 After cleaning: {cleaned_count} unique links")
        print(f"📊 Duplicates removed: {duplicates_removed}")
        
        return df_links
    
    def prepare_for_upsert(self, df_links):
        """Prepare the links DataFrame for database upsert - cat_link_list should have 1 column only"""
        
        if df_links is None or df_links.empty:
            print("❌ No links to prepare for upsert")
            return None
        
        print("📊 Preparing links for database upsert...")
        
        # cat_link_list should have only 1 column - just the links
        # Simply copy the df_links as-is for the database
        df_prepared = df_links.copy()
        
        print(f"✅ Prepared {len(df_prepared)} links for upsert")
        print(f"📋 Database columns: {list(df_prepared.columns)} (should be 1 column only)")
        print(f"📋 Original df_link still has: {list(df_links.columns)}")
        
        return df_prepared
    
    def get_links(self):
        """Main method: Get cleaned Healthy Planet links as DataFrame with enhanced proxy support"""
        
        print("🚀 Healthy Planet Scraper with Enhanced Proxy")
        print("=" * 60)
        
        # Display initial proxy stats
        print("\n📊 Initial Proxy Configuration:")
        stats = get_proxy_stats()
        for cred_info in stats['credentials']:
            print(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
        
        # Create session
        self.create_session()
        
        # Test proxy connection
        if not self.test_proxy_connection():
            print("⚠️ Proxy test failed, but continuing...")
        
        # Step 1: Scrape all pages (front page + sitemap)
        print("\n" + "="*60)
        print("STEP 1: SCRAPING ALL PAGES")
        print("="*60)
        all_links = self.scrape_all_pages()
        
        if not all_links:
            print("❌ No links found. Scraping stopped.")
            return None
        
        # Step 2: Create DataFrame
        print("\n" + "="*60)
        print("STEP 2: CREATING DATAFRAME")
        print("="*60)
        df_links = self.create_dataframe(all_links)
        
        # Step 3: Filter internal links
        print("\n" + "="*60)
        print("STEP 3: FILTERING INTERNAL LINKS")
        print("="*60)
        df_internal = self.filter_internal_links(df_links)
        
        # Step 4: Clean URLs
        print("\n" + "="*60)
        print("STEP 4: CLEANING URLS")
        print("="*60)
        df_cleaned = self.cleanup_urls(df_internal)
        
        # Display final proxy stats
        print("\n📊 Final Proxy Statistics:")
        final_stats = get_proxy_stats()
        for cred_info in final_stats['credentials']:
            print(f"  {cred_info['city']}: usage={cred_info['usage_count']}, blocked={cred_info['is_blocked']}")
        
        # Final summary
        print("\n" + "="*60)
        print("SCRAPING COMPLETE - FINAL SUMMARY")
        print("="*60)
        
        if df_cleaned is not None:
            print(f"✅ Successfully processed {len(df_cleaned)} clean, unique URLs!")
            print(f"📊 DataFrame contains {len(df_cleaned)} URLs ready for next steps")
            print(f"📊 Total requests: {self.successful_requests + self.failed_requests}")
            print(f"📊 Success rate: {self.successful_requests/(self.successful_requests + self.failed_requests)*100:.1f}%")
            return df_cleaned
        else:
            print("❌ Scraping failed")
            return None

def get_healthyplanet_links():
    """Convenience function to get Healthy Planet links with enhanced proxy"""
    scraper = HealthyPlanetScraper()
    return scraper.get_links()

def main():
    """Main execution function with enhanced proxy support"""
    scraper = HealthyPlanetScraper()
    df_links = scraper.get_links()
    
    if df_links is not None:
        print(f"\n🎉 Scraping completed!")
        print(f"Shape: {df_links.shape}")
        print(f"Columns: {list(df_links.columns)}")
        print(f"\nSample links:")
        for i, url in enumerate(df_links['link'].head(5), 1):
            print(f"  {i}. {url}")
        
        # Prepare data for upsert (df_links remains unchanged with 1 column)
        print("\n" + "="*60)
        print("UPSERTING TO DATABASE")
        print("="*60)
        
        try:
            # Get database engine
            engine = get_database_engine()
            print("✅ Database engine created successfully")
            
            # Prepare data for upsert (creates separate DataFrame for database)
            df_prepared = scraper.prepare_for_upsert(df_links)
            
            if df_prepared is not None:
                # cat_link_list should have only 1 column (link)
                # Use 'link' as the key column since it's the only column
                upsert_df_to_mysql(
                    df=df_prepared,
                    engine=engine,
                    target_table='cat_link_list',
                    key_col='link'
                )
                
                print("\n" + "="*60)
                print("UPSERT COMPLETE - FINAL SUMMARY")
                print("="*60)
                print(f"✅ Successfully upserted {len(df_prepared)} Healthy Planet links!")
                print(f"📊 Table: cat_link_list")
                print(f"📊 Source: healthyplanet")
                print(f"📊 Status: active")
                print(f"📊 Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print("❌ Failed to prepare data for upsert")
                
        except Exception as e:
            print(f"❌ Error during upsert: {e}")
        
        return df_links
    else:
        print("\n❌ Scraping failed")
        return None

if __name__ == "__main__":
    result = main()

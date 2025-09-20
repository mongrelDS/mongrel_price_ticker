#!/usr/bin/env python3
"""
Healthy Planet Canada Scraper
Complete pipeline to scrape, filter, and clean URLs from Healthy Planet
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

# Add the src directory to the path so we can import our modules (same as Well.ca)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import database functions (same as Well.ca)
from mySQL_Upsert_Function import upsert_df_to_mysql
from database_config import get_database_engine

class HealthyPlanetScraper:
    """Main scraper class for Healthy Planet Canada"""
    
    def __init__(self):
        """Initialize the scraper with proxy configuration"""
        self.proxy_config = {
            'host': 'residential.ipb.cloud',
            'port': '7777',
            'username': 'customer-mnft29185901-city-toronto-sessid-oUcO-sesstime-30',
            'password': 'xyspgptxmm_J9v'
        }
        self.session = None
        
    def create_session(self):
        """Create session with working IPBurger proxy"""
        
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
        
        # Configure proxy
        proxy_url = f"http://{self.proxy_config['username']}:{self.proxy_config['password']}@{self.proxy_config['host']}:{self.proxy_config['port']}"
        self.session.proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        # Set headers to mimic real browser
        self.session.headers.update({
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
        
        return self.session
    
    def test_proxy_connection(self):
        """Test if proxy is working"""
        try:
            print("🔍 Testing proxy connection...")
            response = self.session.get("http://httpbin.org/ip", timeout=15)
            if response.status_code == 200 and "origin" in response.text:
                print(f"✅ Proxy working! IP: {response.text}")
                return True
            else:
                print(f"❌ Proxy test failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Proxy test error: {e}")
            return False
    
    def scrape_page_links(self, url, page_name):
        """Scrape a specific page and collect all links"""
        
        print(f"🚀 Scraping {page_name}...")
        
        all_links = []
        
        try:
            print(f"🌐 Navigating to: {url}")
            
            # Add random delay to appear human
            time.sleep(random.uniform(2, 5))
            
            # Make request
            response = self.session.get(url, timeout=30)
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
                        return []
                
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
        
        return all_links
    
    def scrape_all_pages(self):
        """Scrape both front page and sitemap to collect all links"""
        
        print("🚀 Scraping Healthy Planet pages...")
        
        all_links = []
        
        # URLs to scrape
        pages_to_scrape = [
            ("https://www.healthyplanetcanada.com/", "front page"),
            ("https://www.healthyplanetcanada.com/sitemap", "sitemap page")
        ]
        
        for url, page_name in pages_to_scrape:
            print(f"\n{'='*60}")
            print(f"SCRAPING: {page_name.upper()}")
            print(f"{'='*60}")
            
            page_links = self.scrape_page_links(url, page_name)
            all_links.extend(page_links)
            
            # Add delay between pages
            if page_name != "sitemap page":  # Don't delay after the last page
                time.sleep(random.uniform(3, 7))
        
        # Remove duplicates across all pages
        unique_links = list(set(all_links))
        duplicates_removed = len(all_links) - len(unique_links)
        
        print(f"\n{'='*60}")
        print("COMBINED RESULTS")
        print(f"{'='*60}")
        print(f"📊 Total links collected: {len(all_links)}")
        print(f"📊 Unique links after deduplication: {len(unique_links)}")
        print(f"📊 Duplicates removed: {duplicates_removed}")
        
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
        """Main method: Get cleaned Healthy Planet links as DataFrame"""
        
        print("🚀 Healthy Planet Scraper")
        print("=" * 60)
        
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
        
        # Final summary
        print("\n" + "="*60)
        print("SCRAPING COMPLETE - FINAL SUMMARY")
        print("="*60)
        
        if df_cleaned is not None:
            print(f"✅ Successfully processed {len(df_cleaned)} clean, unique URLs!")
            print(f"📊 DataFrame contains {len(df_cleaned)} URLs ready for next steps")
            return df_cleaned
        else:
            print("❌ Scraping failed")
            return None

def get_healthyplanet_links():
    """Convenience function to get Healthy Planet links"""
    scraper = HealthyPlanetScraper()
    return scraper.get_links()

def main():
    """Main execution function"""
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

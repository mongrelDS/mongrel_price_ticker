# @title Initialize

import sys
import asyncio
import json
import re
import random
import pandas as pd
import numpy as np

from playwright.async_api import async_playwright
from datetime import datetime
from urllib.parse import urljoin
from urllib.parse import urljoin, urlparse, urlunparse

import os
from urllib.parse import urljoin, urlparse
import sys
import time
import nest_asyncio

# Add project root to Python path for imports
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add missing imports
from src.get_domain import get_domain
from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql, read_mysql_to_df
from src.database_config import get_database_engine
from src.proxy_config import get_proxy_for_playwright, record_proxy_usage, get_proxy_stats


# @title Network Crawl

# --- Configuration ---
# The initial list of URLs to start crawling from (will be loaded from database)
INITIAL_URLS = [
    'https://www.healthyplanetcanada.com'  # Fallback URL
]

# The target domain. Links outside this domain will be ignored.
TARGET_DOMAIN = "www.healthyplanetcanada.com"

# Maximum number of pages to crawl. Helps to prevent infinitely long crawls.
MAX_PAGES_TO_CRAWL = 100

# Number of concurrent workers. Reduced to 3 to avoid being flagged.
CONCURRENT_WORKERS = 2

# Early stopping configuration
MAX_CRAWL_TIME_MINUTES = 30  # Maximum crawl time in minutes
CONVERGENCE_THRESHOLD = 5    # Stop if no new links found for N consecutive iterations
DUPLICATE_RATIO_THRESHOLD = 0.8  # Stop if duplicate ratio exceeds this threshold
MIN_PAGES_FOR_EARLY_STOP = 20    # Minimum pages to crawl before early stopping kicks in
MAX_PROXY_BLOCKED_COUNT = 3  # Stop if this many proxy credentials are blocked
PROXY_BLOCKED_TIMEOUT_MINUTES = 5  # Maximum time to continue after proxy is blocked

# JS script to inject to help bypass bot detection by hiding the 'webdriver' flag
JS_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"

async def get_all_links(page, url):
    """
    Navigates to a URL and extracts all href links with proxy error handling.
    """
    links = set()
    try:
        # Use a less strict wait condition ('load') and a longer timeout.
        await page.goto(url, wait_until='load', timeout=120000)
        # Add a fixed delay to allow JavaScript to execute.
        await page.wait_for_timeout(5000)

        # Extract all href attributes from anchor tags
        hrefs = await page.eval_on_selector_all('a', 'elements => elements.map(el => el.href)')

        for href in hrefs:
            # Clean and resolve the link to be an absolute URL
            absolute_link = urljoin(url, href)
            parsed = urlparse(absolute_link)

            # URL Normalization : Rebuild the URL without query strings or fragments to avoid duplicates
            normalized_link = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, '', ''))

            # Ensure the link is a valid, crawlable http/https link within the target domain
            if (parsed.scheme in ['http', 'https'] and
                parsed.netloc == TARGET_DOMAIN):
                links.add(normalized_link)

        # Record successful proxy usage
        record_proxy_usage(success=True)

    except Exception as e:
        print(f"Could not process page {url}. Error: {e}")
        # Record failed proxy usage and potentially switch credentials
        record_proxy_usage(success=False)

    return links


async def worker(queue, browser, crawled_urls, all_found_links, lock, early_stop_flags):
    """
    A worker that continuously fetches URLs from the queue and processes them.
    """
    while True:
        try:
            # Check for early stopping conditions
            if early_stop_flags['should_stop']:
                break
            
            # Check if all proxies are blocked
            try:
                proxy_stats = get_proxy_stats()
                if proxy_stats['blocked_credentials'] >= len(proxy_stats['credentials']):
                    print("🚫 All proxy credentials are blocked, stopping worker")
                    early_stop_flags['should_stop'] = True
                    early_stop_flags['stop_reason'] = 'all_proxies_blocked'
                    break
            except Exception as e:
                print(f"⚠️ Error checking proxy stats in worker: {e}")
                
            # Get a URL from the queue.
            current_url = await queue.get()

            # Use a lock to check and add to crawled_urls atomically
            async with lock:
                # Skip if URL has been crawled or if we have hit the page limit
                if current_url in crawled_urls or len(crawled_urls) >= MAX_PAGES_TO_CRAWL:
                    queue.task_done()
                    continue
                # Add to the set of pages being processed
                crawled_urls.add(current_url)
                print(f"Crawling ({len(crawled_urls)}/{MAX_PAGES_TO_CRAWL}): {current_url}")

            # Create a new page with a common user agent to appear more human.
            page = await browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

            # Add the anti-bot detection script before navigating.
            await page.add_init_script(JS_SCRIPT)

            # Get all links from the current page
            new_links = await get_all_links(page, current_url)
            await page.close()

            # Use a lock to safely update the shared sets
            async with lock:
                # Find links that have not been seen before
                genuinely_new_links = new_links - all_found_links
                
                # Update early stopping counters
                if len(genuinely_new_links) == 0:
                    early_stop_flags['no_new_links_count'] += 1
                else:
                    early_stop_flags['no_new_links_count'] = 0
                
                # Calculate duplicate ratio
                total_links_processed = len(crawled_urls)
                if total_links_processed > 0:
                    duplicate_ratio = (total_links_processed - len(genuinely_new_links)) / total_links_processed
                    early_stop_flags['duplicate_ratio'] = duplicate_ratio

                # Add these new links to the master list and the queue
                for link in genuinely_new_links:
                    all_found_links.add(link)
                    await queue.put(link)

            # Signal that the task from the queue is done
            queue.task_done()

        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Worker encountered an error: {e}")
            # Still mark task as done to prevent the queue from stalling
            if not queue.empty():
                queue.task_done()
            continue

async def monitor_early_stopping(early_stop_flags, start_time, crawled_urls):
    """
    Monitor early stopping conditions and set flags accordingly.
    """
    while not early_stop_flags['should_stop']:
        await asyncio.sleep(5)  # Check every 5 seconds
        
        current_time = time.time()
        elapsed_minutes = (current_time - start_time) / 60
        
        # Time-based early stopping
        if elapsed_minutes >= MAX_CRAWL_TIME_MINUTES:
            print(f"⏰ Early stopping: Maximum crawl time ({MAX_CRAWL_TIME_MINUTES} minutes) reached")
            early_stop_flags['should_stop'] = True
            early_stop_flags['stop_reason'] = 'timeout'
            break
        
        # Convergence-based early stopping
        if (len(crawled_urls) >= MIN_PAGES_FOR_EARLY_STOP and 
            early_stop_flags['no_new_links_count'] >= CONVERGENCE_THRESHOLD):
            print(f"🔄 Early stopping: No new links found for {CONVERGENCE_THRESHOLD} consecutive iterations")
            early_stop_flags['should_stop'] = True
            early_stop_flags['stop_reason'] = 'convergence'
            break
        
        # Duplicate ratio early stopping
        if (len(crawled_urls) >= MIN_PAGES_FOR_EARLY_STOP and 
            early_stop_flags['duplicate_ratio'] >= DUPLICATE_RATIO_THRESHOLD):
            print(f"🔄 Early stopping: Duplicate ratio ({early_stop_flags['duplicate_ratio']:.2f}) exceeds threshold ({DUPLICATE_RATIO_THRESHOLD})")
            early_stop_flags['should_stop'] = True
            early_stop_flags['stop_reason'] = 'duplicate_ratio'
            break
        
        # Proxy blocking early stopping
        try:
            proxy_stats = get_proxy_stats()
            blocked_count = proxy_stats['blocked_credentials']
            
            # Check if we have blocked proxies
            if blocked_count > 0:
                # Record when proxy blocking started
                if early_stop_flags['proxy_blocked_start_time'] is None:
                    early_stop_flags['proxy_blocked_start_time'] = current_time
                    print(f"🚫 Proxy blocking detected: {blocked_count} credentials blocked")
                
                # Check if we've exceeded the proxy blocked timeout
                proxy_blocked_elapsed = (current_time - early_stop_flags['proxy_blocked_start_time']) / 60
                if proxy_blocked_elapsed >= PROXY_BLOCKED_TIMEOUT_MINUTES:
                    print(f"⏰ Early stopping: Proxy blocked for {proxy_blocked_elapsed:.1f} minutes (timeout: {PROXY_BLOCKED_TIMEOUT_MINUTES} minutes)")
                    early_stop_flags['should_stop'] = True
                    early_stop_flags['stop_reason'] = 'proxy_blocked_timeout'
                    break
                
                # Also check if we've hit the blocked count threshold
                if blocked_count >= MAX_PROXY_BLOCKED_COUNT:
                    print(f"🚫 Early stopping: {blocked_count} proxy credentials are blocked (threshold: {MAX_PROXY_BLOCKED_COUNT})")
                    early_stop_flags['should_stop'] = True
                    early_stop_flags['stop_reason'] = 'proxy_blocked'
                    break
            else:
                # Reset proxy blocked timer if no proxies are blocked
                early_stop_flags['proxy_blocked_start_time'] = None
                
        except Exception as e:
            print(f"⚠️ Error checking proxy stats: {e}")
        
        # Print progress every 30 seconds
        if int(elapsed_minutes * 2) % 1 == 0:  # Every 30 seconds
            try:
                proxy_stats = get_proxy_stats()
                blocked_count = proxy_stats['blocked_credentials']
                
                # Calculate proxy blocked time if applicable
                proxy_blocked_time_str = ""
                if early_stop_flags['proxy_blocked_start_time'] is not None:
                    proxy_blocked_elapsed = (current_time - early_stop_flags['proxy_blocked_start_time']) / 60
                    proxy_blocked_time_str = f", proxy blocked: {proxy_blocked_elapsed:.1f}min"
                
                print(f"📊 Progress: {len(crawled_urls)} pages crawled, {elapsed_minutes:.1f} minutes elapsed, "
                      f"duplicate ratio: {early_stop_flags['duplicate_ratio']:.2f}, "
                      f"no new links count: {early_stop_flags['no_new_links_count']}, "
                      f"blocked proxies: {blocked_count}{proxy_blocked_time_str}")
            except Exception as e:
                print(f"📊 Progress: {len(crawled_urls)} pages crawled, {elapsed_minutes:.1f} minutes elapsed, "
                      f"duplicate ratio: {early_stop_flags['duplicate_ratio']:.2f}, "
                      f"no new links count: {early_stop_flags['no_new_links_count']}")

async def main(initial_urls=None):
    """
    Main function to orchestrate the parallel web crawling process.
    """
    if initial_urls is None:
        initial_urls = INITIAL_URLS
    
    queue = asyncio.Queue()
    lock = asyncio.Lock()

    # Using sets for efficient add/check operations
    crawled_urls = set()
    all_found_links = set(initial_urls)
    
    # Initialize early stopping flags
    start_time = time.time()
    early_stop_flags = {
        'should_stop': False,
        'stop_reason': None,
        'no_new_links_count': 0,
        'duplicate_ratio': 0.0,
        'proxy_blocked_start_time': None  # Track when proxy blocking started
    }

    # Add all initial URLs to the queue
    for url in initial_urls:
        await queue.put(url)

    # Print early stopping configuration
    print(f"🚀 Starting crawler with early stopping enabled:")
    print(f"   • Max pages: {MAX_PAGES_TO_CRAWL}")
    print(f"   • Max time: {MAX_CRAWL_TIME_MINUTES} minutes")
    print(f"   • Convergence threshold: {CONVERGENCE_THRESHOLD} consecutive iterations with no new links")
    print(f"   • Duplicate ratio threshold: {DUPLICATE_RATIO_THRESHOLD}")
    print(f"   • Min pages before early stop: {MIN_PAGES_FOR_EARLY_STOP}")
    print(f"   • Max blocked proxies: {MAX_PROXY_BLOCKED_COUNT}")
    print(f"   • Proxy blocked timeout: {PROXY_BLOCKED_TIMEOUT_MINUTES} minutes")
    print()

    async with async_playwright() as p:
        # Get proxy configuration for Playwright
        proxy_config = get_proxy_for_playwright()
        print(f"🌐 Using proxy: {proxy_config['server']} (City: {proxy_config.get('username', 'Unknown').split('-city-')[1].split('-sessid-')[0] if '-city-' in proxy_config.get('username', '') else 'Unknown'})")
        
        # Launch browser with proxy configuration
        browser = await p.chromium.launch(proxy=proxy_config)

        # Create and start the worker tasks
        tasks = []
        for _ in range(CONCURRENT_WORKERS):
            task = asyncio.create_task(worker(queue, browser, crawled_urls, all_found_links, lock, early_stop_flags))
            tasks.append(task)
        
        # Start the early stopping monitor
        monitor_task = asyncio.create_task(monitor_early_stopping(early_stop_flags, start_time, crawled_urls))

        # Wait for the queue to be fully processed or early stopping
        try:
            # Check if we should stop before waiting
            while not queue.empty() and not early_stop_flags['should_stop']:
                await asyncio.sleep(1)  # Check every second
            await queue.join()
        except Exception as e:
            print(f"Queue processing interrupted: {e}")

        # Cancel the worker tasks
        for task in tasks:
            task.cancel()
        
        # Cancel the monitor task
        monitor_task.cancel()

        # Wait for all tasks to be cancelled
        await asyncio.gather(*tasks, monitor_task, return_exceptions=True)

        await browser.close()
        
        # Display stopping reason
        if early_stop_flags['stop_reason']:
            print(f"\n🛑 Crawl stopped early due to: {early_stop_flags['stop_reason']}")
        else:
            print("\n✅ Crawl completed normally!")
        
        elapsed_time = (time.time() - start_time) / 60
        print(f"⏱️ Total crawl time: {elapsed_time:.1f} minutes")

        # Display proxy usage statistics
        print("\n📊 Proxy Usage Statistics:")
        print("-" * 40)
        proxy_stats = get_proxy_stats()
        for i, cred_info in enumerate(proxy_stats['credentials']):
            status = "🚫 BLOCKED" if cred_info['is_blocked'] else "✅ ACTIVE"
            print(f"  {i+1}. {cred_info['city']}: {cred_info['usage_count']} uses {status}")
        print(f"  Active Credential: {proxy_stats['active_credential'] + 1}")
        print(f"  Blocked Credentials: {proxy_stats['blocked_credentials']}/{proxy_stats['total_credentials']}")
        
        # Show proxy blocking reason if applicable
        if early_stop_flags['stop_reason'] in ['proxy_blocked', 'all_proxies_blocked', 'proxy_blocked_timeout']:
            print(f"\n🚫 Crawl stopped due to proxy issues:")
            if early_stop_flags['stop_reason'] == 'proxy_blocked':
                print(f"   • {proxy_stats['blocked_credentials']} out of {proxy_stats['total_credentials']} proxy credentials are blocked")
                print(f"   • Threshold: {MAX_PROXY_BLOCKED_COUNT} blocked credentials")
            elif early_stop_flags['stop_reason'] == 'all_proxies_blocked':
                print(f"   • All {proxy_stats['total_credentials']} proxy credentials are blocked")
                print(f"   • No working proxies available")
            elif early_stop_flags['stop_reason'] == 'proxy_blocked_timeout':
                print(f"   • Proxy blocked for {PROXY_BLOCKED_TIMEOUT_MINUTES} minutes")
                print(f"   • Timeout threshold exceeded")
                if early_stop_flags['proxy_blocked_start_time'] is not None:
                    actual_blocked_time = (time.time() - early_stop_flags['proxy_blocked_start_time']) / 60
                    print(f"   • Actual blocked time: {actual_blocked_time:.1f} minutes")

        # Create the final DataFrame
        df_link = pd.DataFrame(list(all_found_links), columns=['link'])

        print(f"\nTotal unique links found: {len(df_link)}")
        print("DataFrame `df_link` created successfully.")

        # Display the first few rows of the DataFrame
        print("\n--- DataFrame Head ---")
        print(df_link.head())

        return df_link


def run_healthyplanet_crawler():
    """
    Main function to run the Healthy Planet crawler.
    Crawls the website, processes links, and stores them in the database.
    """
    # Apply nest_asyncio
    nest_asyncio.apply()
    
    # Initialize database engine
    db_engine = get_database_engine()
    
    # Load initial URLs from database
    try:
        print("📊 Loading initial URLs from database...")
        df_initial_urls = read_mysql_to_df(engine=db_engine, table_name='cat_link_list')
        if df_initial_urls is not None and len(df_initial_urls) > 0:
            # Sample URLs for crawling
            df_initial_urls = df_initial_urls.sample(min(3, len(df_initial_urls)))
            initial_urls = df_initial_urls['link'].tolist()
            print(f"✅ Loaded {len(initial_urls)} URLs from database")
        else:
            print("⚠️ No URLs found in database, using fallback URL")
            initial_urls = INITIAL_URLS
    except Exception as e:
        print(f"⚠️ Error loading URLs from database: {e}")
        print("Using fallback URL")
        initial_urls = INITIAL_URLS
    
    # Run the crawler with loaded URLs
    df_link = asyncio.run(main(initial_urls))

    # Process the links
    # df_link link rstrip "/"
    df_link['link'] = df_link['link'].str.rstrip('/')
    # df_link['slash_count'] =  count the instances of "/"  in link
    df_link['slash_count'] = df_link['link'].str.count('/')

    # df_link_item = df_link where slash_count is <4 and [link] str includes html
    # Updated to match actual URL structure: https://www.healthyplanetcanada.com/products/item.html
    df_link_item = df_link[(df_link['slash_count'] < 4) &  (df_link['link'].str.contains('html', na=False))]

    # drop column slash_count
    df_link_item = df_link_item.drop(columns=['slash_count'])

    # get domain from link
    df_link_item = get_domain(df_link_item, link_col='link')
    # drop duplicates based on link
    df_link_item = df_link_item.drop_duplicates(subset='link', keep='first')
    # upsert
    upsert_df_to_mysql(df=df_link_item, engine=db_engine, target_table='df_product_url', key_col='link')

    # Category links: either more than 3 slashes OR doesn't contain 'html'
    df_catlink = df_link[(df_link['slash_count'] > 3) |  (~df_link['link'].str.contains('html', na=False))]
    df_catlink = df_catlink.drop(columns=['slash_count'])
    # drop rows where link str includes "blog"
    df_catlink = df_catlink[~df_catlink['link'].str.contains('/blog/', na=False)]
    df_catlink = df_catlink.drop_duplicates(subset='link', keep='first')
    # upsert
    upsert_df_to_mysql(df=df_catlink, engine=db_engine, target_table='cat_link_list', key_col='link')
    
    return df_link, df_link_item, df_catlink


# Run the crawler if this script is executed directly
if __name__ == "__main__":
    df_link, df_link_item, df_catlink = run_healthyplanet_crawler()
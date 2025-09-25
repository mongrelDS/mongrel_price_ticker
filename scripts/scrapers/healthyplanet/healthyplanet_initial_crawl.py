#!/usr/bin/env python3
"""
Healthy Planet Brand Links Scraper

This script scrapes all brand links from the Healthy Planet website.
It inspects JSON results when available (responses or embedded scripts),
falls back to HTML when needed, and upserts the links to MySQL.
Additionally, it records duration metrics.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from urllib.parse import urljoin
import re
import json

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Import database configuration and upsert function
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql

# Configuration
DOMAIN = 'healthyplanetcanada.com'
BASE_URL = 'https://www.healthyplanetcanada.com/'
BRANDS_PATH = 'brands'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def validate_url(url):
    """Validate that a URL is properly formatted and from the expected domain."""
    if not url or not isinstance(url, str):
        return False
    return url.startswith('http') and DOMAIN in url


def _extract_links_from_json_like(obj) -> list:
    """Recursively walk JSON-like data and collect brand-like URLs."""
    found = []
    try:
        if isinstance(obj, dict):
            for k, v in obj.items():
                # Common URL fields
                if isinstance(v, str) and re.search(r"/(brand|brands)/", v, flags=re.IGNORECASE):
                    found.append(v)
                else:
                    found.extend(_extract_links_from_json_like(v))
        elif isinstance(obj, list):
            for item in obj:
                found.extend(_extract_links_from_json_like(item))
        elif isinstance(obj, str):
            if re.search(r"/(brand|brands)/", obj, flags=re.IGNORECASE):
                found.append(obj)
    except Exception:
        pass
    return found


def _try_fetch_json_endpoints(session: requests.Session, url: str) -> list:
    """Try a few JSON variations of the page and extract brand links if any."""
    candidates = [
        url,
        url + ("&view=json" if ("?" in url) else "?view=json"),
        url + ("&format=json" if ("?" in url) else "?format=json"),
        url.rstrip('/') + '.json',
    ]

    links = []
    for ep in candidates:
        try:
            r = session.get(ep, headers={**HEADERS, 'Accept': 'application/json'}, timeout=30)
            # Only proceed if body looks like JSON
            data = None
            try:
                data = r.json()
            except Exception:
                continue
            if data is not None:
                links.extend(_extract_links_from_json_like(data))
        except Exception:
            continue
    return links


def _extract_links_from_embedded_scripts(soup) -> list:
    """Scan <script> tags for JSON blobs that include brand URLs."""
    links = []
    try:
        # application/json or ld+json blocks
        for script in soup.find_all('script'):
            t = (script.get('type') or '').lower()
            if t in ('application/json', 'application/ld+json'):
                try:
                    data = json.loads(script.text.strip())
                    links.extend(_extract_links_from_json_like(data))
                except Exception:
                    # If not valid single JSON, try to salvage JSON objects/arrays
                    try:
                        candidates = re.findall(r"\{[\s\S]*?\}|\[[\s\S]*?\]", script.text)
                        for c in candidates:
                            try:
                                data = json.loads(c)
                                links.extend(_extract_links_from_json_like(data))
                            except Exception:
                                continue
                    except Exception:
                        continue
            else:
                # Generic scripts: search for URL-like strings
                try:
                    url_candidates = re.findall(r"https?://[^\"'\s>]+|/[^\"'\s>]+", script.text)
                    for u in url_candidates:
                        if re.search(r"/(brand|brands)/", u, flags=re.IGNORECASE):
                            links.append(u)
                except Exception:
                    continue
    except Exception:
        pass
    return links


def scrape_brand_links(target_url, max_retries=3, retry_delay=1):
    """
    Scrape brand links from the Healthy Planet website.
    
    Args:
        target_url (str): The URL to scrape
        max_retries (int): Maximum number of retry attempts
        retry_delay (int): Delay between retries in seconds
    
    Returns:
        list: List of brand URLs
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to scrape brand links from: {target_url} (attempt {attempt + 1}/{max_retries})")
            
            # Session for reuse
            session = requests.Session()

            # 0) Magento-first strategy: GraphQL aggregations
            def fetch_brand_options_via_graphql(sess) -> dict:
                options_by_code = {}
                try:
                    graphql_url = urljoin(BASE_URL, 'graphql')
                    payload = {
                        "query": "{ products(search: \"\", pageSize: 1) { aggregations { attribute_code options { label value } } } }"
                    }
                    r = sess.post(
                        graphql_url,
                        headers={**HEADERS, 'Content-Type': 'application/json', 'Accept': 'application/json'},
                        json=payload,
                        timeout=30,
                    )
                    data = r.json() if r is not None else None
                    aggs = (((data or {}).get('data') or {}).get('products') or {}).get('aggregations') or []
                    for agg in aggs:
                        code = (agg or {}).get('attribute_code')
                        if not code or code.lower() not in ('brand', 'manufacturer'):
                            continue
                        opts = (agg or {}).get('options') or []
                        clean_opts = []
                        for o in opts:
                            val = (o or {}).get('value')
                            lab = (o or {}).get('label')
                            if val in (None, "", "0"):
                                continue
                            clean_opts.append({'value': str(val), 'label': str(lab) if lab is not None else None})
                        if clean_opts:
                            options_by_code[code] = clean_opts
                except Exception:
                    pass
                return options_by_code

            def fetch_brand_options_via_rest(sess) -> dict:
                options_by_code = {}
                try:
                    for code in ('brand', 'manufacturer'):
                        rest_url = urljoin(BASE_URL, f'rest/default/V1/products/attributes/{code}/options')
                        try:
                            r = sess.get(rest_url, headers={**HEADERS, 'Accept': 'application/json'}, timeout=30)
                            arr = r.json() if r is not None else None
                            if isinstance(arr, list) and arr:
                                clean_opts = []
                                for o in arr:
                                    val = (o or {}).get('value')
                                    lab = (o or {}).get('label')
                                    if val in (None, "", "0"):
                                        continue
                                    clean_opts.append({'value': str(val), 'label': str(lab) if lab is not None else None})
                                if clean_opts:
                                    options_by_code[code] = clean_opts
                        except Exception:
                            continue
                except Exception:
                    pass
                return options_by_code

            def build_search_urls_from_options(options_by_code: dict) -> list:
                links_local = []
                try:
                    for code, opts in (options_by_code or {}).items():
                        for o in opts:
                            v = (o or {}).get('value')
                            if not v:
                                continue
                            # Catalog search with attribute filter is stable and indexable
                            url = urljoin(BASE_URL, f'catalogsearch/result/?q=&{code}={v}')
                            links_local.append(url)
                except Exception:
                    pass
                return links_local

            # GraphQL first
            gql_opts = fetch_brand_options_via_graphql(session)
            if gql_opts:
                gql_links = build_search_urls_from_options(gql_opts)
                gql_links = [u for u in gql_links if validate_url(u)]
                if gql_links:
                    # Deduplicate preserving order and return immediately
                    seen_g = set(); unique_g = []
                    for u in gql_links:
                        if u not in seen_g:
                            seen_g.add(u); unique_g.append(u)
                    logger.info(f"Found {len(unique_g)} brand links via GraphQL aggregations")
                    return unique_g

            # REST fallback
            rest_opts = fetch_brand_options_via_rest(session)
            if rest_opts:
                rest_links = build_search_urls_from_options(rest_opts)
                rest_links = [u for u in rest_links if validate_url(u)]
                if rest_links:
                    seen_r = set(); unique_r = []
                    for u in rest_links:
                        if u not in seen_r:
                            seen_r.add(u); unique_r.append(u)
                    logger.info(f"Found {len(unique_r)} brand links via REST attribute options")
                    return unique_r

            # 1) Try JSON endpoints first as requested
            json_links = _try_fetch_json_endpoints(session, target_url)
            if json_links:
                logger.info(f"Found {len(json_links)} candidate links from JSON endpoints")

            # 2) Fetch the page content
            response = session.get(target_url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 3) Inspect embedded scripts for JSON that may contain brand URLs
            script_links = _extract_links_from_embedded_scripts(soup)
            if script_links:
                logger.info(f"Found {len(script_links)} candidate links from embedded scripts")
            
            # 4) Fallback: Look for anchor tags that look like brand links
            selectors = [
                'a[href*="/brands/"]',
                'a[href*="/brand/"]',
                'ul li a',
            ]
            link_elements = []
            for selector in selectors:
                found = soup.select(selector)
                if found:
                    link_elements.extend(found)
            
            all_links = []
            # From JSON endpoints
            for raw in json_links:
                try:
                    full_url = urljoin(BASE_URL, str(raw))
                    if validate_url(full_url):
                        all_links.append(full_url)
                except Exception:
                    continue
            # From script JSON
            for raw in script_links:
                try:
                    full_url = urljoin(BASE_URL, str(raw))
                    if validate_url(full_url):
                        all_links.append(full_url)
                except Exception:
                    continue
            # From anchors
            for element in link_elements:
                try:
                    href = element.get('href')
                    if not href:
                        continue
                    full_url = urljoin(BASE_URL, href)
                    if validate_url(full_url):
                        all_links.append(full_url)
                except Exception:
                    continue
            
            # Deduplicate while preserving order
            seen = set()
            unique_links = []
            for link in all_links:
                if link not in seen:
                    seen.add(link)
                    unique_links.append(link)
            
            logger.info(f"Successfully scraped {len(unique_links)} brand links")
            return unique_links
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise
        except Exception as e:
            logger.error(f"Unexpected error occurred (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise
    
    return []


def upsert_to_mysql(df_brand, engine, table_name='brand_link_list'):
    """
    Upsert df_brand to MySQL table.
    """
    try:
        upsert_df_to_mysql(
            df=df_brand,
            engine=engine,
            target_table=table_name,
            key_col='brand_url',
            chunksize=1000
        )
        logger.info(f"Successfully upserted {len(df_brand)} brand links to {table_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert data to MySQL table {table_name}: {e}")
        return False


def main():
    """Main function to orchestrate the scraping process."""
    parser = argparse.ArgumentParser(description='Scrape brand links from healthyplanetcanada.com and upsert to MySQL')
    parser.add_argument('-t', '--table', default='brand_link_list',
                       help='MySQL table name (default: brand_link_list)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    target_url = urljoin(BASE_URL, BRANDS_PATH)
    engine = get_database_engine()
    start_ts = time.time()
    
    try:
        # Scrape the brand links
        brand_links = scrape_brand_links(target_url)
        
        if not brand_links:
            logger.error("No brand links were found. Exiting.")
            sys.exit(1)
        
        # Build df_brand
        df_brand = pd.DataFrame(brand_links, columns=['brand_url'])
        logger.info(f"Found {len(df_brand)} brand links")
        logger.info("-" * 50)
        logger.info("Sample of the data:")
        logger.info(f"\n{df_brand.head().to_string(index=False)}")
        logger.info("-" * 50)
        
        # Upsert df_brand
        if not upsert_to_mysql(df_brand, engine, args.table):
            logger.error("❌ Failed to upsert df_brand to MySQL table")
            sys.exit(1)
        
        # Duration metrics
        end_ts = time.time()
        duration_in_minutes = (end_ts - start_ts) / 60.0
        df_duration = pd.DataFrame({
            'duration_min': [duration_in_minutes],
            'date': [datetime.now()],
            'results': [len(df_brand)],
            'domain': [DOMAIN],
            'type': ['brand_crawl'],
        })
        df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
        upsert_df_to_mysql(df=df_duration, engine=engine, target_table='duration', key_col='date')
        
        logger.info("✅ Scraping and database upserts completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
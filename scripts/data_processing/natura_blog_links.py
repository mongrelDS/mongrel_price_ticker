# @title Source and Target links

# --- Required Imports ---
import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from urllib.parse import urljoin, urlparse, urlunparse
import nest_asyncio
import argparse
import sys
sys.path.append('/home/mongreldatalab/mongrel_price_ticker')
from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from sqlalchemy import inspect, text

# Apply nest_asyncio to allow running asyncio in environments like Jupyter
nest_asyncio.apply()


# --- Configuration ---
# The target domain. Links outside this domain will be ignored.
TARGET_DOMAIN = "naturamarket.ca"

# Maximum number of pages to crawl. Helps to prevent infinitely long crawls.
MAX_PAGES_TO_CRAWL = 200

# Number of concurrent workers.
CONCURRENT_WORKERS = 6

# JS script to inject to help bypass bot detection by hiding the 'webdriver' flag
JS_SCRIPT = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"


async def get_all_links(page, url: str) -> set[str]:
    """
    Navigates to a URL and extracts all valid, normalized href links
    within the TARGET_DOMAIN.
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

            # URL Normalization: Rebuild the URL without query strings or fragments
            normalized_link = urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

            # Ensure the link is a valid, crawlable http/https link within the target domain (allow optional 'www.')
            target_hosts = {TARGET_DOMAIN, f"www.{TARGET_DOMAIN}"}
            if (parsed.scheme in ['http', 'https'] and parsed.netloc in target_hosts):
                links.add(normalized_link)

    except Exception as e:
        print(f"Could not process page {url}. Error: {e}")

    return links


async def worker(queue, browser, crawled_urls, all_found_links, link_pairs, lock):
    """
    A worker that continuously fetches URLs from the queue, crawls them,
    and records the link relationships.
    """
    while True:
        try:
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
            found_links_on_page = await get_all_links(page, current_url)
            await page.close()

            # Use a lock to safely update the shared data structures
            async with lock:
                for target_link in found_links_on_page:
                    # Record the relationship: current_url -> target_link
                    link_pairs.append((current_url, target_link))

                    # If this target_link has never been seen before, add it to the
                    # master set and the queue to be crawled later.
                    if target_link not in all_found_links:
                        all_found_links.add(target_link)
                        await queue.put(target_link)

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


async def main(df_initial: pd.DataFrame, headless: bool = True, no_sandbox: bool = False) -> pd.DataFrame:
    """
    Main function to orchestrate the parallel web crawling process.
    """
    queue = asyncio.Queue()
    lock = asyncio.Lock()

    # Get initial URLs from the input DataFrame, assuming a 'url' column
    initial_urls = df_initial['url'].tolist()

    # --- Shared data structures ---
    # Stores all (source_url, target_url) pairs found
    link_pairs = []
    # Set of URLs that have already been crawled or are in the queue
    crawled_urls = set()
    # Set of all unique URLs ever discovered
    all_found_links = set(initial_urls)

    # Add all initial URLs to the queue
    for url in initial_urls:
        await queue.put(url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--no-sandbox"] if no_sandbox else [])

        # Create and start the worker tasks
        tasks = []
        for _ in range(CONCURRENT_WORKERS):
            task = asyncio.create_task(worker(queue, browser, crawled_urls, all_found_links, link_pairs, lock))
            tasks.append(task)

        # Wait for the queue to be fully processed
        await queue.join()

        # Cancel the worker tasks, as they are now idle
        for task in tasks:
            task.cancel()

        # Wait for all tasks to be cancelled
        await asyncio.gather(*tasks, return_exceptions=True)

        await browser.close()
        print("\nCrawl finished!")

        # --- Create the final DataFrame as requested ---
        df_result = pd.DataFrame(link_pairs, columns=['source_url', 'target_url'])
        # Optional: Remove duplicate source-target pairs
        df_result.drop_duplicates(inplace=True)

        print(f"Total source-target link pairs found: {len(df_result)}")
        print("DataFrame `df_crawl_results` created successfully.")

        # Display the first few rows of the DataFrame
        print("\n--- DataFrame Head ---")
        print(df_result.head())

        return df_result

# --- CLI Entrypoint ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl Natura Market blog links within domain and output source→target pairs.")
    parser.add_argument("--start-url", action="append", dest="start_urls", help="Seed start URL (can specify multiple)")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES_TO_CRAWL, help="Max pages to crawl")
    parser.add_argument("--workers", type=int, default=CONCURRENT_WORKERS, help="Number of concurrent workers")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser in headless mode (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run browser with UI")
    parser.add_argument("--no-sandbox", action="store_true", help="Pass --no-sandbox to Chromium")
    # No CSV output per requirements; storing to SQL instead

    args = parser.parse_args()

    # Defaults
    start_urls = args.start_urls or ["https://www.naturamarket.ca/blog"]

    # Update runtime configuration
    MAX_PAGES = args.max_pages
    WORKERS = args.workers
    MAX_PAGES_TO_CRAWL = MAX_PAGES
    CONCURRENT_WORKERS = WORKERS

    # Build initial links DataFrame
    df_initial_links = pd.DataFrame({"url": start_urls})

    # Execute crawl
    df_crawl_results = asyncio.run(main(df_initial_links, headless=args.headless, no_sandbox=bool(args.no_sandbox)))

    # Normalize and deduplicate
    df_crawl_results['source_url'] = df_crawl_results['source_url'].str.rstrip('/')
    df_crawl_results['target_url'] = df_crawl_results['target_url'].fillna('').astype(str).str.rstrip('/')
    df_crawl_results['source_url'] = df_crawl_results['source_url'].str.replace('www.', '', regex=False)
    df_crawl_results['target_url'] = df_crawl_results['target_url'].str.replace('www.', '', regex=False)
    df_crawl_results.drop_duplicates(inplace=True)

    # Add slash_count: number of '/' characters in target_url
    df_crawl_results['slash_count'] = df_crawl_results['target_url'].str.count('/').astype(int)

    # select rows where slash_count is  3
    df_crawl_results = df_crawl_results[df_crawl_results['slash_count'] == 3]



    # Upsert to SQL: natura_link_pairs
    print("\n💾 Upserting link pairs to MySQL table 'natura_link_pairs'...")
    db_engine = get_database_engine()

    from src.generate_key import generate_key
    df_crawl_results = generate_key(df_crawl_results, ['source_url', 'target_url'], key_col='key')
    upsert_df_to_mysql(
            df=df_crawl_results[['key', 'source_url', 'target_url', 'slash_count']],
            engine=db_engine,
            target_table='natura_link_pairs',
            key_col='key',
            chunksize=5000
        )

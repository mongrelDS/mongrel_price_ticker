# --- 
import asyncio
import pandas as pd
import os
import sys

from datetime import datetime, timedelta
from playwright.async_api import async_playwright, expect
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Import required functions via package
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from generate_key import generate_key
from cleanup_column_names import clean_column_names

# --- Functions now imported from src directory ---

# --- Date Helper Function ---
def get_date_strings():
    """Generates formatted date strings for the URL."""
    today = datetime.now() 
    three_days_ago = today - timedelta(days=5)
    end_date = today.strftime('%m/%d/%Y').replace('/', '%2F')
    start_date = three_days_ago.strftime('%m/%d/%Y').replace('/', '%2F')
    return start_date, end_date

# --- Main Scraping and Database Logic ---
async def main(db_engine):
    all_line_items = []
    timestamp_0 = datetime.now()
    start_date, end_date = get_date_strings()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Set to True for production
        page = await browser.new_page()

        # --- LOGIN ---
        print("Logging in...")
        await page.goto("https://app.shiphero.com/account/login")
        
        # Get credentials from environment variables
        shiphero_email = os.getenv('SHIPHERO_EMAIL')
        shiphero_password = os.getenv('SHIPHERO_PASSWORD')
        if not shiphero_email or not shiphero_password:
            raise ValueError("Missing SHIPHERO_EMAIL or SHIPHERO_PASSWORD environment variables")
        
        await page.locator('[name="username"]').fill(shiphero_email)
        await page.get_by_role("button", name="Continue").click()
        await page.locator('[name="password"]').fill(shiphero_password)
        await page.get_by_role("button", name="Continue").click()
        await expect(page).to_have_title("ShipHero - Simplify How You Pick and Pack Your Orders - ShipHero")
        print("Login Successful!")

        # --- NAVIGATE AND FILTER ---
        target_url = f"https://app.shiphero.com/dashboard/line-items?start_date={start_date}&end_date={end_date}"
        await page.goto(target_url)
        await page.locator('select[name="fulfillment_status"]').select_option(label="All")
        await page.wait_for_load_state("networkidle")
        print("Navigated and filters set.")
        
        # --- SCRAPE DATA ---

        for i in range(99): # Scrape up to n pages
            print(f"Scraping page {i + 1}...")

            # Wait for the main table content to be ready
            await page.locator("#line_items tbody").wait_for(timeout=30000)
            rows = await page.locator("#line_items tbody tr").all()

            for row in rows:
                cells = await row.locator("td").all_text_contents()
                all_line_items.append({
                    "Order Date": cells[1], "SKU": cells[3], "Name": cells[4],
                    "Quantity": cells[5], "Price": cells[8], "Subtotal": cells[9],
                    "Order Number": cells[12], "Customer Email": cells[15]
                })

            # Wait for any potential overlays to disappear before interacting further
            try:
                await page.locator(".modal-backdrop").wait_for(state="hidden", timeout=10000)
            except:
                pass  # Continue if no modal backdrop
            
            try:
                await page.locator("#line_items_processing").wait_for(state="hidden", timeout=10000)
            except:
                pass  # Continue if no processing overlay

            # Check if the 'Next' button is disabled (last page)
            next_button = page.locator("#line_items_next")
            if 'disabled' in (await next_button.get_attribute('class') or ''):
                print("Last page reached. Ending scrape.")
                break # Exit the loop if the button is disabled

            # If not disabled, try to click to go to the next page with retry logic
            try:
                await next_button.click(timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                print(f"Error clicking next button on page {i + 1}: {e}")
                print("Stopping scrape due to navigation error.")
                break

        await browser.close()

    # --- INTEGRATION: Convert to DataFrame and Upsert ---
    if all_line_items:
        print(f"\nScraping complete. Found {len(all_line_items)} total items.")
        
        # 1. Convert list of dicts to pandas DataFrame
        shiphero_line_items_df = pd.DataFrame(all_line_items)
        shiphero_line_items_df['Order Date'] = pd.to_datetime(shiphero_line_items_df['Order Date'], format='mixed')

        # 2. Generate the unique key for deduplication
        print("Generating unique keys...")
        shiphero_line_items_df = generate_key(
            shiphero_line_items_df,
            # Date is not an ideal deduplication column because it is not format-controlled in the source data
            deduplication_columns=['SKU', 'Quantity', 'Subtotal', 'Order Number'],
            key_col="key"
        )
        
        #drop duplicates based on key
        shiphero_line_items_df = shiphero_line_items_df.drop_duplicates(subset='key', keep='first')
        
        shiphero_line_items_df = clean_column_names(shiphero_line_items_df)

        # 3. Call your upsert function
        upsert_df_to_mysql(
            df=shiphero_line_items_df,
            engine=db_engine,
            target_table='natura_line_items',
            key_col='key'
        )
    else:
        print("\nNo data was scraped.")

    # --- Duration tracking and upsert ---
    try:
        timestamp_1 = datetime.now()
        duration = timestamp_1 - timestamp_0
        duration_in_minutes = duration.total_seconds() / 60

        results_count = len(all_line_items)
        df_duration = pd.DataFrame({
            'duration_min': [duration_in_minutes],
            'date': [datetime.now()],
            'results': [results_count],
            'result_per_minute': [results_count / duration_in_minutes if duration_in_minutes > 0 else 0.0],
            'domain': ['shiphero'],
            'type': ['line_items']
        })

        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        print("Successfully upserted duration data to 'duration' table")
    except Exception as e:
        print(f"Failed to upsert duration data: {e}")

# --- Script Execution ---
if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Database Credentials & Connection (using environment variables)
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_port = os.getenv('DB_PORT', '3306')
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD')

    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required (no default in repo)")

    # Create the SQLAlchemy Engine
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(connection_string, poolclass=NullPool)

    # Run the main async function
    asyncio.run(main(engine))
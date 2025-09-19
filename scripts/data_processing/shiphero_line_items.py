# --- 
import asyncio
import pandas as pd
import hashlib
import json
import time
import random

from datetime import datetime, timedelta
from playwright.async_api import async_playwright, expect
from sqlalchemy import create_engine, text, inspect, types
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool

# --- HashKey Generation Function ---
def generate_key(df, deduplication_columns, key_col="key"):
    """
    Generates a unique 13-character key for each row in a DataFrame based on
    a set of deduplication columns.
    """
    concatenated_strings = df[deduplication_columns].astype(str).agg(''.join, axis=1)
    hashed_keys = concatenated_strings.apply(
        lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest()
    )
    df[key_col] = hashed_keys.str[:13]
    return df

# --- MySQL Upsert Functions ---
def upsert_df_to_mysql(df: pd.DataFrame, engine, target_table: str, key_col: str, custom_dtypes: dict = None, max_retries: int = 3):
    """
    Upserts a pandas DataFrame into a MySQL table with an automatic retry mechanism.
    """
    if df.empty:
        print("Input DataFrame is empty. Nothing to do.")
        return

    df_processed = df.copy()
    for col in ['tags', 'overlay_badges']:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)

    last_exception = None
    for attempt in range(max_retries):
        try:
            _perform_upsert(df_processed, engine, target_table, key_col, custom_dtypes)
            return
        except OperationalError as e:
            last_exception = e
            print(f"\n--- WARNING: Connection Error on attempt {attempt + 1}/{max_retries} ---")
            print(f"Error: {e}")
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("All retry attempts failed. Please check the network or database server status.")
                raise last_exception

def _perform_upsert(df: pd.DataFrame, engine, target_table: str, key_col: str, custom_dtypes: dict):
    """Helper function containing the core upsert logic."""
    temp_table = f"temp_{target_table}"
    with engine.connect() as conn:
        print(f"--- Starting upsert process for table '{target_table}' ---")
        inspector = inspect(engine)
        if not inspector.has_table(target_table):
            print(f"Table '{target_table}' does not exist. Creating it now...")
            inferred_dtypes = {
                col: types.TEXT for col, dtype in df.dtypes.items() if dtype == 'object'
            }
            inferred_dtypes[key_col] = types.VARCHAR(255)
            if custom_dtypes:
                inferred_dtypes.update(custom_dtypes)
            df.head(0).to_sql(target_table, conn, if_exists='replace', index=False, dtype=inferred_dtypes)
            conn.execute(text(f'ALTER TABLE `{target_table}` ADD PRIMARY KEY (`{key_col}`);'))
            conn.commit()
            print(f"Table '{target_table}' created successfully.")
        else:
            print(f"Table '{target_table}' already exists.")
        
        print(f"Uploading {len(df)} rows to temporary table '{temp_table}'...")
        df.to_sql(temp_table, conn, if_exists='replace', index=False)

        cols = df.columns.tolist()
        update_cols = [f"`{col}` = VALUES(`{col}`)" for col in cols if col != key_col]
        
        upsert_query = text(f"""
            INSERT INTO `{target_table}` ({', '.join([f'`{c}`' for c in cols])})
            SELECT {', '.join([f'`{c}`' for c in cols])} FROM `{temp_table}`
            ON DUPLICATE KEY UPDATE {', '.join(update_cols)};
        """)
        
        print("Performing UPSERT operation...")
        result = conn.execute(upsert_query)
        conn.commit()
        print(f"Upsert to '{target_table}' completed successfully! Rows affected: {result.rowcount}")
        
        conn.execute(text(f"DROP TABLE IF EXISTS `{temp_table}`;"))
        conn.commit()

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
    start_date, end_date = get_date_strings()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Set to True for production
        page = await browser.new_page()

        # --- LOGIN ---
        print("Logging in...")
        await page.goto("https://app.shiphero.com/account/login")
        
        # Get credentials from environment variables
        shiphero_email = os.getenv('SHIPHERO_EMAIL', 'shipheronatura@gmail.com')
        shiphero_password = os.getenv('SHIPHERO_PASSWORD', 'WQG4SjHzeq9e65a')
        
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

            # NEW: Wait for any potential overlays to disappear before interacting further
            # This directly solves the "intercepts pointer events" error.
            await page.locator(".modal-backdrop").wait_for(state="hidden", timeout=15000)

            # Check if the 'Next' button is disabled (last page)
            next_button = page.locator("#line_items_next")
            if 'disabled' in (await next_button.get_attribute('class') or ''):
                print("Last page reached. Ending scrape.")
                break # Exit the loop if the button is disabled

            # If not disabled, click to go to the next page
            await next_button.click()
            await page.wait_for_load_state("networkidle")

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

        # 3. Call your upsert function
        upsert_df_to_mysql(
            df=shiphero_line_items_df,
            engine=db_engine,
            target_table='shiphero_line_items',
            key_col='key'
        )
    else:
        print("\nNo data was scraped.")

# --- Script Execution ---
if __name__ == "__main__":
    # Database Credentials & Connection (using environment variables)
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD', 'taan2#IbizaI')

    if not db_password:
        raise ValueError("Database password is not set. Please configure it.")

    # Create the SQLAlchemy Engine
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
    engine = create_engine(connection_string, poolclass=NullPool)

    # Run the main async function
    asyncio.run(main(engine))
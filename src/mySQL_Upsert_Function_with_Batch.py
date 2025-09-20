#@title mySQL Upsert Function (with Batching)
import pandas as pd
from sqlalchemy import create_engine, text, inspect, types
import time
import math # Added for ceiling division
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool
import json
from database_config import get_database_engine, get_database_credentials

# --- MODIFIED FUNCTION ---
def upsert_df_to_mysql(
    df: pd.DataFrame,
    engine,
    target_table: str,
    key_col: str,
    custom_dtypes: dict = None,
    max_retries: int = 3,
    chunksize: int = 5000  # New parameter to control batch size
):
    """
    Upserts a pandas DataFrame into a MySQL table using batch processing
    to handle large datasets efficiently. Includes an automatic retry mechanism.

    Args:
        df (pd.DataFrame): The DataFrame to upsert.
        engine: An active SQLAlchemy engine instance.
        target_table (str): The name of the target table.
        key_col (str): The column name for the PRIMARY KEY.
        custom_dtypes (dict, optional): Map column names to specific SQLAlchemy types.
        max_retries (int, optional): The maximum number of times to retry on a connection error.
        chunksize (int, optional): The number of rows in each batch to be processed.
    """
    if df.empty:
        print("Input DataFrame is empty. Nothing to do.")
        return

    # Process columns with list data into JSON strings first
    df_processed = df.copy()
    for col in ['tags', 'overlay_badges']:
        if col in df_processed.columns:
            df_processed[col] = df_processed[col].apply(
                lambda x: json.dumps(x) if isinstance(x, list) else x
            )

    temp_table = f"temp_{target_table}"
    last_exception = None

    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                print(f"--- Starting upsert process for table '{target_table}' ---")

                # Step 1: Create the target table if it doesn't exist (done only once)
                inspector = inspect(engine)
                if not inspector.has_table(target_table):
                    print(f"Table '{target_table}' does not exist. Creating it now...")
                    inferred_dtypes = {
                        col: types.TEXT for col, dtype in df.dtypes.items()
                        if dtype == 'object' or col in ['tags', 'overlay_badges']
                    }
                    inferred_dtypes[key_col] = types.VARCHAR(255)
                    if custom_dtypes:
                        inferred_dtypes.update(custom_dtypes)

                    df_processed.head(0).to_sql(target_table, conn, if_exists='replace', index=False, dtype=inferred_dtypes)
                    conn.execute(text(f'ALTER TABLE `{target_table}` ADD PRIMARY KEY (`{key_col}`);'))
                    conn.commit()
                    print(f"Table '{target_table}' created successfully.")
                else:
                    print(f"Table '{target_table}' already exists.")

                # Step 2: Prepare the UPSERT query structure
                cols = df_processed.columns.tolist()
                update_cols = [f"`{col}` = VALUES(`{col}`)" for col in cols if col != key_col]
                
                if not update_cols:
                    upsert_query_str = f"""
                        INSERT IGNORE INTO `{target_table}` ({', '.join([f'`{c}`' for c in cols])})
                        SELECT {', '.join([f'`{c}`' for c in cols])} FROM `{temp_table}`;
                    """
                else:
                    upsert_query_str = f"""
                        INSERT INTO `{target_table}` ({', '.join([f'`{c}`' for c in cols])})
                        SELECT {', '.join([f'`{c}`' for c in cols])} FROM `{temp_table}`
                        ON DUPLICATE KEY UPDATE {', '.join(update_cols)};
                    """
                upsert_query = text(upsert_query_str)


                # Step 3: Process the DataFrame in batches
                num_chunks = math.ceil(len(df_processed) / chunksize)
                print(f"Total rows: {len(df_processed)}. Batch size: {chunksize}. Number of batches: {num_chunks}.")

                for i, start in enumerate(range(0, len(df_processed), chunksize)):
                    end = start + chunksize
                    batch_df = df_processed.iloc[start:end]
                    
                    print(f"  -> Processing batch {i + 1}/{num_chunks} ({len(batch_df)} rows)...")

                    # Upload current batch to the temporary table (overwriting it each time)
                    batch_df.to_sql(temp_table, conn, if_exists='replace', index=False)

                    # Perform the UPSERT from the temp table to the target table
                    conn.execute(upsert_query)
                    conn.commit()

                # Step 4: Clean up the temporary table
                print("All batches processed. Cleaning up...")
                conn.execute(text(f"DROP TABLE IF EXISTS `{temp_table}`;"))
                conn.commit()
                print(f"--- Upsert to '{target_table}' completed successfully! ---")
                return # Exit after successful completion

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

# --- Your existing read function (no changes needed) ---
def read_mysql_to_df(engine, table_name: str, max_retries: int = 3) -> pd.DataFrame | None:
    """
    Reads an entire MySQL table into a pandas DataFrame with a retry mechanism.
    """
    last_exception = None
    for attempt in range(max_retries):
        try:
            print(f"--- Attempting to read table '{table_name}' ---")
            df = pd.read_sql_table(table_name, engine)
            # Convert JSON strings back to lists after reading
            for col in ['tags', 'overlay_badges']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) else x)
            print("Read successful!")
            return df
        except OperationalError as e:
            last_exception = e
            print(f"\n--- WARNING: Connection Error on attempt {attempt + 1}/{max_retries} ---")
            print(f"Error: {e}")
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"All retry attempts to read table '{table_name}' failed.")
                return None

# --- HOW TO USE ---
if __name__ == '__main__':
    # --- Get database credentials from environment ---
    credentials = get_database_credentials()
    
    # --- Create engine using the configuration module ---
    db_engine = get_database_engine()
    
    print("Database connection configured successfully!")
    print(f"Connected to: {credentials['host']}/{credentials['name']}")

    # --- Example Usage ---
    # Create a large sample DataFrame for demonstration
    # In your real use case, this would be your actual large dataset
    # num_rows = 50000
    # data = {
    #     'id': [f'product_{i}' for i in range(num_rows)],
    #     'price': [i * 1.5 for i in range(num_rows)],
    #     'category': [f'Category {i % 10}' for i in range(num_rows)],
    #     'tags': [['sale', 'new'] if i % 2 == 0 else ['popular'] for i in range(num_rows)]
    # }
    # large_df = pd.DataFrame(data)

    # # Call the function with the new batching logic
    # # You can adjust the chunksize based on your server's capacity
    # upsert_df_to_mysql(
    #     df=large_df,
    #     engine=db_engine,
    #     target_table='products_example',
    #     key_col='id',
    #     chunksize=10000  # Example: using a chunksize of 10,000 rows
    # )
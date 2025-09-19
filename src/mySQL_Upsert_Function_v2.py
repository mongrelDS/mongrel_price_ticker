#@title mySQL Upsert Function (Environment Variables Version)

import pandas as pd
from sqlalchemy import create_engine, text, inspect, types
import time
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool
import json
from database_config import get_database_engine, get_database_credentials

def upsert_df_to_mysql(df: pd.DataFrame, engine, target_table: str, key_col: str, custom_dtypes: dict = None, max_retries: int = 3):
    """
    Upserts a pandas DataFrame into a MySQL table with an automatic retry mechanism.

    Args:
        df (pd.DataFrame): The DataFrame to upsert.
        engine: An active SQLAlchemy engine instance.
        target_table (str): The name of the target table.
        key_col (str): The column name for the PRIMARY KEY.
        custom_dtypes (dict, optional): Map column names to specific SQLAlchemy types.
        max_retries (int, optional): The maximum number of times to retry on a connection error.
    """
    if df.empty:
        print("Input DataFrame is empty. Nothing to do.")
        return

    # Convert list columns to JSON strings
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
            # Ensure 'tags' and 'overlay_badges' are created as TEXT or JSON type if available
            inferred_dtypes = {
                col: types.TEXT
                for col, dtype in df.dtypes.items()
                if dtype == 'object' or col in ['tags', 'overlay_badges'] # Treat list columns as TEXT for creation
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
        print(f"Uploading data to temporary table '{temp_table}'...")
        df.to_sql(temp_table, conn, if_exists='replace', index=False) # Upload the processed df

        cols = df.columns.tolist()
        update_cols = [f"`{col}` = VALUES(`{col}`)" for col in cols if col != key_col]
        if not update_cols:
             upsert_query = text(f"""
                INSERT IGNORE INTO `{target_table}` ({', '.join([f'`{c}`' for c in cols])})
                SELECT {', '.join([f'`{c}`' for c in cols])} FROM `{temp_table}`;
            """)
        else:
            upsert_query = text(f"""
                INSERT INTO `{target_table}` ({', '.join([f'`{c}`' for c in cols])})
                SELECT {', '.join([f'`{c}`' for c in cols])} FROM `{temp_table}`
                ON DUPLICATE KEY UPDATE {', '.join(update_cols)};
            """)
        print("Performing UPSERT operation...")
        conn.execute(upsert_query)
        conn.commit()
        conn.execute(text(f"DROP TABLE IF EXISTS `{temp_table}`;"))
        conn.commit()
        print(f"Upsert to '{target_table}' completed successfully!")


def read_mysql_to_df(engine, table_name: str, max_retries: int = 3) -> pd.DataFrame | None:
    """
    Reads an entire MySQL table into a pandas DataFrame with a retry mechanism.

    Args:
        engine: An active SQLAlchemy engine instance.
        table_name (str): The name of the table to read.
        max_retries (int, optional): Max number of times to retry on connection error.

    Returns:
        pd.DataFrame: A DataFrame containing the table's data, or None if the
                      operation fails after all retries.
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

def create_database_engine():
    """Create a configured database engine using environment variables."""
    from database_config import get_database_engine
    return get_database_engine()

if __name__ == '__main__':
    # Get database credentials from environment
    credentials = get_database_credentials()
    
    # Create engine using the new configuration
    db_engine = create_database_engine()
    
    print("Database connection configured successfully!")
    print(f"Connected to: {credentials['host']}/{credentials['name']}")


#!/usr/bin/env python3
"""
ShipHero to SQL Inventory Line Items Script
Imports inventory line items data from Google Drive and upserts to MySQL database.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from datetime import datetime

# Add src directory to path
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')

# Import required functions
from google_drive_csv_import import import_csv_from_drive
from cleanup_column_names import clean_column_names
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from generate_key import generate_key

def main():
    """Main function to process inventory line items data from Google Drive to MySQL"""
    start_time = datetime.now()
    results_count = 0
    db_engine = None
    # Load environment variables
    load_dotenv()
    
    # Database connection setup
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required (no default in repo)")
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    try:
        # Create database engine
        connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
        db_engine = create_engine(connection_string)
        
        print("✅ Database connection established")
        
        # Import data from Google Drive
        print("📥 Importing inventory line items data from Google Drive...")
        inventory_line_items = import_csv_from_drive(
            starts_with=["inventory", "Shiphero_inventory_line_items"],
            google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
        )
        
        if inventory_line_items is None:
            print("❌ Failed to import data from Google Drive")
            return False
        
        print(f"✅ Successfully imported {len(inventory_line_items)} rows")
        
        # Clean column names
        inventory_line_items = clean_column_names(inventory_line_items)
        print("✅ Column names cleaned")
        
        # Display data info
        print("\n📊 Data Information:")
        inventory_line_items.info()
        
        # Convert date column to datetime
        print("📅 Converting date column to datetime...")
        inventory_line_items['date'] = pd.to_datetime(inventory_line_items['date'])
        print(f"✅ Date column converted. Sample dates: {inventory_line_items['date'].head().tolist()}")
        
        # Generate unique key for deduplication
        print("🔑 Generating unique keys for deduplication...")
        inventory_line_items = generate_key(
            inventory_line_items, 
            deduplication_columns=['sku', 'date', 'previous_on_hand', 'updated_on_hand'], 
            key_col='key'
        )
        print("✅ Unique keys generated")
        
        # Drop duplicates based on key
        original_rows = len(inventory_line_items)
        inventory_line_items = inventory_line_items.drop_duplicates(subset=['key'])
        removed_duplicates = original_rows - len(inventory_line_items)
        print(f"✅ Removed {removed_duplicates} duplicate rows based on key")
        
        # Upsert to MySQL database
        print("💾 Upserting data to MySQL database...")
        upsert_df_to_mysql(
            df=inventory_line_items,
            engine=db_engine,
            target_table='natura_inventory_line_items',
            key_col='key'
        )
        
        results_count = len(inventory_line_items)
        print("✅ Successfully processed and stored inventory line items data")
        print(f"Final data shape: {inventory_line_items.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False
    finally:
        # Duration upsert to 'duration' table
        try:
            end_time = datetime.now()
            duration_min = (end_time - start_time).total_seconds() / 60
            if db_engine is not None:
                df_duration = pd.DataFrame({
                    'duration_min': [duration_min],
                    'date': [datetime.now()],
                    'results': [results_count],
                    'result_per_minute': [results_count / duration_min if duration_min > 0 else 0.0],
                    'domain': ['shiphero'],
                    'type': ['inventory_line_items']
                })
                upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
                print("✅ Upserted duration record to 'duration' table")
            else:
                print("⚠️ Skipped duration upsert (no DB engine)")
        except Exception as _e:
            print(f"⚠️ Failed to upsert duration data: {_e}")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
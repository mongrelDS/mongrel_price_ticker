
#!/usr/bin/env python3
"""
ShipHero to SQL Product Table Script
Imports product data from Google Drive and upserts to MySQL database.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Ensure project root and src are on sys.path for reliable imports under cron
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR = os.path.join(PROJECT_ROOT, 'src')
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import required functions from src package
from src.google_drive_csv_import import import_csv_from_drive
from src.cleanup_column_names import clean_column_names
from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql

def main():
    """Main function to process product data from Google Drive to MySQL"""
    
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
        print("📥 Importing product data from Google Drive...")
        product_table = import_csv_from_drive(
            starts_with=["product_table", "ALL_Products"],
            google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
        )
        
        if product_table is None or len(product_table) == 0:
            print("⚠️ No product_table CSV rows found on Drive; skipping upsert.")
            return True
        
        print(f"✅ Successfully imported {len(product_table)} rows")
        
        # Clean column names
        product_table = clean_column_names(product_table)
        print("✅ Column names cleaned")
        
        # Drop duplicate rows based on [sku, barcode]
        original_rows = len(product_table)
        product_table = product_table.drop_duplicates(subset=['sku', 'barcode'])
        removed_duplicates = original_rows - len(product_table)
        print(f"✅ Removed {removed_duplicates} duplicate rows")
        
        # Select required columns
        required_columns = ['name', 'on_hand', 'available', 'sku', 'barcode', 'value', 'price', 'product_note', 'tags']
        missing_columns = [col for col in required_columns if col not in product_table.columns]
        
        if missing_columns:
            print(f"⚠️ Missing required columns: {missing_columns}")
            print(f"Available columns: {list(product_table.columns)}")
            # Use available columns that match the required ones
            available_required = [col for col in required_columns if col in product_table.columns]
            product_table = product_table[available_required]
        else:
            product_table = product_table[required_columns]
        
        print(f"✅ Selected {len(product_table.columns)} columns for processing")
        
        # Upsert to MySQL database
        print("💾 Upserting data to MySQL database...")
        upsert_df_to_mysql(
            df=product_table,
            engine=db_engine,
            target_table='natura_product_table',
            key_col='sku'
        )
        
        print("✅ Successfully processed and stored product data")
        print(f"Final data shape: {product_table.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
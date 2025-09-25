
#!/usr/bin/env python3
"""
ShipHero to SQL Product Table Script
Imports product data from Google Drive and upserts to MySQL database.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Import required functions via package
from src.google_drive_csv_import import import_csv_from_drive
from src.cleanup_column_names import clean_column_names
from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from src.generate_key import generate_key

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
        line_items_table = import_csv_from_drive(
            starts_with=["line_items_table"],
            google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
        )
        
        if line_items_table is None:
            print("❌ Failed to import data from Google Drive")
            return False
        
        print(f"✅ Successfully imported {len(line_items_table)} rows")
        
        # Clean column names
        line_items_table = clean_column_names(line_items_table)
        print("✅ Column names cleaned")
        
        # Drop duplicate rows based on [sku, quantity, subtotal, order_number]
        original_rows = len(line_items_table)
        line_items_table = line_items_table.drop_duplicates(subset=['sku',  'quantity' ,'subtotal', 'order_number'])
        removed_duplicates = original_rows - len(line_items_table)
        print(f"✅ Removed {removed_duplicates} duplicate rows")
        # generate key for deduplication
        line_items_table = generate_key(
            line_items_table,
            deduplication_columns=['sku', 'quantity', 'subtotal', 'order_number'],
            key_col='key'
        )
        print("✅ Unique keys generated")
        # Select required columns
        required_columns = ['order_date', 'sku', 'name', 'quantity', 'price', 'subtotal', 'order_number', 'customer_email','key']
        missing_columns = [col for col in required_columns if col not in line_items_table.columns]
        
        if missing_columns:
            print(f"⚠️ Missing required columns: {missing_columns}")
            print(f"Available columns: {list(line_items_table.columns)}")
            # Use available columns that match the required ones
            available_required = [col for col in required_columns if col in line_items_table.columns]
            line_items_table = line_items_table[available_required]
        else:
            line_items_table = line_items_table[required_columns]
        
        print(f"✅ Selected {len(line_items_table.columns)} columns for processing")
        
        # Upsert to MySQL database
        print("💾 Upserting data to MySQL database...")
        upsert_df_to_mysql(
            df=line_items_table,
            engine=db_engine,
            target_table='natura_line_items',
            key_col='key'
        )
        
        print("✅ Successfully processed and stored product data")
        print(f"Final data shape: {line_items_table.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
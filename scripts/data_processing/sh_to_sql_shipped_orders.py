
#!/usr/bin/env python3
"""
ShipHero to SQL Shipped Orders Script
Imports shipped orders data from Google Drive and upserts to MySQL database.
Processes data for both shipped orders and customer order list tables.
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Add src directory to path
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')

# Import required functions
from google_drive_csv_import import import_csv_from_drive
from cleanup_column_names import clean_column_names
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from generate_key import generate_key

def process_shipped_orders(shipped_orders):
    """Process shipped orders data for the natura_shipped_orders table"""
    print("📦 Processing shipped orders data...")
    
    # Clean column names
    shipped_orders = clean_column_names(shipped_orders)
    print("✅ Column names cleaned")
    
    # Fix specific column name mismatch for database compatibility
    if 'size_length_x_width_x_height_in' in shipped_orders.columns:
        shipped_orders = shipped_orders.rename(columns={'size_length_x_width_x_height_in': 'size_length_x_width_x_height__in'})
        print("✅ Fixed column name mismatch for size_length_x_width_x_height__in")
    
    # Convert order_date to datetime
    print("📅 Converting order_date column to datetime...")
    shipped_orders['order_date'] = pd.to_datetime(shipped_orders['order_date'])
    print("✅ Order date column converted")


    # keep the most recent 20 days in order_date
    # Normalize both dates to midnight for consistent comparison
    cutoff_date = (pd.Timestamp.now() - pd.Timedelta(days=20)).normalize()
    shipped_orders = shipped_orders[shipped_orders['order_date'] >= cutoff_date]
    


    # Generate unique key for deduplication
    print("🔑 Generating unique keys for shipped orders...")
    shipped_orders = generate_key(
        shipped_orders, 
        deduplication_columns=['order_id', 'quantity_shipped', 'order_number', 'order_date', 'email'], 
        key_col='key'
    )
    print("✅ Unique keys generated for shipped orders")
    
    # Drop duplicates based on key
    original_rows = len(shipped_orders)
    shipped_orders = shipped_orders.drop_duplicates(subset=['key'])
    removed_duplicates = original_rows - len(shipped_orders)
    print(f"✅ Removed {removed_duplicates} duplicate rows based on key")
    
    # Display data info
    print("\n📊 Shipped Orders Data Information:")
    shipped_orders.info()
    
    return shipped_orders

def process_customer_orderlist(shipped_orders):
    """Process customer order list data for the natura_customer_orderlist table"""
    print("\n👥 Processing customer order list data...")
    
    # Clean column names first
    shipped_orders_clean = clean_column_names(shipped_orders)
    
    # Select required columns for customer order list
    required_columns = ['order_id', 'order_number', 'order_date', 'to_name', 'email', 'address_1', 'address_2', 'city', 'state', 'zip', 'country', 'phone', 'line_item_total']
    missing_columns = [col for col in required_columns if col not in shipped_orders_clean.columns]
    
    if missing_columns:
        print(f"⚠️ Missing required columns: {missing_columns}")
        print(f"Available columns: {list(shipped_orders_clean.columns)}")
        # Use available columns that match the required ones
        available_required = [col for col in required_columns if col in shipped_orders_clean.columns]
        df_order = shipped_orders_clean[available_required].copy()
    else:
        df_order = shipped_orders_clean[required_columns].copy()
    
    print(f"✅ Selected {len(df_order.columns)} columns for customer order list")
    
    # Convert order_date to datetime
    print("📅 Converting order_date column to datetime...")
    df_order['order_date'] = pd.to_datetime(df_order['order_date'], format='mixed')
    print("✅ Order date column converted")
    
    # Process email (lowercase and strip)
    print("📧 Processing email column (lowercase and strip)...")
    df_order['email'] = df_order['email'].str.lower().str.strip()
    print("✅ Email column processed")
    
    # Process city (title case)
    print("🏙️ Processing city column (title case)...")
    df_order['city'] = df_order['city'].str.title()
    print("✅ City column processed")
    
    # Create customer_name from to_name
    print("👤 Creating customer_name from to_name...")
    df_order['customer_name'] = df_order['to_name']
    print("✅ Customer name created")
    
    # Create subtotal from line_item_total
    print("💰 Creating subtotal from line_item_total...")
    df_order['subtotal'] = df_order['line_item_total']
    print("✅ Subtotal created")
    
    # Drop columns
    columns_to_drop = ['to_name', 'line_item_total']
    existing_columns_to_drop = [col for col in columns_to_drop if col in df_order.columns]
    if existing_columns_to_drop:
        df_order = df_order.drop(columns=existing_columns_to_drop)
        print(f"✅ Dropped columns: {existing_columns_to_drop}")
    
    # Generate key for customer order list
    print("🔑 Generating unique keys for customer order list...")
    df_order = generate_key(
        df_order, 
        deduplication_columns=['order_id', 'order_number', 'subtotal'], 
        key_col='key'
    )
    print("✅ Unique keys generated for customer order list")
    
    # Drop duplicates
    original_rows = len(df_order)
    df_order = df_order.drop_duplicates(subset=['key'])
    removed_duplicates = original_rows - len(df_order)
    print(f"✅ Removed {removed_duplicates} duplicate rows based on key")
    
    print(f"✅ Customer order list data shape: {df_order.shape}")
    print(f"Customer order list columns: {list(df_order.columns)}")
    
    return df_order

def main():
    """Main function to process shipped orders data from Google Drive to MySQL"""
    
    # Load environment variables
    load_dotenv()
    
    # Database connection setup
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD', 'defaultpassword')
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    try:
        # Create database engine
        connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
        db_engine = create_engine(connection_string)
        
        print("✅ Database connection established")
        
        # Import data from Google Drive
        print("📥 Importing shipped orders data from Google Drive...")
        shipped_orders = import_csv_from_drive(
            starts_with="202",
            google_drive_id="1qWg8JKHMkqsPTk4gE_3ol57Not2R8Uu5"
        )
        
        if shipped_orders is None:
            print("❌ Failed to import data from Google Drive")
            return False
        
        print(f"✅ Successfully imported {len(shipped_orders)} rows")
        
        # Process shipped orders data
        shipped_orders_processed = process_shipped_orders(shipped_orders)
        
        # Process customer order list data
        customer_order_processed = process_customer_orderlist(shipped_orders)
        
        # Upsert shipped orders to MySQL database
        print("\n💾 Upserting shipped orders data to MySQL database...")
        upsert_df_to_mysql(
            df=shipped_orders_processed,
            engine=db_engine,
            target_table='natura_shipped_orders',
            key_col='key'
        )
        print("✅ Successfully stored shipped orders data")
        
        # Create a new engine for the second upsert to avoid connection issues
        print("🔄 Creating new database connection for customer order list...")
        db_engine_2 = create_engine(connection_string)
        
        # Upsert customer order list to MySQL database
        print("\n💾 Upserting customer order list data to MySQL database...")
        upsert_df_to_mysql(
            df=customer_order_processed,
            engine=db_engine_2,
            target_table='natura_customer_orderlist',
            key_col='key'
        )
        print("✅ Successfully stored customer order list data")
        
        print(f"\n✅ Successfully processed and stored all data")
        print(f"Shipped orders final shape: {shipped_orders_processed.shape}")
        print(f"Customer order list final shape: {customer_order_processed.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
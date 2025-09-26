#!/usr/bin/env python3
"""
Script to set up local database for customer cohort chart
"""
import sys
import os
from datetime import datetime

ROOT_DIR = '/home/mongreldatalab/mongrel_price_ticker'
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Set local database environment variables
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_NAME'] = 'mongrel_price_ticker_local'
os.environ['DB_USER'] = 'mongreldatalab'
os.environ['DB_PASSWORD'] = 'localpass123'
os.environ['DB_PORT'] = '30306'

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df
import pandas as pd

def create_local_database():
    """Create the local database and tables"""
    print("Setting up local database...")
    
    # Connect to MySQL server (without specifying database)
    import mysql.connector
    from mysql.connector import Error
    
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host='localhost',
            user='mongreldatalab',
            password='localpass123',
            port=30306
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS mongrel_price_ticker_local")
            print("✅ Database 'mongrel_price_ticker_local' created or already exists")
            
            # Use the database
            cursor.execute("USE mongrel_price_ticker_local")
            
            # Create tables (we'll get the structure from the remote database)
            print("Creating tables...")
            
            # For now, create basic table structures
            # We'll populate them with data from the remote database
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS natura_customer_profile (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE,
                    first_order_date DATETIME,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS natura_shipped_orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255),
                    order_date DATETIME,
                    order_number VARCHAR(255) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS natura_line_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_date DATETIME,
                    order_number VARCHAR(255),
                    quantity DECIMAL(10,2),
                    price DECIMAL(10,2),
                    subtotal DECIMAL(10,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            print("✅ Tables created successfully")
            
    except Error as e:
        print(f"❌ Error creating database: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
    
    return True

def migrate_data_from_remote():
    """Migrate data from remote database to local database"""
    print("Migrating data from remote database...")
    
    # First, get data from remote database
    # Temporarily switch back to remote database
    os.environ['DB_HOST'] = '127.0.0.1'
    os.environ['DB_NAME'] = 'u488367489_Price_Ticker'
    os.environ['DB_USER'] = 'u488367489_mongrel_data'
    os.environ['DB_PASSWORD'] = 'Quezon12345678'
    
    try:
        remote_engine = get_database_engine()
        
        # Read data from remote database
        print("Reading customer profile data...")
        prof_df = read_mysql_to_df(engine=remote_engine, table_name='natura_customer_profile')
        
        print("Reading shipped orders data...")
        orders_df = read_mysql_to_df(engine=remote_engine, table_name='natura_shipped_orders')
        
        print("Reading line items data...")
        lines_df = read_mysql_to_df(engine=remote_engine, table_name='natura_line_items')
        
        if prof_df is None or prof_df.empty:
            print("❌ No customer profile data found")
            return False
            
        if orders_df is None or orders_df.empty:
            print("❌ No orders data found")
            return False
            
        if lines_df is None or lines_df.empty:
            print("❌ No line items data found")
            return False
        
        print(f"✅ Found {len(prof_df)} customer profiles, {len(orders_df)} orders, {len(lines_df)} line items")
        
        # Switch back to local database
        os.environ['DB_HOST'] = 'localhost'
        os.environ['DB_NAME'] = 'mongrel_price_ticker_local'
        os.environ['DB_USER'] = 'mongreldatalab'
        os.environ['DB_PASSWORD'] = 'localpass123'
        
        local_engine = get_database_engine()
        
        # Write data to local database
        print("Writing customer profile data to local database...")
        prof_df.to_sql('natura_customer_profile', local_engine, if_exists='replace', index=False)
        
        print("Writing orders data to local database...")
        orders_df.to_sql('natura_shipped_orders', local_engine, if_exists='replace', index=False)
        
        print("Writing line items data to local database...")
        lines_df.to_sql('natura_line_items', local_engine, if_exists='replace', index=False)
        
        print("✅ Data migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error migrating data: {e}")
        return False

def test_local_database():
    """Test the local database connection and data"""
    print("Testing local database...")
    
    try:
        engine = get_database_engine()
        
        # Test reading data
        prof_df = read_mysql_to_df(engine=engine, table_name='natura_customer_profile')
        orders_df = read_mysql_to_df(engine=engine, table_name='natura_shipped_orders')
        lines_df = read_mysql_to_df(engine=engine, table_name='natura_line_items')
        
        if prof_df is not None and not prof_df.empty:
            print(f"✅ Customer profiles: {len(prof_df)} records")
        else:
            print("❌ No customer profile data")
            
        if orders_df is not None and not orders_df.empty:
            print(f"✅ Orders: {len(orders_df)} records")
        else:
            print("❌ No orders data")
            
        if lines_df is not None and not lines_df.empty:
            print(f"✅ Line items: {len(lines_df)} records")
        else:
            print("❌ No line items data")
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing local database: {e}")
        return False

def main():
    print("=== Setting up Local Database for Customer Cohort Chart ===")
    
    # Step 1: Create local database and tables
    if not create_local_database():
        print("❌ Failed to create local database")
        return
    
    # Step 2: Migrate data from remote database
    if not migrate_data_from_remote():
        print("❌ Failed to migrate data")
        return
    
    # Step 3: Test local database
    if not test_local_database():
        print("❌ Local database test failed")
        return
    
    print("\n🎉 Local database setup completed successfully!")
    print("You can now run the customer cohort chart script with the local database.")
    print("\nTo use the local database, set these environment variables:")
    print("export DB_HOST='localhost'")
    print("export DB_NAME='mongrel_price_ticker_local'")
    print("export DB_USER='mongreldatalab'")
    print("export DB_PASSWORD='localpass123'")
    print("export DB_PORT='30306'")

if __name__ == '__main__':
    main()

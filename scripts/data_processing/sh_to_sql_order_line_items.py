
#!/usr/bin/env python3
"""
ShipHero to SQL Product Table Script
Imports product data from JSON file and upserts to MySQL database.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Import required functions via package
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))
from cleanup_column_names import clean_column_names
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from generate_key import generate_key

def load_json_data(json_file_path):
    """Load and process product data from JSON file"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Extract products from the JSON structure
        products = data.get('products', [])
        
        if not products:
            print("❌ No products found in JSON file")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(products)
        
        # Map JSON fields to expected column names for line items
        # Since this is product data, we'll create mock order line items
        line_items_data = []
        
        for _, product in df.iterrows():
            # Create a mock order line item for each product
            # In a real scenario, you'd have actual order data
            line_item = {
                'order_date': datetime.now().strftime('%Y-%m-%d'),
                'sku': str(product.get('sku', '')),
                'name': product.get('name', ''),
                'quantity': 1,  # Default quantity
                'price': float(product.get('price', 0)),
                'subtotal': float(product.get('price', 0)),  # Same as price for quantity 1
                'order_number': f"MOCK_ORDER_{product.get('product_id', '')}",
                'customer_email': 'mock@example.com',
                'product_id': product.get('product_id'),
                'brand_name': product.get('brand_name', ''),
                'upc': product.get('upc', ''),
                'weight_kg': product.get('weight_kg', 0),
                'stock_quantity': product.get('stock_quantity', 0),
                'category_id': product.get('category_id', ''),
                'currency': product.get('currency', 'CAD'),
                'last_modified': product.get('last_modified', '')
            }
            line_items_data.append(line_item)
        
        return pd.DataFrame(line_items_data)
        
    except FileNotFoundError:
        print(f"❌ JSON file not found: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return None
    except Exception as e:
        print(f"❌ Error loading JSON data: {e}")
        return None

def main():
    """Main function to process product data from JSON file to MySQL"""
    
    # Load environment variables
    load_dotenv()
    
    # Database connection setup
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        raise ValueError("DB_PASSWORD environment variable is required (no default in repo)")
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    # JSON file path
    json_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'scraping_progress.json')
    
    try:
        # Create database engine
        connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        db_engine = create_engine(connection_string)
        
        print("✅ Database connection established")
        
        # Import data from JSON file
        print("📥 Importing product data from JSON file...")
        line_items_table = load_json_data(json_file_path)
        
        if line_items_table is None:
            print("❌ Failed to import data from JSON file")
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
        # Select only the columns that exist in the target table
        # Based on the current table schema: order_date, sku, name, quantity, price, subtotal, order_number, customer_email, key
        table_columns = ['order_date', 'sku', 'name', 'quantity', 'price', 'subtotal', 'order_number', 'customer_email', 'key']
        
        # Check for missing required columns
        missing_columns = [col for col in table_columns if col not in line_items_table.columns]
        
        if missing_columns:
            print(f"⚠️ Missing required columns: {missing_columns}")
            print(f"Available columns: {list(line_items_table.columns)}")
            # Use available columns that match the table schema
            available_columns = [col for col in table_columns if col in line_items_table.columns]
            line_items_table = line_items_table[available_columns]
        else:
            # Use only the columns that exist in the table
            line_items_table = line_items_table[table_columns]
        
        print(f"✅ Selected {len(line_items_table.columns)} columns for processing")
        
        # Upsert to MySQL database
        print("💾 Upserting data to MySQL database...")
        upsert_df_to_mysql(
            df=line_items_table,
            engine=db_engine,
            target_table='natura_line_items',
            key_col='key'
        )
        
        print("✅ Successfully processed and stored product data from JSON file")
        print(f"Final data shape: {line_items_table.shape}")
        
        return True
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
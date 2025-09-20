#!/usr/bin/env python3
"""
Test error handling and edge cases
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add src directory to path
sys.path.append("/home/mongreldatalab/mongrel_price_ticker/scripts/data_processing")

# Import the functions to test
from sh_to_sql_shipped_orders import process_shipped_orders, process_customer_orderlist, main

def test_empty_data():
    """Test handling of empty data"""
    print("🧪 Testing empty data handling...")
    
    empty_df = pd.DataFrame()
    
    try:
        result = process_shipped_orders(empty_df)
        print(f"✅ Empty data handled: {result.shape}")
    except Exception as e:
        print(f"❌ Empty data error: {e}")
    
    try:
        result = process_customer_orderlist(empty_df)
        print(f"✅ Empty data handled: {result.shape}")
    except Exception as e:
        print(f"❌ Empty data error: {e}")

def test_missing_columns():
    """Test handling of missing columns"""
    print("\n🧪 Testing missing columns handling...")
    
    # Data with missing required columns
    incomplete_data = pd.DataFrame({
        'order_id': ['ORD001'],
        'order_number': ['ON001'],
        'order_date': [datetime.now().strftime('%Y-%m-%d')]
    })
    
    try:
        result = process_customer_orderlist(incomplete_data)
        print(f"✅ Missing columns handled: {result.shape}")
        print(f"✅ Available columns: {list(result.columns)}")
    except Exception as e:
        print(f"❌ Missing columns error: {e}")

def test_old_data_filter():
    """Test 30-day filter with old data"""
    print("\n🧪 Testing 30-day filter...")
    
    # Data with old dates (more than 30 days ago)
    old_data = pd.DataFrame({
        'order_id': ['ORD001'],
        'quantity_shipped': [2],
        'order_number': ['ON001'],
        'order_date': [(datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d')],
        'email': ['test@example.com'],
        'to_name': ['John Doe'],
        'address_1': ['123 Main St'],
        'address_2': [''],
        'city': ['New York'],
        'state': ['NY'],
        'zip': ['10001'],
        'country': ['USA'],
        'phone': ['555-1234'],
        'line_item_total': [29.99],
        'size_length_x_width_x_height_in': ['10x5x2'],
        'product_name': ['Product A']
    })
    
    try:
        result = process_shipped_orders(old_data)
        print(f"✅ Old data filtered: {result.shape} (should be 0)")
    except Exception as e:
        print(f"❌ Old data filter error: {e}")

def test_duplicate_handling():
    """Test duplicate handling"""
    print("\n🧪 Testing duplicate handling...")
    
    # Data with duplicates
    duplicate_data = pd.DataFrame({
        'order_id': ['ORD001', 'ORD001', 'ORD002'],
        'quantity_shipped': [2, 2, 1],
        'order_number': ['ON001', 'ON001', 'ON002'],
        'order_date': [datetime.now().strftime('%Y-%m-%d')] * 3,
        'email': ['test@example.com', 'test@example.com', 'test2@example.com'],
        'to_name': ['John Doe', 'John Doe', 'Jane Smith'],
        'address_1': ['123 Main St', '123 Main St', '456 Oak Ave'],
        'address_2': ['', '', ''],
        'city': ['New York', 'New York', 'Los Angeles'],
        'state': ['NY', 'NY', 'CA'],
        'zip': ['10001', '10001', '90210'],
        'country': ['USA', 'USA', 'USA'],
        'phone': ['555-1234', '555-1234', '555-5678'],
        'line_item_total': [29.99, 29.99, 15.50],
        'size_length_x_width_x_height_in': ['10x5x2', '10x5x2', '8x4x1'],
        'product_name': ['Product A', 'Product A', 'Product B']
    })
    
    try:
        result = process_shipped_orders(duplicate_data)
        print(f"✅ Duplicates handled: {result.shape} (should be 2)")
        print(f"✅ Unique keys: {result['key'].nunique()}")
    except Exception as e:
        print(f"❌ Duplicate handling error: {e}")

def test_main_function_errors():
    """Test main function error handling"""
    print("\n🧪 Testing main function error handling...")
    
    # Test import failure
    with patch('sh_to_sql_shipped_orders.import_csv_from_drive') as mock_import:
        mock_import.return_value = None
        
        result = main()
        print(f"✅ Import failure handled: {result} (should be False)")
    
    # Test database connection failure
    with patch('sh_to_sql_shipped_orders.import_csv_from_drive') as mock_import, \
         patch('sh_to_sql_shipped_orders.create_engine') as mock_engine:
        
        mock_import.return_value = pd.DataFrame({
            'order_id': ['ORD001'],
            'quantity_shipped': [2],
            'order_number': ['ON001'],
            'order_date': [datetime.now().strftime('%Y-%m-%d')],
            'email': ['test@example.com'],
            'to_name': ['John Doe'],
            'address_1': ['123 Main St'],
            'address_2': [''],
            'city': ['New York'],
            'state': ['NY'],
            'zip': ['10001'],
            'country': ['USA'],
            'phone': ['555-1234'],
            'line_item_total': [29.99],
            'size_length_x_width_x_height_in': ['10x5x2'],
            'product_name': ['Product A']
        })
        
        mock_engine.side_effect = Exception("Database connection failed")
        
        result = main()
        print(f"✅ Database error handled: {result} (should be False)")

if __name__ == "__main__":
    print("🚀 Error Handling Tests")
    print("=" * 40)
    
    try:
        test_empty_data()
        test_missing_columns()
        test_old_data_filter()
        test_duplicate_handling()
        test_main_function_errors()
        print("\n🎉 All error handling tests completed!")
    except Exception as e:
        print(f"\n❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()

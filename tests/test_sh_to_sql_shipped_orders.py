#!/usr/bin/env python3
"""
Test script for sh_to_sql_shipped_orders.py
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

def create_test_data():
    """Create mock test data"""
    return pd.DataFrame({
        'order_id': ['ORD001', 'ORD002', 'ORD003'],
        'quantity_shipped': [2, 1, 3],
        'order_number': ['ON001', 'ON002', 'ON003'],
        'order_date': [(datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')] * 3,
        'email': ['test1@example.com', 'test2@example.com', 'test3@example.com'],
        'to_name': ['John Doe', 'Jane Smith', 'Bob Johnson'],
        'address_1': ['123 Main St', '456 Oak Ave', '789 Pine Rd'],
        'address_2': ['Apt 1', '', 'Suite 2'],
        'city': ['new york', 'los angeles', 'chicago'],
        'state': ['NY', 'CA', 'IL'],
        'zip': ['10001', '90210', '60601'],
        'country': ['USA', 'USA', 'USA'],
        'phone': ['555-1234', '555-5678', '555-9012'],
        'line_item_total': [29.99, 15.50, 45.00],
        'size_length_x_width_x_height_in': ['10x5x2', '8x4x1', '12x6x3'],
        'product_name': ['Product A', 'Product B', 'Product C']
    })

def test_process_shipped_orders():
    """Test process_shipped_orders function"""
    print("🧪 Testing process_shipped_orders...")
    
    test_data = create_test_data()
    result = process_shipped_orders(test_data)
    
    # Basic checks
    assert isinstance(result, pd.DataFrame)
    assert 'key' in result.columns
    assert 'size_length_x_width_x_height__in' in result.columns
    assert pd.api.types.is_datetime64_any_dtype(result['order_date'])
    assert len(result) == 3
    assert result['key'].nunique() == len(result)
    
    print("✅ process_shipped_orders test passed")

def test_process_customer_orderlist():
    """Test process_customer_orderlist function"""
    print("🧪 Testing process_customer_orderlist...")
    
    test_data = create_test_data()
    result = process_customer_orderlist(test_data)
    
    # Check required columns
    required_cols = ['order_id', 'order_number', 'order_date', 'email', 'customer_name', 'subtotal']
    for col in required_cols:
        assert col in result.columns, f"Missing column: {col}"
    
    # Check transformations
    assert pd.api.types.is_datetime64_any_dtype(result['order_date'])
    assert all(result['email'].str.islower())
    assert all(result['city'].str.istitle())
    assert 'customer_name' in result.columns
    assert 'subtotal' in result.columns
    assert 'key' in result.columns
    
    print("✅ process_customer_orderlist test passed")

def test_main_function():
    """Test main function with mocked dependencies"""
    print("🧪 Testing main function...")
    
    test_data = create_test_data()
    
    with patch('sh_to_sql_shipped_orders.import_csv_from_drive') as mock_import, \
         patch('sh_to_sql_shipped_orders.create_engine') as mock_engine, \
         patch('sh_to_sql_shipped_orders.upsert_df_to_mysql') as mock_upsert:
        
        mock_import.return_value = test_data
        mock_engine.return_value = Mock()
        mock_upsert.return_value = None
        
        result = main()
        assert result is True
        mock_import.assert_called_once()
        assert mock_upsert.call_count == 2
    
    print("✅ main function test passed")

def main():
    """Run all tests"""
    print("🚀 Testing sh_to_sql_shipped_orders.py")
    print("=" * 50)
    
    try:
        test_process_shipped_orders()
        test_process_customer_orderlist()
        test_main_function()
        print("\n🎉 All tests passed!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

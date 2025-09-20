#!/usr/bin/env python3
"""
Simple test for sh_to_sql_shipped_orders.py
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add src directory to path
sys.path.append("/home/mongreldatalab/mongrel_price_ticker/scripts/data_processing")

# Import the functions to test
from sh_to_sql_shipped_orders import process_shipped_orders, process_customer_orderlist

def test_basic_functionality():
    """Test basic functionality without recursion"""
    print("🧪 Testing basic functionality...")
    
    # Create test data
    test_data = pd.DataFrame({
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
    
    print(f"📊 Input data shape: {test_data.shape}")
    print(f"📊 Input columns: {list(test_data.columns)}")
    
    # Test shipped orders processing
    print("\n🔧 Testing process_shipped_orders...")
    shipped_result = process_shipped_orders(test_data)
    print(f"✅ Shipped orders result shape: {shipped_result.shape}")
    print(f"✅ Key column present: {'key' in shipped_result.columns}")
    print(f"✅ Fixed column present: {'size_length_x_width_x_height__in' in shipped_result.columns}")
    
    # Test customer order list processing
    print("\n🔧 Testing process_customer_orderlist...")
    customer_result = process_customer_orderlist(test_data)
    print(f"✅ Customer orders result shape: {customer_result.shape}")
    print(f"✅ Customer name present: {'customer_name' in customer_result.columns}")
    print(f"✅ Subtotal present: {'subtotal' in customer_result.columns}")
    
    # Display sample results
    print("\n📊 Sample shipped orders data:")
    print(shipped_result[['order_id', 'order_date', 'email', 'key']].head())
    
    print("\n📊 Sample customer orders data:")
    print(customer_result[['order_id', 'customer_name', 'email', 'subtotal']].head())
    
    return True

if __name__ == "__main__":
    print("🚀 Simple test for sh_to_sql_shipped_orders.py")
    print("=" * 50)
    
    try:
        test_basic_functionality()
        print("\n🎉 Test completed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

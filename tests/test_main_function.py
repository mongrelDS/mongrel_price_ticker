#!/usr/bin/env python3
"""
Test main function with proper mocking
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add src directory to path
sys.path.append("/home/mongreldatalab/mongrel_price_ticker/scripts/data_processing")

# Import the main function
from sh_to_sql_shipped_orders import main

def test_main_function():
    """Test main function with mocked dependencies"""
    print("🧪 Testing main function...")
    
    # Create test data
    test_data = pd.DataFrame({
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
    
    # Mock all external dependencies
    with patch('sh_to_sql_shipped_orders.import_csv_from_drive') as mock_import, \
         patch('sh_to_sql_shipped_orders.create_engine') as mock_engine, \
         patch('sh_to_sql_shipped_orders.upsert_df_to_mysql') as mock_upsert:
        
        # Configure mocks
        mock_import.return_value = test_data
        mock_engine_instance = Mock()
        mock_engine.return_value = mock_engine_instance
        mock_upsert.return_value = None
        
        # Run main function
        result = main()
        
        # Check results
        print(f"✅ Main function returned: {result}")
        print(f"✅ Import called: {mock_import.called}")
        print(f"✅ Upsert called {mock_upsert.call_count} times")
        
        return result is True

if __name__ == "__main__":
    print("🚀 Testing main function")
    print("=" * 30)
    
    try:
        success = test_main_function()
        if success:
            print("\n🎉 Main function test passed!")
        else:
            print("\n❌ Main function test failed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

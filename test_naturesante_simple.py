#!/usr/bin/env python3
"""
Simple test for naturesante_product_ticker_data.py
This test focuses on the core functionality without database dependencies.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime

def test_scrape_function():
    """Test the scrape_product_data function."""
    print("🧪 Testing scrape_product_data function")
    print("=" * 50)
    
    # Add the script directory to path
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'scrapers', 'naturesante')
    sys.path.insert(0, script_path)
    
    try:
        from naturesante_product_ticker_data import scrape_product_data
        
        # Test with a non-existent URL to test error handling
        test_url = 'https://naturesante.ca/products/test-product-12345'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"Testing URL: {test_url}")
        result = scrape_product_data(test_url, headers)
        
        print("✅ Scrape function executed successfully")
        print(f"Result keys: {list(result.keys())}")
        print(f"Expected keys: ['link', 'title', 'brand', 'price', 'tag', 'imgurl', 'item_code']")
        
        # Check if all expected keys are present
        expected_keys = ['link', 'title', 'brand', 'price', 'tag', 'imgurl', 'item_code']
        missing_keys = [key for key in expected_keys if key not in result]
        
        if missing_keys:
            print(f"❌ Missing keys: {missing_keys}")
            return False
        else:
            print("✅ All expected keys present")
            
        # Check error handling
        if 'ERROR' in str(result.values()):
            print("✅ Error handling working correctly")
        else:
            print("⚠️  Expected error handling, but got normal response")
            
        return True
        
    except Exception as e:
        print(f"❌ Scrape function test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_processing():
    """Test the data processing functions."""
    print("\n🧪 Testing data processing functions")
    print("=" * 50)
    
    try:
        # Add src directory to path
        src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        
        from get_domain import get_domain
        from function_extract_volume import extract_volume
        from price_to_float import price_to_float
        from generate_key import generate_key
        
        # Create test data
        test_data = [
            {
                'link': 'https://naturesante.ca/products/test-product-1',
                'title': 'Test Product 1 - 100ml',
                'brand': 'Test Brand',
                'price': '$19.99',
                'tag': 'In Stock',
                'imgurl': 'https://example.com/image1.jpg',
                'item_code': 'test-1'
            },
            {
                'link': 'https://naturesante.ca/products/test-product-2',
                'title': 'Test Product 2 - 250ml Bottle',
                'brand': 'Another Brand',
                'price': '$29.99',
                'tag': 'Out of Stock',
                'imgurl': 'https://example.com/image2.jpg',
                'item_code': 'test-2'
            }
        ]
        
        df = pd.DataFrame(test_data)
        print(f"✅ Created test DataFrame with {len(df)} rows")
        
        # Test get_domain
        df = get_domain(df, 'link')
        print("✅ get_domain function: SUCCESS")
        
        # Test extract_volume
        df = extract_volume(df, vol_col="title", result_col="vol")
        print("✅ extract_volume function: SUCCESS")
        
        # Test price_to_float
        df = price_to_float(df, price_col="price", currency_marker="$")
        print("✅ price_to_float function: SUCCESS")
        
        # Test generate_key
        df['date'] = datetime.now().strftime('%Y-%m-%d')
        df_ticker = df[['link', 'item_code', 'domain', 'price', 'date', 'tag']].copy()
        df_ticker = df_ticker.rename(columns={'item_code': 'sku'})
        df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")
        print("✅ generate_key function: SUCCESS")
        
        print(f"Final DataFrame shape: {df_ticker.shape}")
        print(f"Final columns: {list(df_ticker.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_duration_calculation():
    """Test the duration calculation logic."""
    print("\n🧪 Testing duration calculation")
    print("=" * 50)
    
    try:
        # Simulate start and end times
        start_time = time.time()
        time.sleep(0.1)  # Simulate some work
        end_time = time.time()
        
        duration_in_minutes = (end_time - start_time) / 60
        print(f"Duration: {duration_in_minutes:.4f} minutes")
        
        # Test DataFrame creation
        df_duration = pd.DataFrame({'duration_min': [duration_in_minutes], 'date': [datetime.now()]})
        df_duration['results'] = 100  # Simulate results
        df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
        df_duration['domain'] = 'naturesante.ca'
        df_duration['type'] = 'product_ticker_data'
        
        print("✅ Duration calculation: SUCCESS")
        print(f"Results per minute: {df_duration['result_per_minute'].iloc[0]:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Duration calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Starting Nature Santé Script Tests")
    print("=" * 60)
    
    tests = [
        test_scrape_function,
        test_data_processing,
        test_duration_calculation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests PASSED!")
        return True
    else:
        print("❌ Some tests FAILED!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Dry run test for naturesante_product_ticker_data.py
This test simulates the main function flow without actually scraping data.
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime

# Add the src directory to the path so we can import our modules
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Add the analytics directory to the path
analytics_path = os.path.join(os.path.dirname(__file__), 'scripts', 'analytics')
sys.path.append(analytics_path)

def test_dry_run():
    """Test the main function flow with mock data."""
    print("🧪 Starting Dry Run Test for Nature Santé Scraper")
    print("=" * 60)
    
    # Record start time for duration calculation
    start_time = time.time()
    
    # Test database connection
    try:
        from database_config import get_database_engine
        db_engine = get_database_engine()
        print("✅ Database connection established")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

    # Test getting data from database
    try:
        from df_price_30d import get_price_30d
        df_link = get_price_30d(domain='naturesante.ca', table_name='df_ticker', verbose=True)
        print(f"📊 Total product URLs in database: {len(df_link)}")
    except Exception as e:
        print(f"❌ Failed to read from database: {e}")
        return False

    # Test data filtering
    df_link = df_link[df_link['link'].str.contains('naturesante.ca')]
    df_link = df_link[df_link['tag'] != 'Failed']
    df_link = df_link.sort_values(by='date', ascending=False)
    df_link = df_link.tail(10)  # Use only 10 for testing
    
    print(f"📊 Nature Santé product URLs found: {len(df_link)}")
    
    if len(df_link) == 0:
        print("❌ No Nature Santé product URLs found")
        return False

    # Test data processing functions
    try:
        from get_domain import get_domain
        from function_extract_volume import extract_volume
        from price_to_float import price_to_float
        from generate_key import generate_key
        
        # Create mock scraped data
        mock_data = []
        for i, link in enumerate(df_link['link'].head(3)):  # Test with 3 URLs
            mock_data.append({
                'link': link,
                'title': f'Test Product {i+1}',
                'brand': 'Test Brand',
                'price': '$19.99',
                'tag': 'In Stock',
                'imgurl': 'https://example.com/image.jpg',
                'item_code': f'test-{i+1}'
            })
        
        df_pdp_links = pd.DataFrame(mock_data)
        print(f"✅ Created mock data with {len(df_pdp_links)} products")
        
        # Test data processing pipeline
        df_pdp_links = get_domain(df_pdp_links, 'link')
        df_pdp_links = extract_volume(df_pdp_links, vol_col="title", result_col="vol")
        df_pdp_links = df_pdp_links.rename(columns={'item_code': 'sku'})
        df_pdp_links['date'] = datetime.now().strftime('%Y-%m-%d')
        
        print("✅ Data processing pipeline: SUCCESS")
        
        # Test required columns validation
        required_columns = ['link', 'imgurl', 'title', 'brand', 'sku', 'vol', 'domain', 'price', 'tag']
        missing_columns = [col for col in required_columns if col not in df_pdp_links.columns]
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        else:
            print("✅ Required columns validation: SUCCESS")
        
        # Test price processing
        df_pdp_links = price_to_float(df_pdp_links, price_col="price", currency_marker="$")
        df_ticker = df_pdp_links[['link', 'sku', 'domain', 'price','date','tag']]
        df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")
        
        print("✅ Price processing and key generation: SUCCESS")
        
    except Exception as e:
        print(f"❌ Data processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test duration calculation
    end_time = time.time()
    duration_in_minutes = (end_time - start_time) / 60
    
    df_duration = pd.DataFrame({'duration_min': [duration_in_minutes], 'date': [datetime.now()]})
    df_duration['results'] = len(df_ticker)
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
    df_duration['domain'] = 'naturesante.ca'
    df_duration['type'] = 'product_ticker_data'
    
    print("✅ Duration calculation: SUCCESS")
    print(f"   Duration: {duration_in_minutes:.4f} minutes")
    print(f"   Results: {len(df_ticker)}")
    print(f"   Results per minute: {df_duration['result_per_minute'].iloc[0]:.2f}")
    
    print("\n🎉 Dry run test completed successfully!")
    print("✅ All components are working correctly")
    
    return True

if __name__ == "__main__":
    success = test_dry_run()
    if success:
        print("\n✅ Dry run test PASSED!")
    else:
        print("\n❌ Dry run test FAILED!")
        sys.exit(1)

#!/usr/bin/env python3
"""
Test script for the updated healthyplanet_crawler.py with database URL loading
"""

import sys
import asyncio
import pandas as pd
import nest_asyncio

# Add the project root to the Python path
sys.path.append('/home/mongreldatalab/mongrel_price_ticker')

def test_imports():
    """Test all imports work correctly"""
    print("🔍 Testing Imports...")
    try:
        from scripts.scrapers.healthyplanet.healthyplanet_crawler import (
            run_healthyplanet_crawler, 
            main,
            INITIAL_URLS
        )
        from src.proxy_config import reset_proxy_credentials, get_proxy_stats
        from src.database_config import get_database_engine
        from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df
        
        print("✅ All imports successful")
        print(f"  Fallback URLs: {INITIAL_URLS}")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_url_loading():
    """Test loading URLs from database"""
    print("\n🗄️ Testing Database URL Loading...")
    try:
        from src.database_config import get_database_engine
        from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df
        
        # Initialize database
        db_engine = get_database_engine()
        print("✅ Database engine created")
        
        # Test reading from cat_link_list table
        df_urls = read_mysql_to_df(engine=db_engine, table_name='cat_link_list')
        
        if df_urls is not None and len(df_urls) > 0:
            print(f"✅ Found {len(df_urls)} URLs in database")
            print(f"  Sample URLs:")
            for i, url in enumerate(df_urls['link'].head(3)):
                print(f"    {i+1}. {url}")
            
            # Test sampling
            sampled = df_urls.sample(min(5, len(df_urls)))
            print(f"  Sampled {len(sampled)} URLs for testing")
            return True
        else:
            print("⚠️ No URLs found in database")
            return False
            
    except Exception as e:
        print(f"❌ Database URL loading error: {e}")
        return False

def test_crawler_with_database_urls():
    """Test the crawler with database-loaded URLs"""
    print("\n🕷️ Testing Crawler with Database URLs...")
    try:
        from scripts.scrapers.healthyplanet.healthyplanet_crawler import run_healthyplanet_crawler
        from src.proxy_config import reset_proxy_credentials
        
        # Reset proxy credentials
        reset_proxy_credentials()
        print("🔄 Reset proxy credentials")
        
        # Run the crawler
        print("🚀 Running crawler with database URLs...")
        df_link, df_link_item, df_catlink = run_healthyplanet_crawler()
        
        print(f"\n✅ Crawler completed successfully!")
        print(f"📊 Results:")
        print(f"  - Total links found: {len(df_link)}")
        print(f"  - Product links: {len(df_link_item)}")
        print(f"  - Category links: {len(df_catlink)}")
        
        # Show some examples
        if len(df_link_item) > 0:
            print(f"\n📄 Sample product links:")
            for i, link in enumerate(df_link_item['link'].head(3)):
                print(f"  {i+1}. {link}")
        
        if len(df_catlink) > 0:
            print(f"\n📁 Sample category links:")
            for i, link in enumerate(df_catlink['link'].head(3)):
                print(f"  {i+1}. {link}")
        
        return True
        
    except Exception as e:
        print(f"❌ Crawler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_behavior():
    """Test fallback behavior when database is empty"""
    print("\n🔄 Testing Fallback Behavior...")
    try:
        from scripts.scrapers.healthyplanet.healthyplanet_crawler import main, INITIAL_URLS
        
        # Test main function with fallback URLs
        print("Testing main function with fallback URLs...")
        result = asyncio.run(main(INITIAL_URLS))
        
        if result is not None and len(result) > 0:
            print(f"✅ Fallback behavior working - found {len(result)} links")
            return True
        else:
            print("⚠️ Fallback behavior may have issues")
            return False
            
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing Updated Healthy Planet Crawler")
    print("=" * 60)
    
    # Apply nest_asyncio
    nest_asyncio.apply()
    
    tests = [
        ("Imports", test_imports),
        ("Database URL Loading", test_database_url_loading),
        ("Fallback Behavior", test_fallback_behavior),
        ("Full Crawler Test", test_crawler_with_database_urls)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("-" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! The updated crawler is ready for production use.")
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

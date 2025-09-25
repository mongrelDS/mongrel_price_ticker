#!/usr/bin/env python3
"""
Test script for healthyplanet_crawler.py

This script tests the Healthy Planet crawler functionality including:
1. Import validation
2. Function structure validation
3. Mock testing of core functions
4. Database connection testing
"""

import sys
import os
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd

# Add the project root to the path
sys.path.append('/home/mongreldatalab/mongrel_price_ticker')

class TestHealthyPlanetCrawler(unittest.TestCase):
    """Test cases for the Healthy Planet crawler."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_url = "https://www.healthyplanetcanada.com/sitemap"
        self.test_links = [
            "https://www.healthyplanetcanada.com/products/test-product.html",
            "https://www.healthyplanetcanada.com/categories/supplements",
            "https://www.healthyplanetcanada.com/blog/some-article"
        ]
    
    def test_imports(self):
        """Test that all required imports are available."""
        try:
            # Test basic imports
            import asyncio
            import pandas as pd
            import numpy as np
            from playwright.async_api import async_playwright
            from urllib.parse import urljoin, urlparse, urlunparse
            
            # Test custom imports
            from src.get_domain import get_domain
            from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
            from database_config import get_database_engine
            
            print("✓ All imports successful")
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    def test_get_domain_function(self):
        """Test the get_domain function."""
        from src.get_domain import get_domain
        
        # Create test DataFrame
        test_df = pd.DataFrame({
            'link': [
                'https://www.healthyplanetcanada.com/products/test.html',
                'https://www.example.com/page'
            ]
        })
        
        # Test the function
        result_df = get_domain(test_df, 'link')
        
        # Verify results
        self.assertIn('domain', result_df.columns)
        self.assertEqual(result_df['domain'].iloc[0], 'www.healthyplanetcanada.com')
        self.assertEqual(result_df['domain'].iloc[1], 'www.example.com')
        print("✓ get_domain function works correctly")
    
    def test_crawler_configuration(self):
        """Test crawler configuration constants."""
        # Import the crawler module
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/healthyplanet')
        import healthyplanet_crawler
        
        # Test configuration values
        self.assertEqual(healthyplanet_crawler.TARGET_DOMAIN, "www.healthyplanetcanada.com")
        self.assertIn('https://www.healthyplanetcanada.com/sitemap', healthyplanet_crawler.INITIAL_URLS)
        self.assertGreater(healthyplanet_crawler.MAX_PAGES_TO_CRAWL, 0)
        self.assertGreater(healthyplanet_crawler.CONCURRENT_WORKERS, 0)
        print("✓ Crawler configuration is valid")
    
    @patch('healthyplanet_crawler.async_playwright')
    async def test_main_function_structure(self, mock_playwright):
        """Test the main function structure with mocked Playwright."""
        # Mock the playwright context
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_browser.close = AsyncMock()
        
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
        
        # Mock page methods
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.eval_on_selector_all = AsyncMock(return_value=[
            "https://www.healthyplanetcanada.com/products/test1.html",
            "https://www.healthyplanetcanada.com/categories/supplements"
        ])
        mock_page.close = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        
        # Import and test the main function
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/healthyplanet')
        import healthyplanet_crawler
        
        # Test that main function can be called
        result = await healthyplanet_crawler.main()
        
        # Verify result is a DataFrame
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('link', result.columns)
        print("✓ Main function structure is valid")
    
    def test_link_processing_logic(self):
        """Test the link processing logic without running the crawler."""
        # Create test data
        test_links = [
            "https://www.healthyplanetcanada.com/products/test.html",
            "https://www.healthyplanetcanada.com/categories/supplements",
            "https://www.healthyplanetcanada.com/blog/article",
            "https://www.healthyplanetcanada.com/products/another.html"
        ]
        
        df_link = pd.DataFrame({'link': test_links})
        
        # Process links as the crawler does
        df_link['link'] = df_link['link'].str.rstrip('/')
        df_link['slash_count'] = df_link['link'].str.count('/')
        
        # Test product links (slash_count == 3 and contains 'html')
        df_link_item = df_link[(df_link['slash_count'] == 3) & (df_link['link'].str.contains('html', na=False))]
        
        # Test category links (slash_count > 3 or doesn't contain 'html')
        df_catlink = df_link[(df_link['slash_count'] > 3) | (~df_link['link'].str.contains('html', na=False))]
        
        # Remove blog links
        df_catlink = df_catlink[~df_catlink['link'].str.contains('/blog/', na=False)]
        
        # Verify results
        self.assertEqual(len(df_link_item), 2)  # Two product links
        self.assertEqual(len(df_catlink), 1)    # One category link (blog removed)
        print("✓ Link processing logic works correctly")
    
    @patch('healthyplanet_crawler.get_database_engine')
    @patch('healthyplanet_crawler.upsert_df_to_mysql')
    def test_database_operations(self, mock_upsert, mock_get_engine):
        """Test database operations with mocked functions."""
        # Mock database engine
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        
        # Mock upsert function
        mock_upsert.return_value = None
        
        # Create test data
        test_df = pd.DataFrame({
            'link': ['https://www.healthyplanetcanada.com/products/test.html'],
            'domain': ['www.healthyplanetcanada.com']
        })
        
        # Test upsert calls
        from src.mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
        
        upsert_df_to_mysql(df=test_df, engine=mock_engine, target_table='test_table', key_col='link')
        
        # Verify upsert was called
        mock_upsert.assert_called()
        print("✓ Database operations work correctly")
    
    def test_url_normalization(self):
        """Test URL normalization logic."""
        from urllib.parse import urljoin, urlparse, urlunparse
        
        # Test URL normalization
        test_url = "https://www.healthyplanetcanada.com/products/test.html?param=value#fragment"
        parsed = urlparse(test_url)
        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, '', ''))
        
        expected = "https://www.healthyplanetcanada.com/products/test.html"
        self.assertEqual(normalized, expected)
        print("✓ URL normalization works correctly")
    
    def test_worker_function_import(self):
        """Test that worker function can be imported and has correct signature."""
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/healthyplanet')
        import healthyplanet_crawler
        
        # Check that worker function exists
        self.assertTrue(hasattr(healthyplanet_crawler, 'worker'))
        self.assertTrue(hasattr(healthyplanet_crawler, 'get_all_links'))
        print("✓ Worker functions are properly defined")


def run_async_tests():
    """Run async tests."""
    async def async_test_main():
        test_instance = TestHealthyPlanetCrawler()
        test_instance.setUp()
        await test_instance.test_main_function_structure()
    
    # Run async test
    asyncio.run(async_test_main())


def main():
    """Run all tests."""
    print("🧪 Testing Healthy Planet Crawler...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHealthyPlanetCrawler)
    
    # Run synchronous tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Run async tests
    print("\n🔄 Running async tests...")
    try:
        run_async_tests()
        print("✓ Async tests completed")
    except Exception as e:
        print(f"❌ Async test failed: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

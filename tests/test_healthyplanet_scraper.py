#!/usr/bin/env python3
"""
Test suite for Healthy Planet Scraper
Tests the core functionality without requiring database access or web requests
"""

import unittest
import sys
import os
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the path
sys.path.append("/home/mongreldatalab/mongrel_price_ticker/scripts/data_processing")
sys.path.append("/home/mongreldatalab/mongrel_price_ticker/scripts/data_processing")

from healthyplanet_scraper import HealthyPlanetScraper

class TestHealthyPlanetScraper(unittest.TestCase):
    """Test cases for HealthyPlanetScraper class"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scraper = HealthyPlanetScraper()
    
    def test_initialization(self):
        """Test scraper initialization"""
        self.assertIsNotNone(self.scraper)
        self.assertIsNotNone(self.scraper.proxy_config)
        self.assertIsNone(self.scraper.session)
        
        # Check proxy config structure
        expected_keys = ['host', 'port', 'username', 'password']
        for key in expected_keys:
            self.assertIn(key, self.scraper.proxy_config)
    
    def test_clean_url_basic(self):
        """Test basic URL cleaning functionality"""
        test_cases = [
            {
                'input': 'https://www.healthyplanetcanada.com/product/test?utm_source=google&utm_campaign=test',
                'expected': 'https://www.healthyplanetcanada.com/product/test'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/vitamins-supplements/?gclid=123&ref=test',
                'expected': 'https://www.healthyplanetcanada.com/vitamins-supplements'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/brand/test?fbclid=456&utm_medium=social',
                'expected': 'https://www.healthyplanetcanada.com/brand/test'
            },
            {
                'input': 'https://www.healthyplanetcanada.com//product//test//?utm_source=test',
                'expected': 'https://www.healthyplanetcanada.com/product/test'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/product/test#section',
                'expected': 'https://www.healthyplanetcanada.com/product/test'
            }
        ]
        
        for case in test_cases:
            with self.subTest(input_url=case['input']):
                result = self.scraper.clean_url(case['input'])
                self.assertEqual(result, case['expected'])
    
    def test_clean_url_tracking_parameters(self):
        """Test URL cleaning with various tracking parameters"""
        url_with_tracking = 'https://www.healthyplanetcanada.com/product/test?utm_source=google&utm_medium=cpc&utm_campaign=test&gclid=123&fbclid=456&ref=test&source=email&campaign=summer&affiliate=partner&uenc=encoded&___store=default&___from_store=old&___sid=session123&___from=homepage&SID=session456&PHPSESSID=php123&sessionid=session789&jsessionid=java123&v=1.0&version=2.0&timestamp=1234567890&t=1234567890&time=1234567890&redirect=home&return=cart&next=checkout&continue=shopping&fb_action_ids=123,456&fb_action_types=like,share&fb_source=timeline&mc_cid=mailchimp123&mc_eid=email456&hsCtaTracking=hubspot123&hsCtaTrackingId=tracking456&hsCtaTrackingData=data789&keep_this_param=important'
        
        result = self.scraper.clean_url(url_with_tracking)
        expected = 'https://www.healthyplanetcanada.com/product/test?keep_this_param=important'
        
        self.assertEqual(result, expected)
    
    def test_clean_url_edge_cases(self):
        """Test URL cleaning with edge cases"""
        test_cases = [
            {
                'input': 'https://www.healthyplanetcanada.com/',
                'expected': 'https://www.healthyplanetcanada.com'
            },
            {
                'input': 'https://www.healthyplanetcanada.com//',
                'expected': 'https://www.healthyplanetcanada.com'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/product/test/',
                'expected': 'https://www.healthyplanetcanada.com/product/test'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/product/test?',
                'expected': 'https://www.healthyplanetcanada.com/product/test'
            },
            {
                'input': 'https://www.healthyplanetcanada.com/product/test?param=value&',
                'expected': 'https://www.healthyplanetcanada.com/product/test?param=value'
            }
        ]
        
        for case in test_cases:
            with self.subTest(input_url=case['input']):
                result = self.scraper.clean_url(case['input'])
                self.assertEqual(result, case['expected'])
    
    def test_clean_url_error_handling(self):
        """Test URL cleaning error handling"""
        # Test with invalid URL
        invalid_url = "not-a-valid-url"
        result = self.scraper.clean_url(invalid_url)
        self.assertEqual(result, invalid_url)  # Should return original on error
    
    def test_create_dataframe(self):
        """Test DataFrame creation from links"""
        test_links = [
            'https://www.healthyplanetcanada.com/',
            'https://www.healthyplanetcanada.com/product/test1',
            'https://www.healthyplanetcanada.com/product/test2'
        ]
        
        df = self.scraper.create_dataframe(test_links)
        
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 3)
        self.assertEqual(list(df.columns), ['link'])
        self.assertEqual(df['link'].tolist(), test_links)
    
    def test_create_dataframe_empty(self):
        """Test DataFrame creation with empty links list"""
        df = self.scraper.create_dataframe([])
        self.assertIsNone(df)
        
        df = self.scraper.create_dataframe(None)
        self.assertIsNone(df)
    
    def test_filter_internal_links(self):
        """Test filtering to internal links only"""
        test_links = [
            'https://www.healthyplanetcanada.com/product/test1',
            'https://www.healthyplanetcanada.com/vitamins-supplements/',
            'https://www.google.com/search?q=test',
            'https://www.healthyplanetcanada.com/brand/test',
            'https://www.amazon.com/product/test',
            'https://www.healthyplanetcanada.com/'
        ]
        
        df_links = pd.DataFrame({'link': test_links})
        df_filtered = self.scraper.filter_internal_links(df_links)
        
        self.assertIsNotNone(df_filtered)
        self.assertEqual(len(df_filtered), 4)  # Only internal links
        
        # Check that all remaining links are internal
        for link in df_filtered['link']:
            self.assertIn('healthyplanetcanada.com', link)
    
    def test_filter_internal_links_empty(self):
        """Test filtering with empty DataFrame"""
        df_empty = pd.DataFrame({'link': []})
        df_filtered = self.scraper.filter_internal_links(df_empty)
        self.assertIsNone(df_filtered)
        
        df_filtered = self.scraper.filter_internal_links(None)
        self.assertIsNone(df_filtered)
    
    def test_cleanup_urls(self):
        """Test URL cleanup and deduplication"""
        test_links = [
            'https://www.healthyplanetcanada.com/product/test?utm_source=google',
            'https://www.healthyplanetcanada.com/product/test?utm_medium=cpc',
            'https://www.healthyplanetcanada.com/vitamins-supplements/',
            'https://www.healthyplanetcanada.com/vitamins-supplements/?utm_source=test'
        ]
        
        df_links = pd.DataFrame({'link': test_links})
        df_cleaned = self.scraper.cleanup_urls(df_links)
        
        self.assertIsNotNone(df_cleaned)
        # After cleaning, we should have 2 unique URLs (duplicates removed)
        self.assertEqual(len(df_cleaned), 2)
        
        # Check that tracking parameters are removed
        for link in df_cleaned['link']:
            self.assertNotIn('utm_source', link)
            self.assertNotIn('utm_medium', link)
    
    def test_cleanup_urls_empty(self):
        """Test cleanup with empty DataFrame"""
        df_cleaned = self.scraper.cleanup_urls(None)
        self.assertIsNone(df_cleaned)
    
    def test_prepare_for_upsert(self):
        """Test data preparation for database upsert"""
        test_links = [
            'https://www.healthyplanetcanada.com/product/test1',
            'https://www.healthyplanetcanada.com/product/test2'
        ]
        
        df_links = pd.DataFrame({'link': test_links})
        df_prepared = self.scraper.prepare_for_upsert(df_links)
        
        self.assertIsNotNone(df_prepared)
        self.assertEqual(len(df_prepared), 2)
        self.assertEqual(list(df_prepared.columns), ['link'])
        self.assertTrue(df_prepared.equals(df_links))
    
    def test_prepare_for_upsert_empty(self):
        """Test preparation with empty DataFrame"""
        df_prepared = self.scraper.prepare_for_upsert(None)
        self.assertIsNone(df_prepared)
        
        df_empty = pd.DataFrame({'link': []})
        df_prepared = self.scraper.prepare_for_upsert(df_empty)
        self.assertIsNone(df_prepared)
    
    @patch('healthyplanet_scraper.requests.Session')
    def test_create_session(self, mock_session_class):
        """Test session creation with mocked requests"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        result = self.scraper.create_session()
        
        self.assertEqual(result, mock_session)
        self.assertEqual(self.scraper.session, mock_session)
        
        # Verify session configuration
        mock_session.mount.assert_called()
        self.assertIsNotNone(mock_session.proxies)
        self.assertIsNotNone(mock_session.headers)
    
    @patch('healthyplanet_scraper.requests.Session')
    def test_test_proxy_connection_success(self, mock_session_class):
        """Test proxy connection test with successful response"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"origin": "192.168.1.1"}'
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        self.scraper.session = mock_session
        
        result = self.scraper.test_proxy_connection()
        
        self.assertTrue(result)
        mock_session.get.assert_called_once_with("http://httpbin.org/ip", timeout=15)
    
    @patch('healthyplanet_scraper.requests.Session')
    def test_test_proxy_connection_failure(self, mock_session_class):
        """Test proxy connection test with failed response"""
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = 'Error'
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        self.scraper.session = mock_session
        
        result = self.scraper.test_proxy_connection()
        
        self.assertFalse(result)
    
    @patch('healthyplanet_scraper.requests.Session')
    def test_test_proxy_connection_exception(self, mock_session_class):
        """Test proxy connection test with exception"""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")
        mock_session_class.return_value = mock_session
        
        self.scraper.session = mock_session
        
        result = self.scraper.test_proxy_connection()
        
        self.assertFalse(result)

class TestHealthyPlanetScraperIntegration(unittest.TestCase):
    """Integration tests for HealthyPlanetScraper"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.scraper = HealthyPlanetScraper()
    
    def test_url_processing_pipeline(self):
        """Test the complete URL processing pipeline"""
        # Test data
        raw_links = [
            'https://www.healthyplanetcanada.com/product/test1?utm_source=google&utm_campaign=test',
            'https://www.healthyplanetcanada.com/product/test1?utm_medium=cpc&utm_campaign=test2',
            'https://www.healthyplanetcanada.com/vitamins-supplements/?gclid=123',
            'https://www.google.com/search?q=test',  # External link
            'https://www.healthyplanetcanada.com/brand/test?fbclid=456',
            'https://www.healthyplanetcanada.com/'  # Homepage
        ]
        
        # Step 1: Create DataFrame
        df_links = self.scraper.create_dataframe(raw_links)
        self.assertIsNotNone(df_links)
        self.assertEqual(len(df_links), 6)
        
        # Step 2: Filter internal links
        df_internal = self.scraper.filter_internal_links(df_links)
        self.assertIsNotNone(df_internal)
        self.assertEqual(len(df_internal), 5)  # 5 internal links
        
        # Step 3: Clean URLs
        df_cleaned = self.scraper.cleanup_urls(df_internal)
        self.assertIsNotNone(df_cleaned)
        self.assertEqual(len(df_cleaned), 4)  # 4 unique links after cleaning
        
        # Step 4: Prepare for upsert
        df_prepared = self.scraper.prepare_for_upsert(df_cleaned)
        self.assertIsNotNone(df_prepared)
        self.assertEqual(len(df_prepared), 4)
        
        # Verify final result
        expected_links = [
            'https://www.healthyplanetcanada.com/product/test1',
            'https://www.healthyplanetcanada.com/vitamins-supplements',
            'https://www.healthyplanetcanada.com/brand/test',
            'https://www.healthyplanetcanada.com'
        ]
        
        actual_links = sorted(df_prepared['link'].tolist())
        expected_links = sorted(expected_links)
        
        self.assertEqual(actual_links, expected_links)

def run_tests():
    """Run all tests and return results"""
    print("🧪 Running Healthy Planet Scraper Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestHealthyPlanetScraper))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthyPlanetScraperIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

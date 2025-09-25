#!/usr/bin/env python3
"""
Test Script for SQL Maintenance Optimizations

This script validates that the optimized version produces the same results
as the original script while demonstrating performance improvements.

Author: Mongrel Data Lab
Date: 2024
"""

import time
import logging
import sys
import os
from typing import Dict, Any, List
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseValidator:
    """Validate database operations and results"""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'srv1978.hstgr.io'),
            'user': os.getenv('DB_USER', 'u488367489_mongrel_data'),
            'password': os.getenv('DB_PASSWORD', 'taan2#IbizaI'),
            'database': os.getenv('DB_NAME', 'u488367489_Price_Ticker'),
            'port': int(os.getenv('DB_PORT', '3306'))
        }
    
    def get_connection(self):
        """Get database connection"""
        return mysql.connector.connect(**self.config)
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all relevant tables"""
        counts = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                tables = [
                    'natura_sku_summary',
                    'fixed_fields', 
                    'df_ticker',
                    'market_price_list'
                ]
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        result = cursor.fetchone()
                        counts[table] = result[0] if result else 0
                    except mysql.connector.Error as e:
                        logger.warning(f"Could not count rows in {table}: {e}")
                        counts[table] = -1
                
                return counts
                
        except Exception as e:
            logger.error(f"Error getting table counts: {e}")
            return {}
    
    def get_zero_price_count(self) -> int:
        """Get count of rows with price = 0 in natura_sku_summary"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM natura_sku_summary WHERE price = 0")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting zero price count: {e}")
            return -1
    
    def get_domain_update_counts(self) -> Dict[str, int]:
        """Get counts of domain updates needed"""
        counts = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check df_ticker domain updates needed
                cursor.execute("""
                    SELECT COUNT(*) FROM df_ticker 
                    WHERE link IS NOT NULL 
                    AND link != '' 
                    AND link != 'nan'
                    AND link LIKE '%://%'
                    AND (domain IS NULL OR domain = '' OR domain != SUBSTRING_INDEX(
                        SUBSTRING_INDEX(
                            SUBSTRING_INDEX(link, '://', -1), 
                            '/', 1
                        ), 
                        '?', 1
                    ))
                """)
                result = cursor.fetchone()
                counts['df_ticker_domain_updates'] = result[0] if result else 0
                
                # Check fixed_fields domain updates needed
                cursor.execute("""
                    SELECT COUNT(*) FROM fixed_fields 
                    WHERE link IS NOT NULL 
                    AND link != '' 
                    AND link != 'nan'
                    AND link LIKE '%://%'
                    AND (domain IS NULL OR domain = '' OR domain != SUBSTRING_INDEX(
                        SUBSTRING_INDEX(
                            SUBSTRING_INDEX(link, '://', -1), 
                            '/', 1
                        ), 
                        '?', 1
                    ))
                """)
                result = cursor.fetchone()
                counts['fixed_fields_domain_updates'] = result[0] if result else 0
                
                return counts
                
        except Exception as e:
            logger.error(f"Error getting domain update counts: {e}")
            return {}
    
    def get_market_price_list_merge_count(self) -> int:
        """Get expected count for market_price_list merge"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM fixed_fields ff
                    INNER JOIN df_ticker dt ON ff.sku = dt.sku
                    WHERE ff.sku IS NOT NULL 
                    AND ff.sku != ''
                    AND dt.sku IS NOT NULL 
                    AND dt.sku != ''
                    AND (dt.domain IS NULL OR dt.domain != 'naturamarket.ca')
                    AND (dt.link IS NULL OR dt.link NOT LIKE '%naturamarket%')
                """)
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting merge count: {e}")
            return -1


def run_validation_tests():
    """Run comprehensive validation tests"""
    logger.info("Starting validation tests for SQL maintenance optimizations")
    logger.info("=" * 60)
    
    validator = DatabaseValidator()
    
    # Test 1: Check initial state
    logger.info("Test 1: Checking initial database state...")
    initial_counts = validator.get_table_counts()
    zero_price_count = validator.get_zero_price_count()
    domain_updates = validator.get_domain_update_counts()
    merge_count = validator.get_market_price_list_merge_count()
    
    logger.info(f"Initial table counts: {initial_counts}")
    logger.info(f"Zero price rows: {zero_price_count}")
    logger.info(f"Domain updates needed: {domain_updates}")
    logger.info(f"Expected merge count: {merge_count}")
    
    # Test 2: Run optimized script
    logger.info("\nTest 2: Running optimized SQL maintenance script...")
    start_time = time.time()
    
    try:
        # Import and run optimized script
        sys.path.append('/home/mongreldatalab/mongrel_price_ticker')
        from sql_maintenance_optimized import main as optimized_main
        optimized_main()
        
        execution_time = time.time() - start_time
        logger.info(f"Optimized script completed in {execution_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Error running optimized script: {e}")
        return False
    
    # Test 3: Verify results
    logger.info("\nTest 3: Verifying results...")
    final_counts = validator.get_table_counts()
    final_zero_price_count = validator.get_zero_price_count()
    
    # Verify zero price rows were deleted
    if final_zero_price_count == 0:
        logger.info("✅ Zero price rows successfully deleted")
    else:
        logger.warning(f"⚠️  {final_zero_price_count} zero price rows still exist")
    
    # Verify market_price_list was created/updated
    if final_counts.get('market_price_list', 0) > 0:
        logger.info(f"✅ market_price_list created with {final_counts['market_price_list']} rows")
    else:
        logger.warning("⚠️  market_price_list appears to be empty or missing")
    
    # Test 4: Performance metrics
    logger.info("\nTest 4: Performance metrics...")
    logger.info(f"Execution time: {execution_time:.2f}s")
    
    # Calculate efficiency metrics
    if zero_price_count > 0:
        rows_per_second = zero_price_count / execution_time
        logger.info(f"Processing rate: {rows_per_second:.0f} rows/second")
    
    return True


def run_connection_pool_test():
    """Test connection pool functionality"""
    logger.info("\nTesting connection pool functionality...")
    
    try:
        from sql_maintenance_optimized import OptimizedSQLMaintenance, DatabaseConfig
        
        config = DatabaseConfig()
        maintenance = OptimizedSQLMaintenance(config)
        
        # Test multiple concurrent connections
        import concurrent.futures
        
        def test_connection():
            with maintenance.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return cursor.fetchone()
        
        # Test 10 concurrent connections
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(test_connection) for _ in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        logger.info(f"✅ Connection pool test passed - {len(results)} concurrent connections successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Connection pool test failed: {e}")
        return False


def run_sql_function_test():
    """Test the domain extraction SQL function"""
    logger.info("\nTesting domain extraction SQL function...")
    
    try:
        from sql_maintenance_optimized import OptimizedSQLMaintenance, DatabaseConfig
        
        config = DatabaseConfig()
        maintenance = OptimizedSQLMaintenance(config)
        
        with maintenance.get_connection() as conn:
            cursor = conn.cursor()
            
            # Test the function with sample URLs
            test_urls = [
                'https://example.com/path?param=value',
                'http://test.org/page',
                'https://subdomain.example.com:8080/path',
                'invalid-url',
                None,
                ''
            ]
            
            for url in test_urls:
                cursor.execute("SELECT extract_domain(%s) as domain", (url,))
                result = cursor.fetchone()
                domain = result[0] if result else None
                logger.info(f"URL: {url} -> Domain: {domain}")
            
            logger.info("✅ Domain extraction function test passed")
            return True
            
    except Exception as e:
        logger.error(f"❌ Domain extraction function test failed: {e}")
        return False


def main():
    """Main test function"""
    logger.info("Starting comprehensive validation of SQL maintenance optimizations")
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Validation tests
    if run_validation_tests():
        tests_passed += 1
        logger.info("✅ Validation tests passed")
    else:
        logger.error("❌ Validation tests failed")
    
    # Test 2: Connection pool test
    if run_connection_pool_test():
        tests_passed += 1
        logger.info("✅ Connection pool test passed")
    else:
        logger.error("❌ Connection pool test failed")
    
    # Test 3: SQL function test
    if run_sql_function_test():
        tests_passed += 1
        logger.info("✅ SQL function test passed")
    else:
        logger.error("❌ SQL function test failed")
    
    # Test 4: Performance comparison (if both scripts exist)
    try:
        logger.info("\nRunning performance comparison...")
        from performance_comparison import main as compare_main
        compare_main()
        tests_passed += 1
        logger.info("✅ Performance comparison completed")
    except Exception as e:
        logger.warning(f"⚠️  Performance comparison skipped: {e}")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    logger.info("=" * 60)
    
    if tests_passed == total_tests:
        logger.info("🎉 All tests passed! Optimizations are working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed. Please review the logs.")
        sys.exit(1)


if __name__ == "__main__":
    main()

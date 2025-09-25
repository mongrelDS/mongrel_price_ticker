#!/usr/bin/env python3
"""
SQL Maintenance Script for Mongrel Price Ticker Database

This script performs maintenance operations on multiple tables:
1. Drop rows from natura_sku_summary where price is 0
2. Update domain column in df_ticker table based on link column using get_domain logic
3. SKIPPED: fixed_fields table (excluded due to persistent lock timeouts)
4. Create market_price_list by merging fixed_fields and df_ticker data

Author: Mongrel Data Lab
Date: 2024
"""

import mysql.connector
import logging
import sys
import os
import pandas as pd
from typing import List, Dict, Any, Tuple
from contextlib import contextmanager
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path to import get_domain function
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sql_maintenance.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration class"""
    def __init__(self):
        """Initialize database configuration from environment variables."""
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
        self.port = int(os.getenv('DB_PORT', '3306'))

        # Validate required credentials
        missing = [k for k, v in [('DB_HOST', self.host), ('DB_USER', self.user), ('DB_PASSWORD', self.password), ('DB_NAME', self.database)] if not v]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


class SQLMaintenance:
    """Main class for SQL maintenance operations"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=False
            )
            logger.info("Successfully connected to database")
            yield self.connection
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if self.connection and self.connection.is_connected():
                self.connection.close()
                logger.info("Database connection closed")
    
    def extract_domain_from_url(self, url: str) -> str:
        """
        Extract domain from URL using the same logic as get_domain function.
        
        Args:
            url (str): The URL to extract domain from
            
        Returns:
            str: The extracted domain
        """
        if not url or str(url).strip().lower() in ['nan', 'none', '']:
            return ''
        
        try:
            parsed = urlparse(str(url))
            return parsed.netloc
        except Exception as e:
            logger.warning(f"Error parsing URL '{url}': {e}")
            return ''
    
    def task1_drop_zero_price_rows(self) -> Dict[str, Any]:
        """
        Task 1: Drop rows from natura_sku_summary where price is 0
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 1: Drop rows from natura_sku_summary where price is 0")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, count how many rows will be affected
                count_query = "SELECT COUNT(*) FROM natura_sku_summary WHERE price = 0"
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_delete = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_delete} rows with price = 0 in natura_sku_summary")
                
                if rows_to_delete > 0:
                    # Delete the rows
                    delete_query = "DELETE FROM natura_sku_summary WHERE price = 0"
                    cursor.execute(delete_query)
                    affected_rows = cursor.rowcount
                    
                    logger.info(f"Successfully deleted {affected_rows} rows from natura_sku_summary")
                    
                    return {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': 'Dropped rows where price is 0'
                    }
                else:
                    logger.info("No rows found with price = 0 in natura_sku_summary")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No rows with price = 0 found'
                    }
                    
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 1: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to drop rows where price is 0'
            }
    
    def task2_update_fixed_fields_domain(self) -> Dict[str, Any]:
        """
        Task 2: Update domain column in fixed_fields table based on link column
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 2: Update domain column in fixed_fields table")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use a single SQL query to update domains using SUBSTRING_INDEX and REPLACE
                # This extracts the domain from the URL directly in SQL
                update_query = """
                UPDATE fixed_fields 
                SET domain = SUBSTRING_INDEX(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(link, '://', -1), 
                        '/', 1
                    ), 
                    '?', 1
                )
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
                """
                
                cursor.execute(update_query)
                affected_rows = cursor.rowcount
                
                logger.info(f"Successfully updated {affected_rows} domain values in fixed_fields")
                
                return {
                    'success': True,
                    'affected_rows': affected_rows,
                    'description': 'Updated domain column based on link column'
                }
                
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 2: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to update domain column in fixed_fields'
            }
    
    def task3_update_df_ticker_domain(self) -> Dict[str, Any]:
        """
        Task 3: Update domain column in df_ticker table based on link column
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 3: Update domain column in df_ticker table")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use a single SQL query to update domains using SUBSTRING_INDEX and REPLACE
                # This extracts the domain from the URL directly in SQL
                update_query = """
                UPDATE df_ticker 
                SET domain = SUBSTRING_INDEX(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(link, '://', -1), 
                        '/', 1
                    ), 
                    '?', 1
                )
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
                """
                
                cursor.execute(update_query)
                affected_rows = cursor.rowcount
                
                logger.info(f"Successfully updated {affected_rows} domain values in df_ticker")
                
                return {
                    'success': True,
                    'affected_rows': affected_rows,
                    'description': 'Updated domain column based on link column'
                }
                
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 3: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to update domain column in df_ticker'
            }
    
    def create_market_price_list_table(self, cursor) -> bool:
        """
        Create the market_price_list table if it doesn't exist
        
        Returns:
            bool: True if table was created or already exists, False on error
        """
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS market_price_list (
                sku VARCHAR(255) PRIMARY KEY,
                brand TEXT,
                title TEXT,
                barcode TEXT,
                vol TEXT,
                keywords TEXT,
                imgurl TEXT,
                price DOUBLE,
                tag TEXT,
                link TEXT,
                domain TEXT,
                `key` VARCHAR(255),
                date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_query)
            logger.info("market_price_list table created or already exists")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating market_price_list table: {e}")
            return False

    def task4_create_market_price_list(self) -> Dict[str, Any]:
        """
        Task 4: Create market_price_list by merging fixed_fields and df_ticker data
        
        Steps:
        1. Create market_price_list table if it doesn't exist
        2. Get df_fixed_fields from fixed_fields table (drop domain, link columns)
        3. Get df_price_30d from df_ticker table
        4. Merge on sku with inner join
        5. Upsert to market_price_list table with sku as key
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 4: Create market_price_list by merging fixed_fields and df_ticker")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Step 1: Create market_price_list table if it doesn't exist
                logger.info("Ensuring market_price_list table exists...")
                if not self.create_market_price_list_table(cursor):
                    return {
                        'success': False,
                        'error': 'Failed to create market_price_list table',
                        'description': 'Could not create required table'
                    }
                
                # Step 2: Get df_fixed_fields from fixed_fields table (excluding domain, link columns)
                logger.info("Fetching data from fixed_fields table...")
                fixed_fields_query = """
                SELECT sku, brand, title, barcode, vol, keywords, imgurl
                FROM fixed_fields
                WHERE sku IS NOT NULL AND sku != ''
                """
                cursor.execute(fixed_fields_query)
                fixed_fields_data = cursor.fetchall()
                
                # Get column names for fixed_fields
                fixed_fields_columns = [desc[0] for desc in cursor.description]
                df_fixed_fields = pd.DataFrame(fixed_fields_data, columns=fixed_fields_columns)
                
                logger.info(f"Retrieved {len(df_fixed_fields)} records from fixed_fields")
                
                # Step 3: Get df_price_30d from df_ticker table (excluding naturamarket links)
                logger.info("Fetching data from df_ticker table (excluding naturamarket links)...")
                ticker_query = """
                SELECT sku, price, tag, link, domain, `key`, date
                FROM df_ticker
                WHERE sku IS NOT NULL AND sku != ''
                AND (domain IS NULL OR domain != 'naturamarket.ca')
                AND (link IS NULL OR link NOT LIKE '%naturamarket%')
                """
                cursor.execute(ticker_query)
                ticker_data = cursor.fetchall()
                
                # Get column names for df_ticker
                ticker_columns = [desc[0] for desc in cursor.description]
                df_price_30d = pd.DataFrame(ticker_data, columns=ticker_columns)
                
                logger.info(f"Retrieved {len(df_price_30d)} records from df_ticker")
                
                # Step 4: Merge df_fixed_fields and df_price_30d on sku with inner join
                logger.info("Merging dataframes on sku...")
                df_market_price_list = pd.merge(
                    df_fixed_fields, 
                    df_price_30d, 
                    on='sku', 
                    how='inner',
                    suffixes=('_fixed', '_ticker')
                )
                
                logger.info(f"Merged data contains {len(df_market_price_list)} records")
                
                if len(df_market_price_list) == 0:
                    logger.warning("No matching records found between fixed_fields and df_ticker")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No matching records to merge'
                    }
                
                # Step 5: Prepare data for upsert to market_price_list table
                logger.info("Preparing data for upsert to market_price_list table...")
                
                # Create the upsert query
                upsert_query = """
                INSERT INTO market_price_list (
                    sku, brand, title, barcode, vol, keywords, imgurl,
                    price, tag, link, domain, `key`, date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    brand = VALUES(brand),
                    title = VALUES(title),
                    barcode = VALUES(barcode),
                    vol = VALUES(vol),
                    keywords = VALUES(keywords),
                    imgurl = VALUES(imgurl),
                    price = VALUES(price),
                    tag = VALUES(tag),
                    link = VALUES(link),
                    domain = VALUES(domain),
                    `key` = VALUES(`key`),
                    date = VALUES(date)
                """
                
                # Prepare data for insertion
                upsert_data = []
                for _, row in df_market_price_list.iterrows():
                    upsert_data.append((
                        row['sku'],
                        row.get('brand', None),
                        row.get('title', None),
                        row.get('barcode', None),
                        row.get('vol', None),
                        row.get('keywords', None),
                        row.get('imgurl', None),
                        row.get('price', None),
                        row.get('tag', None),
                        row.get('link', None),
                        row.get('domain', None),
                        row.get('key', None),
                        row.get('date', None)
                    ))
                
                # Execute upsert in smaller batches with connection retry logic
                batch_size = 100  # Much smaller batch size
                total_affected_rows = 0
                max_retries = 3
                
                logger.info(f"Processing {len(upsert_data)} records in batches of {batch_size}")
                
                for i in range(0, len(upsert_data), batch_size):
                    batch = upsert_data[i:i + batch_size]
                    success = False
                    
                    for retry in range(max_retries):
                        try:
                            cursor.executemany(upsert_query, batch)
                            batch_affected = cursor.rowcount
                            total_affected_rows += batch_affected
                            success = True
                            break
                            
                        except mysql.connector.Error as e:
                            if retry < max_retries - 1:
                                logger.warning(f"Retry {retry + 1}/{max_retries} for batch {i//batch_size + 1}: {e}")
                                # Reconnect for retry
                                try:
                                    conn.close()
                                    conn = mysql.connector.connect(
                                        host=self.config.host,
                                        port=self.config.port,
                                        user=self.config.user,
                                        password=self.config.password,
                                        database=self.config.database,
                                        autocommit=False
                                    )
                                    cursor = conn.cursor()
                                except:
                                    pass
                                continue
                            else:
                                logger.error(f"Failed to process batch {i//batch_size + 1} after {max_retries} retries: {e}")
                                break
                    
                    if not success:
                        logger.warning(f"Skipping batch {i//batch_size + 1} due to persistent errors")
                        continue
                    
                    if (i // batch_size + 1) % 50 == 0:  # Log every 50 batches
                        logger.info(f"Processed {i + len(batch)}/{len(upsert_data)} records")
                
                affected_rows = total_affected_rows
                
                logger.info(f"Successfully upserted {affected_rows} records to market_price_list")
                
                return {
                    'success': True,
                    'affected_rows': affected_rows,
                    'description': 'Created market_price_list by merging fixed_fields and df_ticker'
                }
                
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 4: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to create market_price_list'
            }
        except Exception as e:
            error_msg = f"Unexpected error in Task 4: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to create market_price_list due to unexpected error'
            }
    
    def run_all_maintenance_tasks(self) -> Dict[str, Any]:
        """Run all maintenance tasks and return results"""
        
        logger.info("Starting SQL maintenance process")
        logger.info("=" * 60)
        logger.info("NOTE: fixed_fields table excluded due to persistent lock timeouts")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Task 1: Drop rows from natura_sku_summary where price is 0
                logger.info("\n" + "=" * 40)
                logger.info("TASK 1: Drop zero price rows from natura_sku_summary")
                logger.info("=" * 40)
                task1_result = self.task1_drop_zero_price_rows()
                results['task1_natura_sku_summary'] = task1_result
                
                # Task 2: Update domain in df_ticker table
                logger.info("\n" + "=" * 40)
                logger.info("TASK 2: Update domain in df_ticker table")
                logger.info("=" * 40)
                task2_result = self.task3_update_df_ticker_domain()
                results['task2_df_ticker'] = task2_result
                
                # Skip fixed_fields due to lock timeouts
                logger.info("\n" + "=" * 40)
                logger.info("TASK 3: SKIPPED - fixed_fields table (lock timeouts)")
                logger.info("=" * 40)
                results['task3_fixed_fields'] = {
                    'success': False,
                    'skipped': True,
                    'reason': 'Table experiencing persistent lock timeouts',
                    'description': 'Skipped due to concurrent access issues'
                }
                
                # Task 4: Create market_price_list by merging fixed_fields and df_ticker
                logger.info("\n" + "=" * 40)
                logger.info("TASK 4: Create market_price_list by merging fixed_fields and df_ticker")
                logger.info("=" * 40)
                task4_result = self.task4_create_market_price_list()
                results['task4_market_price_list'] = task4_result
                
                # Commit all changes
                conn.commit()
                logger.info("\nAll changes committed successfully")
                
                cursor.close()
                
        except Exception as e:
            logger.error(f"Error during maintenance process: {e}")
            results['error'] = str(e)
        
        return results
    
    def log_summary(self, results: Dict[str, Any]):
        """Log a summary of all maintenance tasks"""
        logger.info("\n" + "=" * 60)
        logger.info("MAINTENANCE SUMMARY")
        logger.info("=" * 60)
        
        for task_name, result in results.items():
            if task_name == 'error':
                logger.error(f"❌ Process Error: {result}")
                continue
                
            if result.get('skipped', False):
                logger.warning(f"⏭️  {task_name}: SKIPPED - {result.get('reason', 'Unknown reason')}")
            elif result['success']:
                logger.info(f"✅ {task_name}: {result['affected_rows']} rows affected - {result['description']}")
            else:
                logger.error(f"❌ {task_name}: FAILED - {result.get('error', 'Unknown error')}")
        
        logger.info("=" * 60)


def main():
    """Main function"""
    try:
        # Initialize database configuration from environment variables
        config = DatabaseConfig()
        
        # Create maintenance instance and run
        maintenance = SQLMaintenance(config)
        results = maintenance.run_all_maintenance_tasks()
        
        # Log summary
        maintenance.log_summary(results)
        
        # Check if all tasks succeeded
        all_success = all(
            result.get('success', False) 
            for task_name, result in results.items() 
            if task_name != 'error'
        )
        
        if all_success:
            logger.info("All maintenance tasks completed successfully")
            sys.exit(0)
        else:
            logger.error("Some maintenance tasks failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Maintenance interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

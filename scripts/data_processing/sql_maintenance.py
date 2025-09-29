#!/usr/bin/env python3
"""
SQL Maintenance Script for Mongrel Price Ticker Database

This script performs maintenance operations on multiple tables:
1. Drop rows from natura_sku_summary where price is 0
2. Drop rows from natura_sku_summary where price < 0.1
3. Update domain column in fixed_fields table based on link column using get_domain logic
4. Drop rows from df_ticker where price is 0
5. Update domain column in df_ticker table based on link column using get_domain logic
6. Drop rows from fixed_fields where title column is null
7. Update SKU from barcode in fixed_fields where SKU length < 4 and barcode length > 4

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

# Note: get_price_30d logic is implemented directly in task8_create_market_price_list

# Load environment variables
load_dotenv()

# Add src directory to path to import get_domain function
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import generate_key function
from generate_key import generate_key

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
                    
                    # Commit the changes
                    conn.commit()
                    
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
    
    def task2_drop_low_price_rows_natura_sku_summary(self) -> Dict[str, Any]:
        """
        Task 2: Drop rows from natura_sku_summary where price < 0.1
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 2: Drop rows from natura_sku_summary where price < 0.1")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, count how many rows will be affected
                count_query = "SELECT COUNT(*) FROM natura_sku_summary WHERE price < 0.1"
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_delete = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_delete} rows with price < 0.1 in natura_sku_summary")
                
                if rows_to_delete > 0:
                    # Delete the rows
                    delete_query = "DELETE FROM natura_sku_summary WHERE price < 0.1"
                    cursor.execute(delete_query)
                    affected_rows = cursor.rowcount
                    
                    # Commit the changes
                    conn.commit()
                    
                    logger.info(f"Successfully deleted {affected_rows} rows from natura_sku_summary")
                    
                    return {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': 'Dropped rows where price < 0.1'
                    }
                else:
                    logger.info("No rows found with price < 0.1 in natura_sku_summary")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No rows with price < 0.1 found'
                    }
                    
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 2: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to drop rows where price < 0.1'
            }

    def task3_update_fixed_fields_domain(self) -> Dict[str, Any]:
        """
        Task 3: Update domain column in fixed_fields table based on link column
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 3: Update domain column in fixed_fields table")
        
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
    
    def task4_drop_zero_price_rows_df_ticker(self) -> Dict[str, Any]:
        """
        Task 4: Drop rows from df_ticker where price is 0
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 4: Drop rows from df_ticker where price is 0")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, count how many rows will be affected
                count_query = "SELECT COUNT(*) FROM df_ticker WHERE price = 0"
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_delete = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_delete} rows with price = 0 in df_ticker")
                
                if rows_to_delete > 0:
                    # Delete the rows
                    delete_query = "DELETE FROM df_ticker WHERE price = 0"
                    cursor.execute(delete_query)
                    affected_rows = cursor.rowcount
                    
                    # Commit the changes
                    conn.commit()
                    
                    logger.info(f"Successfully deleted {affected_rows} rows from df_ticker")
                    
                    return {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': 'Dropped rows where price is 0'
                    }
                else:
                    logger.info("No rows found with price = 0 in df_ticker")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No rows with price = 0 found'
                    }
                    
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 3: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to drop rows where price is 0'
            }

    def task5_update_df_ticker_domain(self) -> Dict[str, Any]:
        """
        Task 5: Update domain column in df_ticker table based on link column
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 5: Update domain column in df_ticker table")
        
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
    

    def task6_drop_null_title_rows(self) -> Dict[str, Any]:
        """
        Task 6: Drop rows from fixed_fields where title column is null
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 6: Drop rows from fixed_fields where title is null")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, count how many rows will be affected
                count_query = "SELECT COUNT(*) FROM fixed_fields WHERE title IS NULL"
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_delete = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_delete} rows with null title in fixed_fields")
                
                if rows_to_delete > 0:
                    # Delete the rows
                    delete_query = "DELETE FROM fixed_fields WHERE title IS NULL"
                    cursor.execute(delete_query)
                    affected_rows = cursor.rowcount
                    
                    # Commit the changes
                    conn.commit()
                    
                    logger.info(f"Successfully deleted {affected_rows} rows from fixed_fields")
                    
                    return {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': 'Dropped rows where title is null'
                    }
                else:
                    logger.info("No rows found with null title in fixed_fields")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No rows with null title found'
                    }
                    
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 4: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to drop rows where title is null'
            }

    def task7_update_sku_from_barcode(self) -> Dict[str, Any]:
        """
        Task 7: Update SKU from barcode in fixed_fields table
        
        For rows where:
        - SKU string length < 4 AND barcode string length > 4, OR
        - SKU is null AND barcode string length > 4
        Copy the barcode value to the SKU field
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 7: Update SKU from barcode in fixed_fields table")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, count how many rows will be affected
                count_query = """
                SELECT COUNT(*) FROM fixed_fields 
                WHERE (
                    (CHAR_LENGTH(sku) < 4 AND CHAR_LENGTH(barcode) > 4 AND sku IS NOT NULL AND sku != '') 
                    OR 
                    (sku IS NULL AND CHAR_LENGTH(barcode) > 4)
                )
                AND barcode IS NOT NULL 
                AND barcode != ''
                """
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_update = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_update} rows where (SKU length < 4 and barcode length > 4) OR (SKU is null and barcode length > 4)")
                
                if rows_to_update > 0:
                    # Update the rows
                    update_query = """
                    UPDATE fixed_fields 
                    SET sku = barcode
                    WHERE (
                        (CHAR_LENGTH(sku) < 4 AND CHAR_LENGTH(barcode) > 4 AND sku IS NOT NULL AND sku != '') 
                        OR 
                        (sku IS NULL AND CHAR_LENGTH(barcode) > 4)
                    )
                    AND barcode IS NOT NULL 
                    AND barcode != ''
                    """
                    cursor.execute(update_query)
                    affected_rows = cursor.rowcount
                    
                    # Commit the changes
                    conn.commit()
                    
                    logger.info(f"Successfully updated {affected_rows} SKU values from barcode in fixed_fields")
                    
                    return {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': 'Updated SKU from barcode where (SKU length < 4 and barcode length > 4) OR (SKU is null and barcode length > 4)'
                    }
                else:
                    logger.info("No rows found matching SKU/barcode criteria in fixed_fields")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No rows found matching SKU/barcode criteria'
                    }
                    
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 5: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to update SKU from barcode'
            }

    def create_price_30d_avg_table(self, cursor) -> bool:
        """
        Create the price_30d_avg table if it doesn't exist
        
        Returns:
            bool: True if table was created or already exists, False on error
        """
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS price_30d_avg (
                link_key VARCHAR(13) PRIMARY KEY,
                link TEXT,
                domain VARCHAR(255),
                price_30d_avg DOUBLE,
                high DOUBLE,
                low DOUBLE,
                latest_price DOUBLE,
                latest_date DATE,
                record_count INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_query)
            logger.info("price_30d_avg table created or already exists")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating price_30d_avg table: {e}")
            return False

    def task8_create_price_30d_avg_table(self) -> Dict[str, Any]:
        """
        Task 8: Create price_30d_avg table with 30-day price analysis from df_ticker data
        
        Steps:
        1. Create price_30d_avg table if it doesn't exist
        2. Process df_ticker data with 30-day price analysis for all domains
        3. Calculate price_30d_avg, high, low, latest_price, latest_date, record_count
        4. Upsert to price_30d_avg table with link as key
        
        Returns:
            Dict containing success status and affected rows count
        """
        logger.info("Starting Task 8: Create price_30d_avg table with 30-day price analysis")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Step 1: Create price_30d_avg table if it doesn't exist
                logger.info("Ensuring price_30d_avg table exists...")
                if not self.create_price_30d_avg_table(cursor):
                    return {
                        'success': False,
                        'error': 'Failed to create price_30d_avg table',
                        'description': 'Could not create required table'
                    }
                
                # Step 2: Process df_ticker data with 30-day price analysis
                logger.info("Processing df_ticker data with 30-day price analysis...")
                
                # Get all unique domains from df_ticker (excluding naturamarket)
                domain_query = """
                SELECT DISTINCT domain 
                FROM df_ticker 
                WHERE domain IS NOT NULL 
                AND domain != 'naturamarket.ca'
                AND domain != ''
                """
                cursor.execute(domain_query)
                domains = [row[0] for row in cursor.fetchall()]
                
                logger.info(f"Found {len(domains)} domains to process: {domains}")
                
                # Process each domain and combine results
                all_price_data = []
                for domain in domains:
                    logger.info(f"Processing domain: {domain}")
                    try:
                        # Get data for this domain with 30-day analysis
                        domain_query = """
                        SELECT link, price, date, domain
                        FROM df_ticker
                        WHERE domain = %s
                        AND price > 0
                        AND link IS NOT NULL 
                        AND link != ''
                        ORDER BY link, date
                        """
                        cursor.execute(domain_query, (domain,))
                        domain_data = cursor.fetchall()
                        
                        if not domain_data:
                            logger.warning(f"No data found for domain: {domain}")
                            continue
                        
                        # Convert to DataFrame
                        df_domain = pd.DataFrame(domain_data, columns=['link', 'price', 'date', 'domain'])
                        df_domain['date'] = pd.to_datetime(df_domain['date'])
                        
                        # Calculate 30-day stats for each link
                        def calculate_stats(group):
                            # Get 30 days ago
                            thirty_days_ago = pd.Timestamp.now() - pd.Timedelta(days=30)
                            
                            # Filter to last 30 days
                            recent_data = group[group['date'] >= thirty_days_ago]
                            
                            # Get latest entry
                            latest_entry = group.sort_values('date').iloc[-1]
                            
                            return pd.Series({
                                'high': group['price'].max(),
                                'low': group['price'].min(),
                                'price_30d_avg': recent_data['price'].mean() if not recent_data.empty else None,
                                'latest_price': latest_entry['price'],
                                'latest_date': latest_entry['date'],
                                'record_count': len(group)
                            })
                        
                        # Calculate stats for each link
                        stats = df_domain.groupby('link').apply(calculate_stats, include_groups=False).reset_index()
                        
                        # Add domain column
                        stats['domain'] = domain
                        
                        # Select and reorder columns
                        df_domain_processed = stats[['link', 'domain', 'price_30d_avg', 'high', 'low', 'latest_price', 'latest_date', 'record_count']].copy()
                        
                        all_price_data.append(df_domain_processed)
                        logger.info(f"Processed {len(df_domain_processed)} records for {domain}")
                        
                    except Exception as e:
                        logger.error(f"Error processing domain {domain}: {e}")
                        continue
                
                if not all_price_data:
                    logger.error("No price data processed from any domain")
                    return {
                        'success': False,
                        'error': 'No price data processed from any domain',
                        'description': 'Failed to process df_ticker data'
                    }
                
                # Combine all domain data
                df_price_30d = pd.concat(all_price_data, ignore_index=True)
                logger.info(f"Combined data contains {len(df_price_30d)} records from all domains")
                
                if len(df_price_30d) == 0:
                    logger.warning("No price data to process")
                    return {
                        'success': True,
                        'affected_rows': 0,
                        'description': 'No price data to process'
                    }
                
                # Generate link_key using generate_key function
                logger.info("Generating link_key for all records...")
                df_price_30d = generate_key(
                    df_price_30d, 
                    deduplication_columns=['link'], 
                    key_col='link_key'
                )
                logger.info(f"Generated link_key for {len(df_price_30d)} records")
                
                # Step 3: Prepare data for upsert to price_30d_avg table
                logger.info("Preparing data for upsert to price_30d_avg table...")
                
                # Create the upsert query
                upsert_query = """
                INSERT INTO price_30d_avg (
                    link_key, link, domain, price_30d_avg, high, low, latest_price, latest_date, record_count
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    link = VALUES(link),
                    domain = VALUES(domain),
                    price_30d_avg = VALUES(price_30d_avg),
                    high = VALUES(high),
                    low = VALUES(low),
                    latest_price = VALUES(latest_price),
                    latest_date = VALUES(latest_date),
                    record_count = VALUES(record_count)
                """
                
                # Prepare data for insertion with proper NaN handling
                upsert_data = []
                for _, row in df_price_30d.iterrows():
                    # Helper function to convert NaN to None
                    def safe_value(value):
                        if pd.isna(value) or value == 'nan' or str(value).lower() == 'nan':
                            return None
                        return value
                    
                    upsert_data.append((
                        safe_value(row['link_key']),
                        safe_value(row['link']),
                        safe_value(row['domain']),
                        safe_value(row['price_30d_avg']),
                        safe_value(row['high']),
                        safe_value(row['low']),
                        safe_value(row['latest_price']),
                        safe_value(row['latest_date']),
                        safe_value(row['record_count'])
                    ))
                
                # Execute upsert in smaller batches
                batch_size = 100
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
                
                # Commit the changes
                conn.commit()
                affected_rows = total_affected_rows
                
                logger.info(f"Successfully upserted {affected_rows} records to price_30d_avg")
                
                return {
                    'success': True,
                    'affected_rows': affected_rows,
                    'description': 'Created price_30d_avg table with 30-day price analysis'
                }
                
        except mysql.connector.Error as e:
            error_msg = f"Error in Task 8: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to create price_30d_avg table'
            }
        except Exception as e:
            error_msg = f"Unexpected error in Task 8: {e}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': str(e),
                'description': 'Failed to create price_30d_avg table due to unexpected error'
            }


    
    def run_all_maintenance_tasks(self) -> Dict[str, Any]:
        """Run all maintenance tasks and return results"""
        
        logger.info("Starting SQL maintenance process")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Task 1: Drop rows from natura_sku_summary where price is 0
            logger.info("\n" + "=" * 40)
            logger.info("TASK 1: Drop zero price rows from natura_sku_summary")
            logger.info("=" * 40)
            task1_result = self.task1_drop_zero_price_rows()
            results['task1_natura_sku_summary'] = task1_result
            
            # Task 2: Drop rows from natura_sku_summary where price < 0.1
            logger.info("\n" + "=" * 40)
            logger.info("TASK 2: Drop rows from natura_sku_summary where price < 0.1")
            logger.info("=" * 40)
            task2_result = self.task2_drop_low_price_rows_natura_sku_summary()
            results['task2_natura_sku_summary_low_price'] = task2_result
            
            # Task 3: Update domain in fixed_fields table
            logger.info("\n" + "=" * 40)
            logger.info("TASK 3: Update domain in fixed_fields table")
            logger.info("=" * 40)
            task3_result = self.task3_update_fixed_fields_domain()
            results['task3_fixed_fields_domain'] = task3_result
            
            # Task 4: Drop rows from df_ticker where price is 0
            logger.info("\n" + "=" * 40)
            logger.info("TASK 4: Drop rows from df_ticker where price is 0")
            logger.info("=" * 40)
            task4_result = self.task4_drop_zero_price_rows_df_ticker()
            results['task4_df_ticker_zero_price'] = task4_result
            
            # Task 5: Update domain in df_ticker table
            logger.info("\n" + "=" * 40)
            logger.info("TASK 5: Update domain in df_ticker table")
            logger.info("=" * 40)
            task5_result = self.task5_update_df_ticker_domain()
            results['task5_df_ticker_domain'] = task5_result
            
            # Task 6: Drop rows from fixed_fields where title is null
            logger.info("\n" + "=" * 40)
            logger.info("TASK 6: Drop rows from fixed_fields where title is null")
            logger.info("=" * 40)
            task6_result = self.task6_drop_null_title_rows()
            results['task6_fixed_fields_null_title'] = task6_result
            
            # Task 7: Update SKU from barcode in fixed_fields
            logger.info("\n" + "=" * 40)
            logger.info("TASK 7: Update SKU from barcode in fixed_fields")
            logger.info("=" * 40)
            task7_result = self.task7_update_sku_from_barcode()
            results['task7_fixed_fields_sku_barcode'] = task7_result
            
            # Task 8: Create price_30d_avg table with 30-day price analysis
            logger.info("\n" + "=" * 40)
            logger.info("TASK 8: Create price_30d_avg table with 30-day price analysis")
            logger.info("=" * 40)
            task8_result = self.task8_create_price_30d_avg_table()
            results['task8_price_30d_avg'] = task8_result
            
            logger.info("\nAll tasks completed successfully")
                
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

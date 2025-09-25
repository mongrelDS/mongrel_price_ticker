#!/usr/bin/env python3
"""
Robust SQL Maintenance Script for Mongrel Price Ticker Database

This version handles database constraints better with:
1. Proper timeout handling
2. Query optimization for large datasets
3. Better lock management
4. Chunked processing for large operations

Author: Mongrel Data Lab
Date: 2024
"""

import mysql.connector
from mysql.connector import pooling
import logging
import sys
import os
import asyncio
import concurrent.futures
from typing import List, Dict, Any, Tuple, Optional
from contextlib import contextmanager
from urllib.parse import urlparse
from dotenv import load_dotenv
import time
from dataclasses import dataclass
from enum import Enum

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sql_maintenance_robust.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    task_name: str
    status: TaskStatus
    affected_rows: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    description: str = ""


class DatabaseConfig:
    """Enhanced database configuration with robust connection handling"""
    
    def __init__(self):
        """Initialize database configuration from environment variables."""
        self.host = os.getenv('DB_HOST')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME')
        self.port = int(os.getenv('DB_PORT', '3306'))

        # Validate required credentials to avoid using insecure defaults
        missing = [k for k, v in [('DB_HOST', self.host), ('DB_USER', self.user), ('DB_PASSWORD', self.password), ('DB_NAME', self.database)] if not v]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        # Connection pool configuration
        self.pool_name = 'robust_maintenance_pool'
        self.pool_size = 3  # Reduced pool size to avoid lock contention
        self.pool_reset_session = True
        self.autocommit = False
        
        # Timeout configuration
        self.connection_timeout = 60
        self.query_timeout = 300  # 5 minutes
        self.lock_wait_timeout = 30  # 30 seconds
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2.0


class RobustSQLMaintenance:
    """Robust SQL maintenance operations with better constraint handling"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self._initialize_connection_pool()
    
    def _initialize_connection_pool(self):
        """Initialize MySQL connection pool with robust settings"""
        try:
            pool_config = {
                'pool_name': self.config.pool_name,
                'pool_size': self.config.pool_size,
                'pool_reset_session': self.config.pool_reset_session,
                'host': self.config.host,
                'port': self.config.port,
                'user': self.config.user,
                'password': self.config.password,
                'database': self.config.database,
                'autocommit': self.config.autocommit,
                'connection_timeout': self.config.connection_timeout,
                'charset': 'utf8mb4',
                'use_unicode': True,
                'sql_mode': 'TRADITIONAL',
                'init_command': "SET SESSION wait_timeout=28800, interactive_timeout=28800"
            }
            
            self.pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Robust connection pool initialized with {self.config.pool_size} connections")
            
        except mysql.connector.Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with timeout handling"""
        connection = None
        try:
            connection = self.pool.get_connection()
            
            # Set session variables for better timeout handling
            cursor = connection.cursor()
            cursor.execute(f"SET SESSION lock_wait_timeout = {self.config.lock_wait_timeout}")
            cursor.execute(f"SET SESSION wait_timeout = {self.config.connection_timeout}")
            cursor.execute("SET SESSION sql_mode = 'TRADITIONAL'")
            cursor.close()
            
            logger.debug("Retrieved connection from pool with timeout settings")
            yield connection
            
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Returned connection to pool")
    
    def create_domain_extraction_function(self, cursor) -> bool:
        """Create a MySQL function for domain extraction"""
        try:
            create_function_sql = """
            CREATE FUNCTION IF NOT EXISTS extract_domain(url TEXT) 
            RETURNS VARCHAR(255)
            DETERMINISTIC
            READS SQL DATA
            BEGIN
                DECLARE domain VARCHAR(255);
                IF url IS NULL OR url = '' OR url = 'nan' THEN
                    RETURN '';
                END IF;
                
                SET domain = SUBSTRING_INDEX(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(url, '://', -1), 
                        '/', 1
                    ), 
                    '?', 1
                );
                
                RETURN domain;
            END
            """
            
            cursor.execute(create_function_sql)
            logger.info("Domain extraction function created successfully")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating domain extraction function: {e}")
            return False
    
    def task1_drop_zero_price_rows(self) -> TaskResult:
        """Task 1: Drop rows from natura_sku_summary where price is 0"""
        start_time = time.time()
        logger.info("Starting Task 1: Drop rows from natura_sku_summary where price is 0")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Count rows to be deleted
                count_query = "SELECT COUNT(*) FROM natura_sku_summary WHERE price = 0"
                cursor.execute(count_query)
                count_result = cursor.fetchone()
                rows_to_delete = count_result[0] if count_result else 0
                
                logger.info(f"Found {rows_to_delete} rows with price = 0 in natura_sku_summary")
                
                if rows_to_delete > 0:
                    # Delete rows in smaller batches to avoid locks
                    delete_query = "DELETE FROM natura_sku_summary WHERE price = 0 LIMIT 100"
                    total_deleted = 0
                    batch_count = 0
                    
                    while True:
                        batch_count += 1
                        cursor.execute(delete_query)
                        deleted_count = cursor.rowcount
                        total_deleted += deleted_count
                        
                        if deleted_count == 0:
                            break
                        
                        conn.commit()  # Commit each batch
                        logger.debug(f"Batch {batch_count}: Deleted {deleted_count} rows, total: {total_deleted}")
                        
                        # Small delay to reduce lock contention
                        time.sleep(0.1)
                    
                    execution_time = time.time() - start_time
                    logger.info(f"Successfully deleted {total_deleted} rows in {execution_time:.2f}s")
                    
                    return TaskResult(
                        task_name="drop_zero_price_rows",
                        status=TaskStatus.COMPLETED,
                        affected_rows=total_deleted,
                        execution_time=execution_time,
                        description="Dropped rows where price is 0"
                    )
                else:
                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_name="drop_zero_price_rows",
                        status=TaskStatus.COMPLETED,
                        affected_rows=0,
                        execution_time=execution_time,
                        description="No rows with price = 0 found"
                    )
                    
        except mysql.connector.Error as e:
            execution_time = time.time() - start_time
            error_msg = f"Error in Task 1: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_name="drop_zero_price_rows",
                status=TaskStatus.FAILED,
                execution_time=execution_time,
                error=str(e),
                description="Failed to drop rows where price is 0"
            )
    
    def task2_update_df_ticker_domain_chunked(self) -> TaskResult:
        """Task 2: Update domain column in df_ticker table using chunked processing"""
        start_time = time.time()
        logger.info("Starting Task 2: Update domain column in df_ticker table (chunked)")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create domain extraction function if it doesn't exist
                if not self.create_domain_extraction_function(cursor):
                    raise Exception("Failed to create domain extraction function")
                
                # First, get the total count of rows that need updating
                count_query = """
                SELECT COUNT(*) FROM df_ticker 
                WHERE link IS NOT NULL 
                AND link != '' 
                AND link != 'nan'
                AND link LIKE '%://%'
                AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                """
                cursor.execute(count_query)
                total_rows = cursor.fetchone()[0]
                
                logger.info(f"Found {total_rows} rows in df_ticker that need domain updates")
                
                if total_rows == 0:
                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_name="update_df_ticker_domain",
                        status=TaskStatus.COMPLETED,
                        affected_rows=0,
                        execution_time=execution_time,
                        description="No rows need domain updates"
                    )
                
                # Process in chunks to avoid lock timeouts
                chunk_size = 500
                total_updated = 0
                chunk_count = 0
                
                while total_updated < total_rows:
                    chunk_count += 1
                    logger.info(f"Processing chunk {chunk_count} (rows {total_updated + 1}-{min(total_updated + chunk_size, total_rows)})")
                    
                    # Update a chunk of rows
                    update_query = f"""
                    UPDATE df_ticker 
                    SET domain = extract_domain(link)
                    WHERE link IS NOT NULL 
                    AND link != '' 
                    AND link != 'nan'
                    AND link LIKE '%://%'
                    AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                    LIMIT {chunk_size}
                    """
                    
                    cursor.execute(update_query)
                    chunk_updated = cursor.rowcount
                    total_updated += chunk_updated
                    
                    conn.commit()  # Commit each chunk
                    logger.info(f"Chunk {chunk_count}: Updated {chunk_updated} rows, total: {total_updated}")
                    
                    if chunk_updated == 0:
                        break
                    
                    # Small delay to reduce lock contention
                    time.sleep(0.2)
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully updated {total_updated} domain values in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="update_df_ticker_domain",
                    status=TaskStatus.COMPLETED,
                    affected_rows=total_updated,
                    execution_time=execution_time,
                    description="Updated domain column based on link column (chunked)"
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error in Task 2: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_name="update_df_ticker_domain",
                status=TaskStatus.FAILED,
                execution_time=execution_time,
                error=str(e),
                description="Failed to update domain column in df_ticker"
            )
    
    def task3_update_fixed_fields_domain_chunked(self) -> TaskResult:
        """Task 3: Update domain column in fixed_fields table using chunked processing"""
        start_time = time.time()
        logger.info("Starting Task 3: Update domain column in fixed_fields table (chunked)")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # First, get the total count of rows that need updating
                count_query = """
                SELECT COUNT(*) FROM fixed_fields 
                WHERE link IS NOT NULL 
                AND link != '' 
                AND link != 'nan'
                AND link LIKE '%://%'
                AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                """
                cursor.execute(count_query)
                total_rows = cursor.fetchone()[0]
                
                logger.info(f"Found {total_rows} rows in fixed_fields that need domain updates")
                
                if total_rows == 0:
                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_name="update_fixed_fields_domain",
                        status=TaskStatus.COMPLETED,
                        affected_rows=0,
                        execution_time=execution_time,
                        description="No rows need domain updates"
                    )
                
                # Process in chunks to avoid lock timeouts
                chunk_size = 500
                total_updated = 0
                chunk_count = 0
                
                while total_updated < total_rows:
                    chunk_count += 1
                    logger.info(f"Processing chunk {chunk_count} (rows {total_updated + 1}-{min(total_updated + chunk_size, total_rows)})")
                    
                    # Update a chunk of rows
                    update_query = f"""
                    UPDATE fixed_fields 
                    SET domain = extract_domain(link)
                    WHERE link IS NOT NULL 
                    AND link != '' 
                    AND link != 'nan'
                    AND link LIKE '%://%'
                    AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                    LIMIT {chunk_size}
                    """
                    
                    cursor.execute(update_query)
                    chunk_updated = cursor.rowcount
                    total_updated += chunk_updated
                    
                    conn.commit()  # Commit each chunk
                    logger.info(f"Chunk {chunk_count}: Updated {chunk_updated} rows, total: {total_updated}")
                    
                    if chunk_updated == 0:
                        break
                    
                    # Small delay to reduce lock contention
                    time.sleep(0.2)
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully updated {total_updated} domain values in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="update_fixed_fields_domain",
                    status=TaskStatus.COMPLETED,
                    affected_rows=total_updated,
                    execution_time=execution_time,
                    description="Updated domain column based on link column (chunked)"
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error in Task 3: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_name="update_fixed_fields_domain",
                status=TaskStatus.FAILED,
                execution_time=execution_time,
                error=str(e),
                description="Failed to update domain column in fixed_fields"
            )
    
    def create_market_price_list_table(self, cursor) -> bool:
        """Create the market_price_list table with optimized structure"""
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
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_domain (domain),
                INDEX idx_price (price),
                INDEX idx_date (date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_query)
            logger.info("market_price_list table created or already exists")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Error creating market_price_list table: {e}")
            return False
    
    def task4_create_market_price_list_chunked(self) -> TaskResult:
        """Task 4: Create market_price_list using chunked processing to avoid timeouts"""
        start_time = time.time()
        logger.info("Starting Task 4: Create market_price_list using chunked processing")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Step 1: Create table with indexes
                if not self.create_market_price_list_table(cursor):
                    raise Exception("Failed to create market_price_list table")
                
                # Step 2: Get count of records to process
                count_query = """
                SELECT COUNT(*) FROM fixed_fields ff
                INNER JOIN df_ticker dt ON ff.sku = dt.sku
                WHERE ff.sku IS NOT NULL 
                AND ff.sku != ''
                AND dt.sku IS NOT NULL 
                AND dt.sku != ''
                AND (dt.domain IS NULL OR dt.domain != 'naturamarket.ca')
                AND (dt.link IS NULL OR dt.link NOT LIKE '%naturamarket%')
                """
                cursor.execute(count_query)
                total_records = cursor.fetchone()[0]
                
                logger.info(f"Found {total_records} records to process for market_price_list")
                
                if total_records == 0:
                    execution_time = time.time() - start_time
                    return TaskResult(
                        task_name="create_market_price_list",
                        status=TaskStatus.COMPLETED,
                        affected_rows=0,
                        execution_time=execution_time,
                        description="No records to process for market_price_list"
                    )
                
                # Step 3: Process in chunks to avoid timeouts
                chunk_size = 1000
                total_processed = 0
                chunk_count = 0
                
                while total_processed < total_records:
                    chunk_count += 1
                    logger.info(f"Processing chunk {chunk_count} (records {total_processed + 1}-{min(total_processed + chunk_size, total_records)})")
                    
                    # Insert chunk using LIMIT and OFFSET
                    insert_query = f"""
                    INSERT INTO market_price_list (
                        sku, brand, title, barcode, vol, keywords, imgurl,
                        price, tag, link, domain, `key`, date
                    )
                    SELECT 
                        ff.sku,
                        ff.brand,
                        ff.title,
                        ff.barcode,
                        ff.vol,
                        ff.keywords,
                        ff.imgurl,
                        dt.price,
                        dt.tag,
                        dt.link,
                        dt.domain,
                        dt.`key`,
                        dt.date
                    FROM fixed_fields ff
                    INNER JOIN df_ticker dt ON ff.sku = dt.sku
                    WHERE ff.sku IS NOT NULL 
                    AND ff.sku != ''
                    AND dt.sku IS NOT NULL 
                    AND dt.sku != ''
                    AND (dt.domain IS NULL OR dt.domain != 'naturamarket.ca')
                    AND (dt.link IS NULL OR dt.link NOT LIKE '%naturamarket%')
                    LIMIT {chunk_size} OFFSET {total_processed}
                    ON DUPLICATE KEY UPDATE
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
                    
                    cursor.execute(insert_query)
                    chunk_processed = cursor.rowcount
                    total_processed += chunk_processed
                    
                    conn.commit()  # Commit each chunk
                    logger.info(f"Chunk {chunk_count}: Processed {chunk_processed} records, total: {total_processed}")
                    
                    if chunk_processed == 0:
                        break
                    
                    # Small delay to reduce lock contention
                    time.sleep(0.5)
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully processed {total_processed} records in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="create_market_price_list",
                    status=TaskStatus.COMPLETED,
                    affected_rows=total_processed,
                    execution_time=execution_time,
                    description="Created market_price_list using chunked processing"
                )
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Error in Task 4: {e}"
            logger.error(error_msg)
            return TaskResult(
                task_name="create_market_price_list",
                status=TaskStatus.FAILED,
                execution_time=execution_time,
                error=str(e),
                description="Failed to create market_price_list"
            )
    
    def run_sequential_tasks(self, tasks: List[callable]) -> List[TaskResult]:
        """Run tasks sequentially to avoid lock contention"""
        logger.info(f"Running {len(tasks)} tasks sequentially to avoid lock contention")
        
        results = []
        for i, task in enumerate(tasks, 1):
            logger.info(f"Running task {i}/{len(tasks)}: {task.__name__}")
            try:
                result = task()
                results.append(result)
                logger.info(f"Task {task.__name__} completed: {result.status.value}")
            except Exception as e:
                logger.error(f"Task {task.__name__} failed: {e}")
                results.append(TaskResult(
                    task_name=task.__name__,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    description="Task failed with exception"
                ))
        
        return results
    
    def run_all_maintenance_tasks(self) -> Dict[str, Any]:
        """Run all maintenance tasks with robust constraint handling"""
        overall_start_time = time.time()
        logger.info("Starting robust SQL maintenance process")
        logger.info("=" * 60)
        logger.info("Using sequential processing to avoid lock contention")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Run tasks sequentially to avoid lock contention
            tasks = [
                self.task1_drop_zero_price_rows,
                self.task2_update_df_ticker_domain_chunked,
                self.task3_update_fixed_fields_domain_chunked,
                self.task4_create_market_price_list_chunked
            ]
            
            task_results = self.run_sequential_tasks(tasks)
            
            # Store results
            for result in task_results:
                results[result.task_name] = result
            
            overall_execution_time = time.time() - overall_start_time
            logger.info(f"All maintenance tasks completed in {overall_execution_time:.2f}s")
            
        except Exception as e:
            overall_execution_time = time.time() - overall_start_time
            logger.error(f"Error during maintenance process: {e}")
            results['error'] = str(e)
            results['execution_time'] = overall_execution_time
        
        return results
    
    def log_summary(self, results: Dict[str, Any]):
        """Log a comprehensive summary of all maintenance tasks"""
        logger.info("\n" + "=" * 80)
        logger.info("ROBUST MAINTENANCE SUMMARY")
        logger.info("=" * 80)
        
        total_execution_time = 0
        total_affected_rows = 0
        successful_tasks = 0
        failed_tasks = 0
        
        for task_name, result in results.items():
            if task_name == 'error':
                logger.error(f"❌ Process Error: {result}")
                continue
            
            if isinstance(result, TaskResult):
                total_execution_time += result.execution_time
                total_affected_rows += result.affected_rows
                
                if result.status == TaskStatus.COMPLETED:
                    successful_tasks += 1
                    logger.info(f"✅ {result.task_name}: {result.affected_rows} rows affected in {result.execution_time:.2f}s - {result.description}")
                elif result.status == TaskStatus.FAILED:
                    failed_tasks += 1
                    logger.error(f"❌ {result.task_name}: FAILED in {result.execution_time:.2f}s - {result.error}")
                elif result.status == TaskStatus.SKIPPED:
                    logger.warning(f"⏭️  {result.task_name}: SKIPPED - {result.description}")
        
        logger.info("=" * 80)
        logger.info(f"SUMMARY STATISTICS:")
        logger.info(f"  Total Execution Time: {total_execution_time:.2f}s")
        logger.info(f"  Total Rows Affected: {total_affected_rows:,}")
        logger.info(f"  Successful Tasks: {successful_tasks}")
        logger.info(f"  Failed Tasks: {failed_tasks}")
        logger.info(f"  Success Rate: {(successful_tasks / (successful_tasks + failed_tasks) * 100):.1f}%")
        logger.info("=" * 80)


def main():
    """Main function with robust execution"""
    try:
        # Initialize database configuration
        config = DatabaseConfig()
        
        # Create robust maintenance instance
        maintenance = RobustSQLMaintenance(config)
        
        # Run all maintenance tasks
        results = maintenance.run_all_maintenance_tasks()
        
        # Log comprehensive summary
        maintenance.log_summary(results)
        
        # Check if all tasks succeeded
        all_success = all(
            isinstance(result, TaskResult) and result.status == TaskStatus.COMPLETED
            for result in results.values()
            if not isinstance(result, str)  # Exclude error strings
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

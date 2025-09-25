#!/usr/bin/env python3
"""
Optimized SQL Maintenance Script for Mongrel Price Ticker Database

This optimized version includes:
1. Connection pooling for better resource management
2. Pure SQL operations instead of pandas for better performance
3. Parallel processing for independent tasks
4. Improved error handling and retry logic
5. Consolidated domain extraction logic
6. Better memory management

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
        logging.FileHandler('sql_maintenance_optimized.log'),
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
    """Enhanced database configuration with connection pooling"""
    
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
        
        # Connection pool configuration
        self.pool_name = 'maintenance_pool'
        self.pool_size = 5
        self.pool_reset_session = True
        self.autocommit = False
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1.0
        self.connection_timeout = 30


class OptimizedSQLMaintenance:
    """Optimized SQL maintenance operations with connection pooling and parallel processing"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
        self._initialize_connection_pool()
    
    def _initialize_connection_pool(self):
        """Initialize MySQL connection pool"""
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
                'use_unicode': True
            }
            
            self.pool = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"Connection pool initialized with {self.config.pool_size} connections")
            
        except mysql.connector.Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections from pool"""
        connection = None
        try:
            connection = self.pool.get_connection()
            logger.debug("Retrieved connection from pool")
            yield connection
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Returned connection to pool")
    
    def extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL using urlparse"""
        if not url or str(url).strip().lower() in ['nan', 'none', '']:
            return ''
        
        try:
            parsed = urlparse(str(url))
            return parsed.netloc
        except Exception as e:
            logger.warning(f"Error parsing URL '{url}': {e}")
            return ''
    
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
                    # Delete rows in batches for better performance
                    delete_query = "DELETE FROM natura_sku_summary WHERE price = 0 LIMIT 1000"
                    total_deleted = 0
                    
                    while True:
                        cursor.execute(delete_query)
                        deleted_count = cursor.rowcount
                        total_deleted += deleted_count
                        
                        if deleted_count == 0:
                            break
                        
                        conn.commit()  # Commit each batch
                        logger.debug(f"Deleted {deleted_count} rows, total: {total_deleted}")
                    
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
    
    def task2_update_df_ticker_domain(self) -> TaskResult:
        """Task 2: Update domain column in df_ticker table using SQL function"""
        start_time = time.time()
        logger.info("Starting Task 2: Update domain column in df_ticker table")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create domain extraction function if it doesn't exist
                if not self.create_domain_extraction_function(cursor):
                    raise Exception("Failed to create domain extraction function")
                
                # Use the function for efficient domain extraction
                update_query = """
                UPDATE df_ticker 
                SET domain = extract_domain(link)
                WHERE link IS NOT NULL 
                AND link != '' 
                AND link != 'nan'
                AND link LIKE '%://%'
                AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                """
                
                cursor.execute(update_query)
                affected_rows = cursor.rowcount
                conn.commit()
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully updated {affected_rows} domain values in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="update_df_ticker_domain",
                    status=TaskStatus.COMPLETED,
                    affected_rows=affected_rows,
                    execution_time=execution_time,
                    description="Updated domain column based on link column"
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
    
    def task3_update_fixed_fields_domain(self) -> TaskResult:
        """Task 3: Update domain column in fixed_fields table using SQL function"""
        start_time = time.time()
        logger.info("Starting Task 3: Update domain column in fixed_fields table")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Use the domain extraction function
                update_query = """
                UPDATE fixed_fields 
                SET domain = extract_domain(link)
                WHERE link IS NOT NULL 
                AND link != '' 
                AND link != 'nan'
                AND link LIKE '%://%'
                AND (domain IS NULL OR domain = '' OR domain != extract_domain(link))
                """
                
                cursor.execute(update_query)
                affected_rows = cursor.rowcount
                conn.commit()
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully updated {affected_rows} domain values in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="update_fixed_fields_domain",
                    status=TaskStatus.COMPLETED,
                    affected_rows=affected_rows,
                    execution_time=execution_time,
                    description="Updated domain column based on link column"
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
    
    def task4_create_market_price_list_optimized(self) -> TaskResult:
        """Task 4: Create market_price_list using pure SQL operations (optimized)"""
        start_time = time.time()
        logger.info("Starting Task 4: Create market_price_list using optimized SQL operations")
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Step 1: Create table with indexes
                if not self.create_market_price_list_table(cursor):
                    raise Exception("Failed to create market_price_list table")
                
                # Step 2: Use pure SQL to create market_price_list
                # This replaces the pandas-based approach with a single SQL operation
                create_market_price_list_sql = """
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
                
                logger.info("Executing optimized SQL merge operation...")
                cursor.execute(create_market_price_list_sql)
                affected_rows = cursor.rowcount
                conn.commit()
                
                execution_time = time.time() - start_time
                logger.info(f"Successfully created market_price_list with {affected_rows} records in {execution_time:.2f}s")
                
                return TaskResult(
                    task_name="create_market_price_list",
                    status=TaskStatus.COMPLETED,
                    affected_rows=affected_rows,
                    execution_time=execution_time,
                    description="Created market_price_list using optimized SQL operations"
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
    
    def run_parallel_tasks(self, tasks: List[callable]) -> List[TaskResult]:
        """Run multiple tasks in parallel using ThreadPoolExecutor"""
        logger.info(f"Running {len(tasks)} tasks in parallel")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(task): task for task in tasks}
            
            # Collect results as they complete
            results = []
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Task {result.task_name} completed: {result.status.value}")
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
        """Run all maintenance tasks with optimizations"""
        overall_start_time = time.time()
        logger.info("Starting optimized SQL maintenance process")
        logger.info("=" * 60)
        
        results = {}
        
        try:
            # Phase 1: Run independent tasks in parallel
            logger.info("Phase 1: Running independent tasks in parallel")
            parallel_tasks = [
                self.task1_drop_zero_price_rows,
                self.task2_update_df_ticker_domain,
                self.task3_update_fixed_fields_domain
            ]
            
            parallel_results = self.run_parallel_tasks(parallel_tasks)
            
            # Store parallel results
            for result in parallel_results:
                results[result.task_name] = result
            
            # Phase 2: Run dependent task (market_price_list creation)
            logger.info("Phase 2: Running dependent task (market_price_list creation)")
            task4_result = self.task4_create_market_price_list_optimized()
            results[task4_result.task_name] = task4_result
            
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
        logger.info("OPTIMIZED MAINTENANCE SUMMARY")
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
    """Main function with optimized execution"""
    try:
        # Initialize database configuration
        config = DatabaseConfig()
        
        # Create optimized maintenance instance
        maintenance = OptimizedSQLMaintenance(config)
        
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

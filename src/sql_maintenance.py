#!/usr/bin/env python3
"""
SQL Maintenance Script for Mongrel Price Ticker Database

This script performs various maintenance operations on the df_ticker table:
- Removes 'www.' prefix from domains
- Removes trailing slashes from domains
- Converts domains to lowercase

Author: Mongrel Data Lab
Date: 2024
"""

import mysql.connector
import logging
import sys
from typing import List, Dict, Any
from contextlib import contextmanager


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
    def __init__(self, host: str = 'localhost', user: str = 'root', 
                 password: str = '', database: str = 'mongrel_price_ticker'):
        self.host = host
        self.user = user
        self.password = password
        self.database = database


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
    
    def execute_maintenance_queries(self) -> Dict[str, Any]:
        """Execute all maintenance queries and return results"""
        
        maintenance_queries = [
            {
                'name': 'Remove www prefix',
                'query': "UPDATE `df_ticker` SET domain = REPLACE(domain, 'www.', '') WHERE domain LIKE 'www.%'",
                'description': 'Removes www. prefix from domains'
            },
            {
                'name': 'Remove trailing slashes',
                'query': "UPDATE `df_ticker` SET domain = TRIM(TRAILING '/' FROM domain) WHERE domain LIKE '%/'",
                'description': 'Removes trailing slashes from domains'
            },
            {
                'name': 'Convert to lowercase',
                'query': "UPDATE `df_ticker` SET domain = LOWER(domain) WHERE domain REGEXP '[A-Z]'",
                'description': 'Converts domains to lowercase'
            }
        ]
        
        results = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for query_info in maintenance_queries:
                try:
                    logger.info(f"Executing: {query_info['description']}")
                    cursor.execute(query_info['query'])
                    affected_rows = cursor.rowcount
                    
                    results[query_info['name']] = {
                        'success': True,
                        'affected_rows': affected_rows,
                        'description': query_info['description']
                    }
                    
                    logger.info(f"✓ {query_info['name']}: {affected_rows} rows affected")
                    
                except mysql.connector.Error as e:
                    error_msg = f"Error executing {query_info['name']}: {e}"
                    logger.error(error_msg)
                    
                    results[query_info['name']] = {
                        'success': False,
                        'error': str(e),
                        'description': query_info['description']
                    }
            
            # Commit all changes
            try:
                conn.commit()
                logger.info("All changes committed successfully")
            except mysql.connector.Error as e:
                conn.rollback()
                logger.error(f"Error committing changes: {e}")
                raise
            
            cursor.close()
        
        return results
    
    def get_domain_statistics(self) -> Dict[str, int]:
        """Get statistics about domain formats before and after maintenance"""
        
        stats_queries = {
            'total_domains': "SELECT COUNT(*) FROM df_ticker",
            'domains_with_www': "SELECT COUNT(*) FROM df_ticker WHERE domain LIKE 'www.%'",
            'domains_with_trailing_slash': "SELECT COUNT(*) FROM df_ticker WHERE domain LIKE '%/'",
            'domains_with_uppercase': "SELECT COUNT(*) FROM df_ticker WHERE domain REGEXP '[A-Z]'"
        }
        
        stats = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for stat_name, query in stats_queries.items():
                try:
                    cursor.execute(query)
                    result = cursor.fetchone()
                    stats[stat_name] = result[0] if result else 0
                except mysql.connector.Error as e:
                    logger.error(f"Error getting {stat_name}: {e}")
                    stats[stat_name] = 0
            
            cursor.close()
        
        return stats
    
    def run_maintenance(self) -> bool:
        """Run complete maintenance process"""
        try:
            logger.info("Starting SQL maintenance process")
            
            # Get statistics before maintenance
            logger.info("Getting pre-maintenance statistics...")
            pre_stats = self.get_domain_statistics()
            logger.info(f"Pre-maintenance stats: {pre_stats}")
            
            # Execute maintenance queries
            logger.info("Executing maintenance queries...")
            results = self.execute_maintenance_queries()
            
            # Get statistics after maintenance
            logger.info("Getting post-maintenance statistics...")
            post_stats = self.get_domain_statistics()
            logger.info(f"Post-maintenance stats: {post_stats}")
            
            # Log summary
            self._log_summary(results, pre_stats, post_stats)
            
            return True
            
        except Exception as e:
            logger.error(f"Maintenance process failed: {e}")
            return False
    
    def _log_summary(self, results: Dict[str, Any], pre_stats: Dict[str, int], post_stats: Dict[str, int]):
        """Log a summary of the maintenance process"""
        logger.info("=" * 50)
        logger.info("MAINTENANCE SUMMARY")
        logger.info("=" * 50)
        
        for query_name, result in results.items():
            if result['success']:
                logger.info(f"✓ {query_name}: {result['affected_rows']} rows updated")
            else:
                logger.info(f"✗ {query_name}: FAILED - {result.get('error', 'Unknown error')}")
        
        logger.info("\nSTATISTICS COMPARISON:")
        logger.info(f"Total domains: {pre_stats['total_domains']} (unchanged)")
        logger.info(f"Domains with www: {pre_stats['domains_with_www']} → {post_stats['domains_with_www']}")
        logger.info(f"Domains with trailing slash: {pre_stats['domains_with_trailing_slash']} → {post_stats['domains_with_trailing_slash']}")
        logger.info(f"Domains with uppercase: {pre_stats['domains_with_uppercase']} → {post_stats['domains_with_uppercase']}")
        
        logger.info("=" * 50)


def main():
    """Main function"""
    try:
        # Initialize database configuration
        # TODO: Consider loading from environment variables or config file
        config = DatabaseConfig(
            host='localhost',
            user='root',
            password='',  # Consider using environment variables for security
            database='mongrel_price_ticker'
        )
        
        # Create maintenance instance and run
        maintenance = SQLMaintenance(config)
        success = maintenance.run_maintenance()
        
        if success:
            logger.info("Maintenance completed successfully")
            sys.exit(0)
        else:
            logger.error("Maintenance failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Maintenance interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
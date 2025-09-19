"""
Database Configuration Module

This module handles database connection configuration using environment variables.
It provides secure access to database credentials and connection management.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseConfig:
    """Database configuration class for managing connection parameters."""
    
    def __init__(self):
        """Initialize database configuration from environment variables."""
        self.host = os.getenv('DB_HOST')
        self.name = os.getenv('DB_NAME')
        self.user = os.getenv('DB_USER')
        self.password = os.getenv('DB_PASSWORD')
        self.port = os.getenv('DB_PORT', '3306')  # Default MySQL port
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '5'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        
        # Validate required credentials
        self._validate_credentials()
    
    def _validate_credentials(self):
        """Validate that all required database credentials are present."""
        required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    def get_connection_string(self):
        """Get the MySQL connection string."""
        return f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    def create_engine(self, poolclass=NullPool):
        """Create a SQLAlchemy engine with the configured parameters."""
        connection_string = self.get_connection_string()
        
        return create_engine(
            connection_string,
            poolclass=poolclass,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            echo=False  # Set to True for SQL query logging
        )
    
    def get_credentials(self):
        """Get database credentials as a dictionary (for backward compatibility)."""
        return {
            'host': self.host,
            'name': self.name,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }

# Create a global instance for easy importing
db_config = DatabaseConfig()

# Convenience function for backward compatibility
def get_database_engine():
    """Get a configured database engine."""
    return db_config.create_engine()

# Convenience function for getting credentials
def get_database_credentials():
    """Get database credentials as a dictionary."""
    return db_config.get_credentials()

"""
Example usage of the database configuration with environment variables.

This file demonstrates how to use the new database configuration system.
"""

from database_config import get_database_engine, get_database_credentials
from mySQL_Upsert_Function_v2 import upsert_df_to_mysql, read_mysql_to_df
import pandas as pd

def example_database_operations():
    """Example of how to use the database with environment variables."""
    
    # Get database engine
    engine = get_database_engine()
    
    # Get credentials info (for logging/debugging)
    credentials = get_database_credentials()
    print(f"Connected to database: {credentials['host']}/{credentials['name']}")
    
    # Example: Create a sample DataFrame
    sample_data = pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Product A', 'Product B', 'Product C'],
        'price': [10.99, 15.50, 8.75],
        'tags': [['tag1', 'tag2'], ['tag3'], ['tag1', 'tag4']]
    })
    
    # Example: Upsert data to a table
    try:
        upsert_df_to_mysql(
            df=sample_data,
            engine=engine,
            target_table='sample_products',
            key_col='id'
        )
        print("✅ Data upserted successfully!")
    except Exception as e:
        print(f"❌ Error upserting data: {e}")
    
    # Example: Read data from a table
    try:
        df = read_mysql_to_df(engine, 'sample_products')
        if df is not None:
            print("✅ Data read successfully!")
            print(df.head())
        else:
            print("❌ Failed to read data")
    except Exception as e:
        print(f"❌ Error reading data: {e}")

if __name__ == "__main__":
    example_database_operations()

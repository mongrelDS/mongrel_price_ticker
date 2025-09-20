# @title Price 30-Day Analysis Function

import pandas as pd
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import database functions
from mySQL_Upsert_Function import read_mysql_to_df
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

def get_price_30d(domain='well.ca', table_name='df_ticker', verbose=True):
    """
    Analyzes 30-day price trends for products from a specific domain.
    
    Args:
        domain (str): The domain to filter products by (e.g., 'well.ca')
        table_name (str): The database table name containing price data
        verbose (bool): Whether to print detailed output
    
    Returns:
        pd.DataFrame: DataFrame with columns ['link', 'price', 'date', 'tag', 'price_30d_avg', 'high', 'low']
                     Returns None if no data found or error occurs
    """
    
    # Database connection setup (using environment variables)
    db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
    db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
    db_password = os.getenv('DB_PASSWORD', 'taan2#IbizaI')
    db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    
    # Create database connection string
    connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
    
    # Create database engine
    db_engine = create_engine(connection_string, poolclass=NullPool)
    
    try:
        if verbose:
            print(f"🔍 Analyzing 30-day price trends for domain: {domain}")
            print(f"📊 Reading data from table: {table_name}")
        
        # Read data from database
        df_ticker = read_mysql_to_df(engine=db_engine, table_name=table_name)
        
        if df_ticker is None or df_ticker.empty:
            if verbose:
                print(f"❌ Table '{table_name}' is empty or doesn't exist.")
                print("Please run the price update script first to populate the table.")
            return None
        
        if verbose:
            print(f"✅ Found {len(df_ticker)} total records")
        
        # Filter by domain if domain column exists
        if 'domain' in df_ticker.columns:
            df_ticker = df_ticker[df_ticker['domain'] == domain].copy()
            if verbose:
                print(f"🔗 Filtered to {len(df_ticker)} records for domain '{domain}'")
        
        if df_ticker.empty:
            if verbose:
                print(f"❌ No data found for domain '{domain}'")
            return None
        
        # Convert date column to datetime
        df_ticker['date'] = pd.to_datetime(df_ticker['date'])
        
        if verbose:
            print("📈 Processing 30-day price analysis...")
        
        # Filter out zero prices
        df_filtered = df_ticker[df_ticker['price'] > 0].copy()
        
        if df_filtered.empty:
            if verbose:
                print("❌ No valid price data found (all prices are zero or null)")
            return None
        
        # Get most recent entry for each link
        df_recent = df_filtered.sort_values('date').groupby('link').tail(1).copy()
        
        # Calculate stats for each link
        def calculate_stats(group):
            # Get 30 days ago
            thirty_days_ago = pd.Timestamp.now() - pd.Timedelta(days=30)
            
            # Filter to last 30 days
            recent_data = group[group['date'] >= thirty_days_ago]
            
            return pd.Series({
                'high': group['price'].max(),
                'low': group['price'].min(),
                'price_30d_avg': recent_data['price'].mean() if not recent_data.empty else None
            })
        
        # Calculate stats for each link
        stats = df_filtered.groupby('link').apply(calculate_stats, include_groups=False).reset_index()
        
        # Merge with most recent data
        df_price_30d = df_recent.merge(stats, on='link', how='left')
        
        # Select and reorder columns
        df_price_30d = df_price_30d[['link', 'price', 'date', 'tag', 'price_30d_avg', 'high', 'low']].copy()
        
        if verbose:
            print(f"\n✅ Analysis complete for domain '{domain}'")
            print(f"📊 Shape: {df_price_30d.shape}")
            print(f"💰 Average current price: ${df_price_30d['price'].mean():.2f}")
            print(f"📈 Average 30-day price: ${df_price_30d['price_30d_avg'].mean():.2f}")
            print(f"🔢 Products with 30-day data: {df_price_30d['price_30d_avg'].notna().sum()}")
        
        return df_price_30d
        
    except Exception as e:
        if verbose:
            print(f"❌ Error processing data: {e}")
            import traceback
            traceback.print_exc()
        return None

# Example usage and testing
if __name__ == "__main__":
    # Test the function
    print("🧪 Testing get_price_30d function...")
    
    # Test with well.ca
    df_wellca = get_price_30d(
        domain='well.ca',
        verbose=True
        )
    
    if df_wellca is not None:
        print("\n📋 Sample results:")
        print(df_wellca.head())
        
        print("\n📊 Summary:")
        print(df_wellca[['link', 'price', 'price_30d_avg', 'high', 'low']].head(10))
    else:
        print("❌ No data returned")



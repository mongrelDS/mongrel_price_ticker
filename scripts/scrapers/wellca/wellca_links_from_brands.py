# @title PDP Link List

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Import database functions
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Database connection setup (using environment variables)
db_host = os.getenv('DB_HOST', '127.0.0.1')
db_port = os.getenv('DB_PORT', '30306')
db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
db_password = os.getenv('DB_PASSWORD')
if not db_password:
    raise ValueError("DB_PASSWORD environment variable is required (no default in repo)")
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')

# Create database connection string
connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create database engine
db_engine = create_engine(connection_string, poolclass=NullPool)

# Read brand links from database
print("Reading brand links from database...")
df_link = read_mysql_to_df(engine=db_engine, table_name='brand_link_list')
# keep only the links that start with https://well.ca/brand/
df_link = df_link[df_link['brand_url'].str.startswith('https://well.ca/brand/')]
df_link = df_link.sample(90) # sample 90 brands
print(f"Selected {len(df_link)} brands for processing")

# List to hold all the product links we find
all_pdp_links = []

# Set headers to mimic a browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Process each brand
for index, row in df_link.iterrows():
    brand_url = row['brand_url']
    print(f"Processing brand {index + 1}/60: {brand_url}")
    
    try:
        # Add random delay to be respectful
        time.sleep(random.uniform(1, 3))
        
        # Fetch the brand page
        response = requests.get(brand_url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all product links
        product_links = soup.select('a[href*="/products/"]')
        
        # Extract the href attributes
        for link in product_links:
            href = link.get('href')
            if href and 'well.ca/products/' in href:
                # Links are already absolute URLs, so add them directly
                all_pdp_links.append(href)
        
        print(f"  Found {len(product_links)} product links")
        
    except Exception as e:
        print(f"  Error processing {brand_url}: {e}")
        continue

# Remove duplicates
all_pdp_links = list(set(all_pdp_links))
print(f"\nTotal unique product links found: {len(all_pdp_links)}")

# Create DataFrame
df_pdp_links = pd.DataFrame(all_pdp_links, columns=['link'])

# Display sample
print("\nSample product links:")
print(df_pdp_links.head())

# Upload to database
if not df_pdp_links.empty:
    print("\nUploading to database...")
    upsert_df_to_mysql(df=df_pdp_links, engine=db_engine, target_table='product_links', key_col='link')
    print("✅ Database upload complete!")
else:
    print("No product links found to upload.")

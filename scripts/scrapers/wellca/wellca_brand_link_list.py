# @title Get Brand Links

import pandas as pd
import requests
from bs4 import BeautifulSoup
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# Import database functions
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Database connection setup (using environment variables)
db_host = os.getenv('DB_HOST', '127.0.0.1')
db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
db_password = os.getenv('DB_PASSWORD')
if not db_password:
    raise ValueError("DB_PASSWORD environment variable is required (no default in repo)")
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')

# Create database connection string
connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

# Create database engine
db_engine = create_engine(connection_string, poolclass=NullPool)

# Define the target URL
url = 'https://well.ca/brand/index.html'

# Set headers to mimic a browser request
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print(f"Attempting to scrape all brand links from: {url}")

try:
    # --- 1. Fetch the page content ---
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # This will raise an error for bad status codes (like 404)

    # --- 2. Parse the HTML ---
    soup = BeautifulSoup(response.content, 'html.parser')

    # --- 3. Find all link elements ---
    # Based on the HTML, each brand link is an <a> tag inside a <div class="brand_item">
    # The CSS selector 'div.brand_item a' precisely targets these elements.
    link_elements = soup.select('div.brand_item a')

    # --- 4. Extract the 'href' attribute from each element ---
    # A list comprehension is a clean way to loop through all found elements and get the link
    all_links = [element.get('href') for element in link_elements]

    # --- 5. Create the DataFrame ---
    # Convert the list of links into a pandas DataFrame with a single column named 'link'
    df_link = pd.DataFrame(all_links, columns=['brand_url'])

    print(f"✅ Scraping complete. Found {len(df_link)} brand links.")
    print("-" * 50)
    print("Here is a sample of the data:")
    print(df_link.head()) # Display the first 5 links
    print("-" * 50)
    print("DataFrame 'df_link' created successfully.")

    # --- 6. Upload to database ---
    print("Uploading to database...")
    upsert_df_to_mysql(df=df_link, engine=db_engine, target_table='brand_link_list', key_col='brand_url')
    print("✅ Database upload complete!")

except requests.exceptions.RequestException as e:
    print(f"❌ Failed to retrieve the page. Error: {e}")
except Exception as e:
    print(f"❌ An unexpected error occurred: {e}")

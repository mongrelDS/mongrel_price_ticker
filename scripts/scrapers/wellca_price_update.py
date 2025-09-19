# @title Price Update

import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
from datetime import date
import concurrent.futures # Import the library
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import datetime
timestamp_0 = datetime.datetime.now() # timestamp_0 = time now
print(timestamp_0)


# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import database functions
from mySQL_Upsert_Function import read_mysql_to_df, upsert_df_to_mysql
from generate_key import generate_key
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Import analytics function with correct path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'analytics'))
from df_price_30d import get_price_30d

# Database connection setup (using environment variables)
db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
db_password = os.getenv('DB_PASSWORD', 'taan2#IbizaI')
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')

# Create database connection string
connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

# Create database engine
db_engine = create_engine(connection_string, poolclass=NullPool)

df_link = read_mysql_to_df(engine=db_engine, table_name='product_links')
print("Available columns in product_links table:")
print(df_link.columns.tolist())
print("\nFirst few rows:")
print(df_link.head())
df_link = df_link.sample(1000)
print(f"Selected {len(df_link)} products for processing")


df_wellca = get_price_30d(domain='well.ca')
#rename link to product_url
df_wellca = df_wellca.rename(columns={'link': 'product_url'})
# sort date
df_wellca = df_wellca.sort_values(by='date', ascending=False)

# get the tail 3000 rows
df_wellca = df_wellca.tail(3000)

df_link = pd.concat([df_link, df_wellca])
df_link = df_link.drop_duplicates(subset='product_url', keep='first')
df_link = df_link[['product_url']]


def get_product_info(url):
    """
    Scrapes a URL for its title, brand, breadcrumbs, price, availability status, image URL, and size.
    Returns a tuple (title, brand, breadcrumbs, price, tag, image_url, size).
    On complete failure (e.g., 404), the tag will be 'Failed'.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise an exception for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Initialize variables to default values ---
        title = None
        brand = None
        breadcrumbs = None
        price = pd.NA
        tag = ''
        image_url = None
        size = None # Initialize the new size field

        # -- Scrape Title --
        title_element = soup.select_one('h1.product-info__title')
        if title_element:
            title = title_element.get_text(strip=True)

        # -- Scrape Brand --
        brand_element = soup.select_one('a.product-info__brand')
        if brand_element:
            brand = brand_element.get_text(strip=True)

        # -- Scrape Size --
        # Selects the second span inside the h5 element with the specified class
        size_element = soup.select_one('h5.product-info__subtitle span:nth-of-type(2)')
        if size_element:
            size = size_element.get_text(strip=True)

        # -- Scrape Breadcrumbs --
        breadcrumb_elements = soup.select('div.bread_crumb_container span[itemprop="name"]')
        if breadcrumb_elements:
            breadcrumb_list = [elem.get_text(strip=True) for elem in breadcrumb_elements]
            breadcrumbs = " > ".join(breadcrumb_list)

        # -- Determine Availability Tag --
        if soup.select_one('div.product-info__unavailable--discontinued'):
            tag = 'Discontinued'
        elif soup.select_one('input#add_to_cart_button'):
            tag = 'Add to Cart'

        # -- Determine Price --
        price_element = soup.select_one('span[itemprop="price"]')
        if price_element:
            price_text = price_element.get_text(strip=True).replace('$', '')
            price = float(price_text)

        # -- Scrape Image URL --
        image_element = soup.select_one('#main-product-image')
        if image_element:
            image_url = image_element.get('src')


        # Return all scraped data, including the new size
        return title, brand, breadcrumbs, price, tag, image_url, size

    except requests.exceptions.RequestException as e:
        # Handle network-related errors (e.g., bad URL, 404 Not Found)
        print(f"Network error for {url}: {e}")
        # Return Nones for all fields and 'Failed' tag
        return None, None, None, pd.NA, 'Failed', None, None
    except Exception as e:
        # Handle any other unexpected errors during scraping
        print(f"An unexpected error occurred for {url}: {e}")
        # Return Nones for all fields and 'Failed' tag
        return None, None, None, pd.NA, 'Failed', None, None


# --- REVISED PARALLEL SCRAPING LOGIC ---
print("Scraping product info in parallel... (this may take a moment)")

# Create a list of URLs to process
urls_to_scrape = df_link['product_url'].tolist()
results = []

# Use ThreadPoolExecutor to scrape URLs concurrently
# max_workers is the number of threads. 5-10 is a good starting point.
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    # map applies the function to every item in the list and returns results in order
    results = list(executor.map(get_product_info, urls_to_scrape))

# Create a new DataFrame from the results
results_df = pd.DataFrame(results, columns=['title', 'brand', 'breadcrumbs', 'price', 'tag', 'image_url', 'size'])

# Update the original DataFrame
# We only update columns where the scrape was successful ('tag' is not 'Failed')
successful_scrapes = results_df['tag'] != 'Failed'
columns_to_update = ['title', 'brand', 'breadcrumbs', 'price', 'image_url', 'size']

# Reset the index of df_link before assignment to ensure alignment
df_link = df_link.reset_index(drop=True)

df_link.loc[successful_scrapes, columns_to_update] = results_df.loc[successful_scrapes, columns_to_update]

# Always update the tag and date for all rows
df_link['tag'] = results_df['tag']
df_link['date'] = date.today()



print("Scraping and updating complete.")
print("-" * 50)

df_link['vol'] = df_link['size']
df_link['imgurl'] = df_link['image_url']
df_link['keywords'] = df_link['breadcrumbs']
df_link = df_link.drop(['breadcrumbs', 'image_url' , 'size' ], axis=1)
df_link['product_url'] = df_link['product_url'].str.replace('_', '/')
df_link['sku'] = df_link['product_url'].str.extract(r'/([^/]+)\.html$')
df_link['link'] = "https://well.ca/products/" + df_link['sku'] + ".html"
df_link['domain'] = 'well.ca'

# drop product_url
df_link = df_link.drop(['product_url'], axis=1)

# Display the final results
print("\nFinal results:")
print(df_link.info())

df_ticker = df_link[['link', 'sku', 'domain', 'price','date','tag']]
generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col='key')
upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')


# fixed fields
fixed_fields = df_link[['link', 'imgurl', 'title', 'brand', 'sku', 'vol', 'keywords','domain']].copy()
fixed_fields = fixed_fields.dropna(subset=['sku']) # dropna sku
fixed_fields = fixed_fields[fixed_fields['sku'] != 'N/A'] # drop when sku is N/A

# dropna link
df_fixed_fields = fixed_fields.dropna(subset=['link'])

# deduplicate
fixed_fields = fixed_fields.drop_duplicates(subset='link', keep='first') # drop duplicate rows

# upload to database
upsert_df_to_mysql(df=fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='sku')


# @title Duration

timestamp_1 = datetime.datetime.now()
duration = timestamp_1 - timestamp_0
duration_in_minutes = duration.total_seconds() / 60

print(f"The duration is: {duration_in_minutes} minutes")

df_duration = pd.DataFrame({'duration_min': [duration_in_minutes], 'date': [datetime.datetime.now()]})
df_duration['results'] = len(df_ticker)
df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min']
df_duration['domain'] = 'well.ca'
df_duration['type'] = 'price_update'
df_duration

upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
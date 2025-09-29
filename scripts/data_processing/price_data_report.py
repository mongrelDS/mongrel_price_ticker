#!/usr/bin/env python3
"""
Price Data Report Script

This script processes product price data from multiple sources, performs matching
and scoring operations, and generates reports for both Canadian and US markets.

Features:
- Product matching using Jaccard similarity
- Computer vision scoring for image similarity
- Price comparison and margin analysis
- Google Sheets integration for reporting
- MySQL database integration

Author: Mongrel Data Lab
Date: 2024
"""

import pandas as pd
import numpy as np
import re
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

# Add the src directory to the path so we can import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import required functions
from mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from google_drive_csv_import import import_csv_from_drive
from write_df_to_sheet import write_df_to_sheet
from database_config import get_database_engine

# Import CV similarity function (now using OpenCV - much lighter!)
from cv_similarity_score import add_cv_scores

# Load environment variables
load_dotenv()

# Initialize database engine
engine = get_database_engine()

# Define display function for compatibility
def display(df):
    """Display function for compatibility with Jupyter notebooks"""
    if hasattr(df, 'head'):
        print(df.head())
    else:
        print(df)
    return df

# Define upload_df_to_google_sheet function
def upload_df_to_google_sheet(df, spreadsheet_id, sheet_name):
    """
    Upload DataFrame to Google Sheet using write_df_to_sheet function
    
    Args:
        df (pd.DataFrame): DataFrame to upload
        spreadsheet_id (str): Google Sheets spreadsheet ID
        sheet_name (str): Name of the sheet/tab
    
    Returns:
        bool: True if successful, False otherwise
    """
    return write_df_to_sheet(df, spreadsheet_id, sheet_name, 'A1')

#df_market_fixed_fields = read mysql to df from fixed_fields table
df_market_fixed_fields = read_mysql_to_df(engine, 'fixed_fields')
# drop column domain
df_market_fixed_fields = df_market_fixed_fields.drop(columns=['domain'])

df_price_30d_avg = read_mysql_to_df(engine, 'price_30d_avg')
df_natura_sku_summary = read_mysql_to_df(engine, 'natura_sku_summary')

# df_market = merge df_market_fixed_fields and df_price_30d_avg on 'sku'
df_market = pd.merge(df_market_fixed_fields, df_price_30d_avg[['link', 'price_30d_avg', 'latest_price','latest_date','domain']], on='link', how='inner')
# rename latest_price to price
df_market = df_market.rename(columns={'latest_price': 'price'})
# rename latest_date to date
df_market = df_market.rename(columns={'latest_date': 'date'})


# @title Inner Merge on firstwords of key column

# Parameters (to make the cell reusable)
left_DF = df_natura_sku_summary  # @param {type:"raw"}
right_DF = df_market     # @param {type:"raw"}

left_column = 'name'  # @param {type:"string"}
right_column = 'title'  # @param {type:"string"}

# Define function to extract first 3 words
def first_words(row, column_name):
    # Get the text from the specified column
    text = str(row[column_name]).lower() if pd.notna(row[column_name]) else ""

    # Split by whitespace and take up to the first 3 words
    words = text.split()[:2]

    # Join the words back with spaces
    return ' '.join(words)

# Step 1: Extract the first words from the left_column and right_column
left_DF['first_words'] = left_DF.apply(lambda row: first_words(row, left_column), axis=1)
right_DF['first_words'] = right_DF.apply(lambda row: first_words(row, right_column), axis=1)

# Step 2: Merge on 'firstword' using inner join
merged_1 = pd.merge(left_DF, right_DF, on='first_words', how='inner')


# @title Inner Merge on firstwords of key column

# Parameters (to make the cell reusable)
left_DF = df_natura_sku_summary  # @param {type:"raw"}
right_DF = df_market     # @param {type:"raw"}

left_column = 'barcode'  # @param {type:"string"}
right_column = 'barcode'  # @param {type:"string"}

# Define function to extract first 3 words
def first_words(row, column_name):
    # Get the text from the specified column
    text = str(row[column_name]).lower() if pd.notna(row[column_name]) else ""

    # Split by whitespace and take up to the first 3 words
    words = text.split()[:3]

    # Join the words back with spaces
    return ' '.join(words)

# Step 1: Extract the first 3 words from the left_column and right_column
left_DF['first_words'] = left_DF.apply(lambda row: first_words(row, left_column), axis=1)
right_DF['first_words'] = right_DF.apply(lambda row: first_words(row, right_column), axis=1)

# Step 2: Merge on 'firstword' using inner join
merged_2 = pd.merge(left_DF, right_DF, on='first_words', how='inner')

# @title merged_df shape
print(merged_1.shape)
display(merged_1.columns)
print("")
print(merged_2.shape)
display(merged_2.columns)

# Step 1: Concatenate merged_1 and merged_2
merged_df = pd.concat([merged_1, merged_2], ignore_index=True)

# Step 2: The merge operations naturally create the expected column structure
# - sku_x and sku_y from the merge operations
# - price_x (from left DF - Natura) and price_y (from right DF - other stores)
print("Columns after merge:", merged_df.columns.tolist())

# Verify that we have the expected columns from the natural merge
expected_columns = ['sku_x', 'sku_y', 'price_x', 'price_y']
missing_columns = [col for col in expected_columns if col not in merged_df.columns]
if missing_columns:
    print(f"Warning: Missing expected columns: {missing_columns}")
    print("Available columns:", merged_df.columns.tolist())
else:
    print("✅ All expected columns (sku_x, sku_y, price_x, price_y) are present from natural merge")

# Step 3: Drop duplicates based on 'sku_x' and 'sku_y'
merged_df = merged_df.drop_duplicates(subset=['sku_x', 'sku_y'])

# Step 4: Drop rows where sku_x is NaN
merged_df = merged_df.dropna(subset=['sku_x'])

# Display the resulting DataFrame
print(merged_df.shape)
display(merged_df.columns)
merged_df.head(3)
print(merged_df[['first_words']].head(3))


# @title title_score { form-width: "30%", display-mode: "form" }

# These are the column names for which we will calculate the Jaccard similarity
title_left = "name" # @param {type:"string"}
title_right = "title" # @param {type:"string"}
# This is the DataFrame on which we will perform the operation
result_df = merged_df # @param

# Import necessary functions from scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Function to calculate Jaccard Similarity
def jaccard_similarity(str1, str2):
    # 1. Handle None or empty strings:
    str1 = str(str1) if str1 is not None else ""
    str2 = str(str2) if str2 is not None else ""

    # 2. Convert to lowercase:
    str1 = str1.lower()
    str2 = str2.lower()

    # 3. Remove punctuation and special characters:
    str1 = re.sub(r'[^\w\s]', '', str1)
    str2 = re.sub(r'[^\w\s]', '', str2)

    # 4. Remove extra whitespace:
    str1 = re.sub(r'\s+', ' ', str1).strip()
    str2 = re.sub(r'\s+', ' ', str2).strip()

    # 5. Tokenization (split into words):
    set1 = set(str1.split())
    set2 = set(str2.split())

    # 6. Calculate Jaccard Similarity:
    intersection = len(set1.intersection(set2))
    union = len(set1) + len(set2) - intersection
    return intersection / float(union) if union else 0.0

# Calculate Jaccard Similarity and create a new column 'title_score'
result_df['title_score'] = result_df.apply(lambda row: jaccard_similarity(row[title_left], row[title_right]), axis=1)

# Round the 'jaccard_score' column to 5 decimal places
result_df['title_score'] = result_df['title_score'].round(5)

# Display the resulting DataFrame
# result_df


# @title vol_score { form-width: "30%", display-mode: "form" }

# These are the column names for which we will calculate the Jaccard similarity
# Fix column name references - check if vol_x and vol_y exist after merge
if 'vol_x' in result_df.columns and 'vol_y' in result_df.columns:
    title_left = "vol_x" # @param {type:"string"}
    title_right = "vol_y" # @param {type:"string"}
else:
    print("Warning: vol_x or vol_y columns not found. Skipping volume similarity calculation.")
    title_left = "vol_x"  # Will be handled in the function
    title_right = "vol_y"
# This is the DataFrame on which we will perform the operation
result_df = result_df # @param

# Import necessary functions from scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Function to calculate Jaccard Similarity
def jaccard_similarity(str1, str2):
    # 1. Handle None or empty strings:
    str1 = str(str1) if str1 is not None else ""
    str2 = str(str2) if str2 is not None else ""

    # 2. Convert to lowercase:
    str1 = str1.lower()
    str2 = str2.lower()

    # 3. Remove punctuation and special characters:
    str1 = re.sub(r'[^\w\s]', '', str1)
    str2 = re.sub(r'[^\w\s]', '', str2)

    # 4. Remove extra whitespace:
    str1 = re.sub(r'\s+', ' ', str1).strip()
    str2 = re.sub(r'\s+', ' ', str2).strip()

    # 5. Tokenization (split into words):
    set1 = set(str1.split())
    set2 = set(str2.split())

    # 6. Calculate Jaccard Similarity:
    intersection = len(set1.intersection(set2))
    union = len(set1) + len(set2) - intersection
    return intersection / float(union) if union else 0.0

# Calculate Jaccard Similarity and create a new column 'vol_score'
# Handle missing columns gracefully
if 'vol_x' in result_df.columns and 'vol_y' in result_df.columns:
    result_df['vol_score'] = result_df.apply(lambda row: jaccard_similarity(row[title_left], row[title_right]), axis=1)
else:
    print("Setting vol_score to 0.0 due to missing volume columns")
    result_df['vol_score'] = 0.0

# Round the 'jaccard_score' column to 5 decimal places
result_df['vol_score'] = result_df['vol_score'].round(5)


#  in instances where result_df['upc_score'] > 0.5 then   result_df['title_score'] = result_df['title_score'] + result_df['upc_score']
result_df.loc[result_df['vol_score'] > 0.99, 'title_score'] = result_df['title_score'] + 0.15


# Display the resulting DataFrame
result_df


# @title vol_score { form-width: "30%", display-mode: "form" }

# These are the column names for which we will calculate the Jaccard similarity
# Fix column name references - check if barcode_x and barcode_y exist after merge
if 'barcode_x' in result_df.columns and 'barcode_y' in result_df.columns:
    title_left = "barcode_x" # @param {type:"string"}
    title_right = "barcode_y" # @param {type:"string"}
else:
    print("Warning: barcode_x or barcode_y columns not found. Skipping barcode similarity calculation.")
    title_left = "barcode_x"  # Will be handled in the function
    title_right = "barcode_y"
# This is the DataFrame on which we will perform the operation
result_df = result_df # @param

# Import necessary functions from scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

# Function to calculate Jaccard Similarity
def jaccard_similarity(str1, str2):
    # 1. Handle None or empty strings:
    str1 = str(str1) if str1 is not None else ""
    str2 = str(str2) if str2 is not None else ""

    # 2. Convert to lowercase:
    str1 = str1.lower()
    str2 = str2.lower()

    # 3. Remove punctuation and special characters:
    str1 = re.sub(r'[^\w\s]', '', str1)
    str2 = re.sub(r'[^\w\s]', '', str2)

    # 4. Remove extra whitespace:
    str1 = re.sub(r'\s+', ' ', str1).strip()
    str2 = re.sub(r'\s+', ' ', str2).strip()

    # 5. Tokenization (split into words):
    set1 = set(str1.split())
    set2 = set(str2.split())

    # 6. Calculate Jaccard Similarity:
    intersection = len(set1.intersection(set2))
    union = len(set1) + len(set2) - intersection
    return intersection / float(union) if union else 0.0

# Calculate Jaccard Similarity and create a new column 'barcode_score'
# Handle missing columns gracefully
if 'barcode_x' in result_df.columns and 'barcode_y' in result_df.columns:
    result_df['barcode_score'] = result_df.apply(lambda row: jaccard_similarity(row[title_left], row[title_right]), axis=1)
else:
    print("Setting barcode_score to 0.0 due to missing barcode columns")
    result_df['barcode_score'] = 0.0

# Round the 'jaccard_score' column to 5 decimal places
result_df['barcode_score'] = result_df['barcode_score'].round(5)

#  in instances where result_df['upc_score'] > 0.5 then   result_df['title_score'] = result_df['title_score'] + result_df['upc_score']
result_df.loc[result_df['barcode_score'] > 0.99, 'title_score'] = result_df['title_score'] + 1.00

# Display the resulting DataFrame
result_df


# @title Est Multiple

"""
EST MULTIPLE

"""


# drop rows where price is 0 - Fix column name references
# Check for price columns after merge (they should be price_x and price_y from the merge)
if 'price_x' in result_df.columns and 'price_y' in result_df.columns:
    result_df = result_df[result_df['price_x'].astype(float) > 0]
    result_df = result_df[result_df['price_y'].astype(float) > 0]
    result_df['est_multiple'] = result_df['price_y'] / result_df['price_x']
else:
    print("Warning: price_x or price_y columns not found after merge. Skipping price filtering.")
    result_df['est_multiple'] = 1.0  # Default value

# in instances where result_df['est_multiple']  < 0.251  then [exclude] = yes
result_df.loc[result_df['est_multiple'] < 0.101, 'exclude'] = 'yes'

# in instances where result_df['est_multiple']  < 0.51      and     [title_score]   <  0.4357   then [exclude] = yes
result_df.loc[(result_df['est_multiple'] < 0.51) & (result_df['title_score'] < 0.3357), 'exclude'] = 'yes'
result_df.loc[(result_df['est_multiple'] > 3) & (result_df['title_score'] < 0.450), 'exclude'] = 'yes'

# prompt: what are the unique values of result_df['est_multiple']
print(result_df['est_multiple'].unique())

# how many rows where result_df['est_multiple']  is 0
zero_est_multiple_count = len(result_df[result_df['est_multiple'] == 0])
print(f"Number of rows where 'est_multiple' is 0: {zero_est_multiple_count}")

# Count rows where 'est_multiple' is an empty string
empty_est_multiple_count = len(result_df[result_df['est_multiple'] == ''])
print(f"Number of rows where 'est_multiple' is '': {empty_est_multiple_count}")

# Count rows where 'est_multiple' is NaN
nan_est_multiple_count = result_df['est_multiple'].isna().sum()
print(f"Number of rows where 'est_multiple' is NaN: {nan_est_multiple_count}")

# Count rows where 'est_multiple' is less than 0.51
count = len(result_df[result_df['est_multiple'] < 0.51])
print(f"Number of rows where 'est_multiple' is less than 0.51: {count}")

# Count rows where 'est_multiple' < 0.51 and 'title_score' < 0.4357
count = len(result_df[(result_df['est_multiple'] < 0.51) & (result_df['title_score'] < 0.4357)])
print(f"Number of rows where 'est_multiple' < 0.61 and 'title_score' < 0.4357: {count}")


# read csv from google drive to df
# def import_csv_from_drive(starts_with="product_table", google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn", chunk_size=None, on_chunk: Optional[Callable[[pd.DataFrame], Optional[pd.DataFrame]]] = None, return_combined: bool = True)
df_cv_score = import_csv_from_drive(starts_with="df_cv_score", google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn", chunk_size=5000)

# Joined SKU - Fix column name inconsistency
# After merge, columns are named sku_x and sku_y
if 'sku_x' in result_df.columns and 'sku_y' in result_df.columns:
    result_df['joined_sku'] = result_df['sku_x'].astype(str) + "_" + result_df['sku_y'].astype(str)
elif 'SKU' in result_df.columns and 'sku' in result_df.columns:
    result_df['joined_sku'] = result_df['SKU'].astype(str) + "_" + result_df['sku'].astype(str)
else:
    print("Warning: Could not find SKU columns for joined_sku creation")
    result_df['joined_sku'] = "unknown_unknown"

# Sort the DataFrame by 'title_score' in descending order
result_df = result_df.sort_values(by=['title_score'], ascending=False)

# drop duplicarte rows based on joined_sku and market
result_df = result_df.drop_duplicates(subset=['joined_sku', 'domain'], keep='first')

# merge result_df and  df_cv_score  on joined_sku  how= left
df_cv = pd.merge(result_df[['joined_sku','title_score','imgurl_x','imgurl_y','exclude']], df_cv_score[['joined_sku','cv_score']], on=['joined_sku'], how='outer')

# drop rows where imgurl_y is NaN
df_cv = df_cv.dropna(subset=['imgurl_y'])

# sort by cv_score
df_cv = df_cv.sort_values(by=['cv_score'], ascending=False)
df_cv = df_cv.drop_duplicates(subset=['joined_sku', 'imgurl_x','imgurl_y'])

# sort by title_score
df_cv = df_cv.sort_values(by=['title_score'], ascending=False)

# df_cv_0  = rows where cv_score is 0
df_cv_0 = df_cv[df_cv['cv_score'] == 0]
display(df_cv_0.head(5))

# keep rows where cv_score  is NaN
df_cv_nan = df_cv[df_cv['cv_score'].isna()]
# keep rows where title_score < 0.50
df_cv_nan = df_cv_nan[df_cv_nan['title_score'] < 0.50]

# display
display(df_cv_0.head(3))
display(df_cv_0.tail(3))
print(df_cv_0.shape)
print("df_cv_0")

# display
display(df_cv_nan.head(3))
display(df_cv_nan.tail(3))
print(df_cv_nan.shape)
print("df_cv_nan")


df_cv_test = df_cv_nan.head(40)

# in instances where  len(df_cv)  is 0 then   concat df_cv  and df_cv_score.head(2)
if len(df_cv_test) < 10:
    df_cv_test = pd.concat([df_cv_nan, df_cv_score.head(1), df_cv_0.head(10)]).reset_index(drop=True).sort_values(by=['cv_score'], na_position='last')



# Add the cv_score column to df_cv
df_cv_test = add_cv_scores(df_cv_test) # use the function from src/cv_similarity_score.py

# Now you can use df_cv with the new cv_score column
display(df_cv_test.head())
print(df_cv_test.shape)


# concat df_cv_score and df_cv_test
df_cv_score = pd.concat([df_cv_score, df_cv_test]).reset_index(drop=True).sort_values(by=['cv_score'], na_position='last')
# drop dulicate rows based on joined_sku
df_cv_score = df_cv_score.drop_duplicates(subset=['joined_sku'])


# in instances where title_score is less than 0.505  and cv_score  is less than 0.693  then ["exclude"] is 'yes'
df_cv_score.loc[(df_cv_score['title_score'] < 0.505) & (df_cv['cv_score'] < 0.666), 'exclude'] = 'yes'
df_cv_score.loc[(df_cv_score['cv_score'] > 0.005) & (df_cv_score['cv_score'] < 0.209), 'exclude'] = 'yes'
df_cv_score.loc[(df_cv_score['title_score'] > 0.725) & (df_cv_score['cv_score'] > 0.800), 'exclude'] = 'no'

display(df_cv_score[df_cv_score['exclude']=='no'])
display(df_cv_score[df_cv_score['exclude']=='yes'])
print(df_cv_score.shape)


# upsert df_cv_score to mysql
upsert_df_to_mysql(df_cv_score, engine, 'df_cv_score', 'joined_sku')


# merge result_df and  df_cv_score  on joined_sku  how= left
result_df = pd.merge(result_df, df_cv_score[['joined_sku','cv_score']], on=['joined_sku'], how='left')

# in instances  where [cv_score]  is > 0.905  then  [title_score]  + 0.15
result_df.loc[result_df['cv_score'] > 0.8295, 'title_score'] = result_df['title_score'] + 0.10
result_df.loc[result_df['cv_score'] > 0.910, 'title_score'] = result_df['title_score'] + 0.10

result_df.loc[(result_df['cv_score'] > 0.005) & (result_df['cv_score'] < 0.601) & (result_df['title_score'] < 0.401), 'exclude'] = 'yes'
result_df.loc[(result_df['cv_score'] > 0.005) & (result_df['cv_score'] < 0.42268) & (result_df['title_score'] < 0.5501), 'exclude'] = 'yes'



# Apply the condition

result_df.loc[
    (result_df['cv_score'] < 0.334) ,'exclude'] = 'yes'

# in instances where  cv_score == 0 then exclude = NaN
result_df.loc[(result_df['cv_score'] == 0 ), 'exclude'] = float('nan')


result_df.loc[
    (result_df['title_score'] < 0.334) ,'exclude'] = 'yes'


# Apply the next condition
result_df.loc[(result_df['title_score'] < 0.451) &
              (result_df['cv_score'] < 0.751),
              'exclude'] = 'yes'

result_df.loc[
    (result_df['title_score'] > 0.999) ,'exclude'] = 'no'

result_df.loc[
    (result_df['cv_score'] > 0.910) ,'exclude'] = 'no'


# Count rows where 'exclude' is blank
blank_exclude_count = result_df[result_df['exclude'] == ''].shape[0]
print(f"Number of rows where 'exclude' is blank: {blank_exclude_count}")

# Count rows where 'exclude' is blank
blank_exclude_count = result_df[result_df['exclude'] == 'yes'].shape[0]
print(f"Number of rows where 'exclude' is yes: {blank_exclude_count}")

# Count rows where 'exclude' is blank
blank_exclude_count = result_df[result_df['exclude'] == 'no'].shape[0]
print(f"Number of rows where 'exclude' is no: {blank_exclude_count}")


# Optimized loading of price_tracker_exceptions table
# Performance improvements:
# 1. Only load the 4 specific columns we need instead of the entire table
# 2. Filter by joined_sku values from result_df to only load relevant records
# 3. Use batch processing for large datasets to avoid SQL IN clause limits
# 4. This can reduce memory usage and query time significantly
try:
    # Get the unique joined_sku values from result_df to filter the query
    unique_joined_skus = result_df['joined_sku'].unique()
    print(f"Found {len(unique_joined_skus)} unique joined_sku values to filter price_tracker_exceptions")
    
    if len(unique_joined_skus) > 0:
        # Create a more efficient query that only selects needed columns and filters by joined_sku
        from sqlalchemy import text
        
        # Handle large datasets by batching the query if needed
        # Some databases have limits on IN clause size
        batch_size = 1000
        if len(unique_joined_skus) <= batch_size:
            # Single query for smaller datasets
            sku_tuple = tuple(unique_joined_skus)
            query = text(f"""
                SELECT joined_sku, exclude, multiple, est_multiple 
                FROM price_tracker_exceptions 
                WHERE joined_sku IN {sku_tuple}
            """)
            df_price_tracker_exceptions = pd.read_sql(query, engine)
        else:
            # Batch processing for larger datasets
            print(f"Large dataset detected ({len(unique_joined_skus)} records), using batch processing")
            df_price_tracker_exceptions = pd.DataFrame(columns=['joined_sku', 'exclude','multiple','est_multiple'])
            
            for i in range(0, len(unique_joined_skus), batch_size):
                batch_skus = unique_joined_skus[i:i + batch_size]
                sku_tuple = tuple(batch_skus)
                query = text(f"""
                    SELECT joined_sku, exclude, multiple, est_multiple 
                    FROM price_tracker_exceptions 
                    WHERE joined_sku IN {sku_tuple}
                """)
                batch_df = pd.read_sql(query, engine)
                df_price_tracker_exceptions = pd.concat([df_price_tracker_exceptions, batch_df], ignore_index=True)
        
        print(f"✅ Loaded {len(df_price_tracker_exceptions)} records from price_tracker_exceptions (optimized)")
    else:
        print("No joined_sku values found in result_df, creating empty DataFrame")
        df_price_tracker_exceptions = pd.DataFrame(columns=['joined_sku', 'exclude','multiple','est_multiple'])
        
except Exception as e:
    print(f"⚠️  price_tracker_exceptions table not found or error: {e}")
    print("Creating empty DataFrame for df_price_tracker_exceptions")
    df_price_tracker_exceptions = pd.DataFrame(columns=['joined_sku', 'exclude','multiple','est_multiple'])


# merge df_price_tracker_exceptions  and  df_cv_score
if not df_price_tracker_exceptions.empty:
    df_price_tracker_exceptions = pd.merge(df_price_tracker_exceptions, df_cv_score[['joined_sku','exclude']].rename(columns={'exclude': 'exclude_z'}), on='joined_sku', how='left')

    # in instances where exclude_z is not NaN then copy to exclude - use lambda
    df_price_tracker_exceptions['exclude'] = df_price_tracker_exceptions.apply(lambda row: row['exclude_z'] if pd.notna(row['exclude_z']) else row['exclude'], axis=1)
    
    # Check if these columns exist before trying to use them
    if 'exclude_y' in df_price_tracker_exceptions.columns:
        df_price_tracker_exceptions['exclude'] = df_price_tracker_exceptions.apply(lambda row: row['exclude_y'] if pd.notna(row['exclude_y']) else row['exclude'], axis=1)
    if 'multiple_y' in df_price_tracker_exceptions.columns:
        df_price_tracker_exceptions['multiple'] = df_price_tracker_exceptions.apply(lambda row: row['multiple_y'] if pd.notna(row['multiple_y']) else row['multiple'], axis=1)
    if 'est_multiple_y' in df_price_tracker_exceptions.columns:
        df_price_tracker_exceptions['est_multiple'] = df_price_tracker_exceptions.apply(lambda row: row['est_multiple_y'] if pd.notna(row['est_multiple_y']) else row['est_multiple'], axis=1)
else:
    print("df_price_tracker_exceptions is empty, skipping merge operations")

# drop columns - only drop columns that exist
columns_to_drop = ['exclude_y', 'multiple_y', 'est_multiple_y', 'exclude_z']
existing_columns_to_drop = [col for col in columns_to_drop if col in df_price_tracker_exceptions.columns]
if existing_columns_to_drop:
    df_price_tracker_exceptions = df_price_tracker_exceptions.drop(columns=existing_columns_to_drop)

# drop duplicate rows based on joined sku
df_price_tracker_exceptions = df_price_tracker_exceptions.drop_duplicates(subset=['joined_sku'])

# drop rows where joined_sku is NaN
df_price_tracker_exceptions = df_price_tracker_exceptions.dropna(subset=['joined_sku'])

print(df_price_tracker_exceptions.shape)
df_price_tracker_exceptions

# upsert df_price_tracker_exceptions to mysql
upsert_df_to_mysql(df_price_tracker_exceptions, engine, 'price_tracker_exceptions', 'joined_sku')


# drop column result_df[est_multiple]
result_df = result_df.drop(columns=['est_multiple'])

# Merge with df_price_tracker_exceptions
result_df = pd.merge(result_df, df_price_tracker_exceptions.rename(columns={'exclude': 'exclude_y'}), on=['joined_sku'], how='left')

result_df['exclude'] = result_df.apply(lambda row: row['exclude_y'] if pd.notna(row['exclude_y']) else row['exclude'], axis=1)

# drop columns
result_df = result_df.drop(columns=['exclude_y'])

# Sort the DataFrame by 'title_score' in descending order
result_df = result_df.sort_values(by=['title_score'], ascending=False)

# drop rows where exclude is yes
result_df = result_df[result_df['exclude'] != 'yes']

# Drop duplicate rows based on 'joined_sku', 'domain' keeping the first occurrence
# Fix column name - use sku_x instead of SKU after merge
if 'SKU' in result_df.columns:
    result_df = result_df.drop_duplicates(subset=['SKU', 'domain'], keep='first')
elif 'sku_x' in result_df.columns:
    result_df = result_df.drop_duplicates(subset=['sku_x', 'domain'], keep='first')
else:
    result_df = result_df.drop_duplicates(subset=['joined_sku', 'domain'], keep='first')
    print("Warning: Using joined_sku for deduplication as SKU columns not found")

# Display
display(result_df.columns)
display(result_df.head(3))
print(result_df.shape)

# @title Canada Main Results

# df_lowest_USA = rows where result_df['market'] is in [ Amazon US     Walmart US  Thrive Market  ]
df_lowest_USA = result_df[result_df['domain'].isin(['Amazon US', 'Walmart US', 'Thrive Market', "iHerb"])]

# df_lowest_result = drop rows where market is in .isin(['Amazon US', 'Walmart US', 'Thrive Market'])]
df_lowest_result = result_df[~result_df['domain'].isin(['Amazon US', 'Walmart US', 'Thrive Market' ,"iHerb" ])]

# Sort the DataFrame by 'price' - Fix column name references
if 'price_CAD' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.sort_values(by=['price_CAD'], ascending=True)
elif 'price' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.sort_values(by=['price'], ascending=True)
    print("Warning: price_CAD not found, using 'price' column instead")
else:
    print("Warning: No price column found for sorting")

# Fix SKU column reference - after merge, use sku_x
if 'SKU' in df_lowest_result.columns:
    sku_col = 'SKU'
elif 'sku_x' in df_lowest_result.columns:
    sku_col = 'sku_x'
elif 'sku' in df_lowest_result.columns:
    sku_col = 'sku'
else:
    sku_col = 'joined_sku'
    print("Warning: Using joined_sku for deduplication as SKU columns not found")

print(f"Using SKU column: {sku_col}")

df_lowest_result = df_lowest_result.drop_duplicates(subset=[sku_col])

# Initialize or update the specified columns in df_lowest_result


df_lowest_result['Natura (Image)'] = '=IMAGE("' + df_lowest_result['imgurl_x'].astype(str) + '")'
df_lowest_result['Competitor (Image)'] = '=IMAGE("' + df_lowest_result['imgurl_y'].astype(str) + '")'

# Fix SKU column references - use sku_x for Natura SKU (from the left side of the merge)
natura_sku_col = 'sku_x' if 'sku_x' in df_lowest_result.columns else ('SKU' if 'SKU' in df_lowest_result.columns else 'sku')
df_lowest_result['SKU - Natura'] = '=HYPERLINK("' + df_lowest_result['link_x'].astype(str) + '","' + df_lowest_result[natura_sku_col].astype(str) + '")'
# Use sku_y for competitor SKU (from the right side of the merge)
competitor_sku_col = 'sku_y' if 'sku_y' in df_lowest_result.columns else 'sku'
df_lowest_result['SKU - Competitor'] = '=HYPERLINK("' + df_lowest_result['link_y'].astype(str) + '","' + df_lowest_result[competitor_sku_col].astype(str) + '")'

df_lowest_result['Market'] = df_lowest_result['domain']
df_lowest_result['Name_y'] = df_lowest_result['title']
df_lowest_result['Margin'] = ""
# Fix price column reference
if 'price_CAD' in df_lowest_result.columns:
    df_lowest_result['Price: Competitor'] = df_lowest_result['price_CAD']
elif 'price' in df_lowest_result.columns:
    df_lowest_result['Price: Competitor'] = df_lowest_result['price']
    print("Warning: price_CAD not found, using 'price' column instead")
else:
    df_lowest_result['Price: Competitor'] = 0.0
    print("Warning: No price column found, setting to 0.0")
df_lowest_result['VAR_market'] = ""
df_lowest_result['VAR_30d'] = ""
# Fix date column reference - use current date if date column doesn't exist
if 'date' in df_lowest_result.columns:
    df_lowest_result['as of (date)'] = df_lowest_result['date']
else:
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    df_lowest_result['as of (date)'] = current_date
    print("Warning: 'date' column not found, using current date")
# Fix column references for 30-day data
if 'avg sold 30days' in df_lowest_result.columns:
    df_lowest_result['30D_sales_Natura'] = df_lowest_result['avg sold 30days']
elif 'l30d_sales' in df_lowest_result.columns:
    df_lowest_result['30D_sales_Natura'] = df_lowest_result['l30d_sales']
    print("Warning: 'avg sold 30days' not found, using 'l30d_sales' instead")
else:
    df_lowest_result['30D_sales_Natura'] = 0
    print("Warning: No 30-day sales column found, setting to 0")

if 'price_30d_avg' in df_lowest_result.columns:
    df_lowest_result['price_30d_avg'] = df_lowest_result['price_30d_avg']
    df_lowest_result['30d_Price'] = df_lowest_result['price_30d_avg']
elif 'price_30d_avg' in df_lowest_result.columns:
    df_lowest_result['price_30d_avg'] = df_lowest_result['price_30d_avg']
    df_lowest_result['30d_Price'] = df_lowest_result['price_30d_avg']
    print("Warning: 'price_30d_avg' not found, using 'price_30d_avg' instead")
else:
    df_lowest_result['price_30d_avg'] = 0.0
    df_lowest_result['30d_Price'] = 0.0
    print("Warning: No 30-day price column found, setting to 0.0")

# Reorder the columns - only include existing columns
desired_columns = ['Natura (Image)', 'Competitor (Image)', 'SKU - Natura', 'Market', 'SKU - Competitor', 'Brand', 'Name', 'Name_y', 'Cost', 'Price', 'Margin',
          '30D_sales_Natura', 'Price: Competitor', 'VAR_market', '30d_Price', 'VAR_30d', 'as of (date)', 'exclude', 'multiple', 'price_x', 'price_y',
          'title_score', 'vol_x', 'vol_y', 'joined_sku', 'est_multiple', 'price_30d_avg','price_CAD','USDCAD']

# Filter to only include columns that exist in the DataFrame
existing_columns = [col for col in desired_columns if col in df_lowest_result.columns]
print(f"Using {len(existing_columns)} out of {len(desired_columns)} desired columns")
match_df = df_lowest_result[existing_columns].copy()

# match_df to google sheet
upload_df_to_google_sheet(match_df, '1Ej_8fMh10w1TtKoGZidR1Lt5yP2Ws7iobrkMGKIEi0M', 'Canada_Shopping')


# @title USD Main Results

# df_lowest_USA = rows where result_df['domain'] is in [ Amazon US     Walmart US  Thrive Market  ]
df_lowest_USA = result_df[result_df['domain'].isin(['Amazon US', 'Walmart US', 'Thrive Market', "iHerb"])]

# Sort the DataFrame by 'price'
# Fix price column reference for USA data
if 'price_CAD' in df_lowest_USA.columns:
    df_lowest_USA = df_lowest_USA.sort_values(by=['price_CAD'], ascending=True)
elif 'price' in df_lowest_USA.columns:
    df_lowest_USA = df_lowest_USA.sort_values(by=['price'], ascending=True)
    print("Warning: price_CAD not found for USA data, using 'price' column instead")
else:
    print("Warning: No price column found for USA data sorting")
# Fix SKU column reference for USA data
if 'SKU' in df_lowest_USA.columns:
    df_lowest_USA = df_lowest_USA.drop_duplicates(subset=['SKU'])
elif 'sku_x' in df_lowest_USA.columns:
    df_lowest_USA = df_lowest_USA.drop_duplicates(subset=['sku_x'])
else:
    df_lowest_USA = df_lowest_USA.drop_duplicates(subset=['joined_sku'])
    print("Warning: Using joined_sku for USA data deduplication as SKU columns not found")

# Initialize or update the specified columns in df_lowest_USA
df_lowest_USA['Natura (Image)'] = '=IMAGE("' + df_lowest_USA['imgurl_x'].astype(str) + '")'
df_lowest_USA['Competitor (Image)'] = '=IMAGE("' + df_lowest_USA['imgurl_y'].astype(str) + '")'

# Fix SKU column reference for USA data
usa_natura_sku_col = 'sku_x' if 'sku_x' in df_lowest_USA.columns else ('SKU' if 'SKU' in df_lowest_USA.columns else 'sku')
df_lowest_USA['SKU - Natura'] = '=HYPERLINK("' + df_lowest_USA['link_x'].astype(str) + '","' + df_lowest_USA[usa_natura_sku_col].astype(str) + '")'
# Use sku_y for competitor SKU (from the right side of the merge)
usa_competitor_sku_col = 'sku_y' if 'sku_y' in df_lowest_USA.columns else 'sku'
df_lowest_USA['SKU - Competitor'] = '=HYPERLINK("' + df_lowest_USA['link_y'].astype(str) + '","' + df_lowest_USA[usa_competitor_sku_col].astype(str) + '")'

df_lowest_USA['Market'] = df_lowest_USA['domain']
df_lowest_USA['Name_y'] = df_lowest_USA['title']
df_lowest_USA['Margin'] = ""
# Fix price column reference for USA data
if 'price_CAD' in df_lowest_USA.columns:
    df_lowest_USA['Price: Competitor'] = df_lowest_USA['price_CAD']
elif 'price' in df_lowest_USA.columns:
    df_lowest_USA['Price: Competitor'] = df_lowest_USA['price']
    print("Warning: price_CAD not found for USA data, using 'price' column instead")
else:
    df_lowest_USA['Price: Competitor'] = 0.0
    print("Warning: No price column found for USA data, setting to 0.0")
df_lowest_USA['VAR_market'] = ""
df_lowest_USA['VAR_30d'] = ""
# Fix date column reference for USA data
if 'date' in df_lowest_USA.columns:
    df_lowest_USA['as of (date)'] = df_lowest_USA['date']
else:
    from datetime import datetime
    current_date = datetime.now().strftime('%Y-%m-%d')
    df_lowest_USA['as of (date)'] = current_date
    print("Warning: 'date' column not found for USA data, using current date")

# Fix 30-day sales column reference for USA data
if 'avg sold 30days' in df_lowest_USA.columns:
    df_lowest_USA['30D_sales_Natura'] = df_lowest_USA['avg sold 30days']
elif 'l30d_sales' in df_lowest_USA.columns:
    df_lowest_USA['30D_sales_Natura'] = df_lowest_USA['l30d_sales']
    print("Warning: 'avg sold 30days' not found for USA data, using 'l30d_sales' instead")
else:
    df_lowest_USA['30D_sales_Natura'] = 0
    print("Warning: No 30-day sales column found for USA data, setting to 0")

# Fix 30-day price column reference for USA data
if 'price_30d_avg' in df_lowest_USA.columns:
    df_lowest_USA['price_30d_avg'] = df_lowest_USA['price_30d_avg']
elif 'price_30d_avg' in df_lowest_USA.columns:
    df_lowest_USA['price_30d_avg'] = df_lowest_USA['price_30d_avg']
    print("Warning: 'price_30d_avg' not found for USA data, using 'price_30d_avg' instead")
else:
    df_lowest_USA['price_30d_avg'] = 0.0
    print("Warning: No 30-day price column found for USA data, setting to 0.0")
df_lowest_USA['30d_Price'] = df_lowest_USA['price_30d_avg']

# Reorder the columns - only include existing columns
desired_columns_usa = ['Natura (Image)', 'Competitor (Image)', 'SKU - Natura', 'Market', 'SKU - Competitor', 'Brand', 'Name', 'Name_y', 'Cost', 'Price', 'Margin',
          '30D_sales_Natura', 'Price: Competitor', 'VAR_market', '30d_Price', 'VAR_30d', 'as of (date)', 'exclude', 'multiple', 'price_x', 'price_y',
          'title_score', 'vol_x', 'vol_y', 'joined_sku', 'est_multiple', 'price_30d_avg','price_CAD','USDCAD']

# Filter to only include columns that exist in the DataFrame
existing_columns_usa = [col for col in desired_columns_usa if col in df_lowest_USA.columns]
print(f"Using {len(existing_columns_usa)} out of {len(desired_columns_usa)} desired columns for USA data")
match_df = df_lowest_USA[existing_columns_usa].copy()

# match_df to google sheet
upload_df_to_google_sheet(match_df, '1Ej_8fMh10w1TtKoGZidR1Lt5yP2Ws7iobrkMGKIEi0M', 'USA_Shopping')

# Computing Margin where Price > 0
# Fix price column references for diff calculation
if 'price_x' in df_lowest_result.columns and 'price_y' in df_lowest_result.columns:
    df_lowest_result['diff'] = df_lowest_result.apply(lambda row: row['price_y'] - row['price_x'] if row['price_x'] > 0 else None, axis=1)
elif 'price' in df_lowest_result.columns:
    df_lowest_result['diff'] = 0  # No comparison possible with single price column
    print("Warning: price_x/price_y not found, setting diff to 0")
else:
    df_lowest_result['diff'] = 0
    print("Warning: No price columns found, setting diff to 0")

df_lowest_result['compare_with'] = '=HYPERLINK("' + df_lowest_result['link_y'].astype(str) + '","' + df_lowest_result['domain'].astype(str) + '")'

#  rename price column to 'Compare' if it exists
if 'price_CAD' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.rename(columns={'price_CAD': 'Compare'})
elif 'price' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.rename(columns={'price': 'Compare'})
    print("Warning: price_CAD not found, renaming 'price' to 'Compare'")
else:
    print("Warning: No price column found to rename")


# merge df_natura_sku_summary  and df_lowest_result on "SKU"
# Fix column name mismatch - use actual column names from df_natura_sku_summary
print("Available columns in df_natura_sku_summary:", df_natura_sku_summary.columns.tolist())
print("Available columns in df_lowest_result:", df_lowest_result.columns.tolist())

# Use actual column names that exist
natura_cols = ['sku', 'name', 'l30d_sales', 'cost', 'price', 'margin', 'wtd_avg_margin']
existing_natura_cols = [col for col in natura_cols if col in df_natura_sku_summary.columns]
print(f"Using natura columns: {existing_natura_cols}")

result_cols = ['sku_x', 'compare_with', 'Compare', 'diff', 'as of (date)']
existing_result_cols = [col for col in result_cols if col in df_lowest_result.columns]
print(f"Using result columns: {existing_result_cols}")

# Merge on the correct SKU column
if 'sku' in df_natura_sku_summary.columns and 'sku_x' in df_lowest_result.columns:
    df_lowest_result = pd.merge(df_natura_sku_summary[existing_natura_cols], df_lowest_result[existing_result_cols], left_on='sku', right_on='sku_x', how='left')
else:
    print("Warning: Cannot merge - SKU columns don't match")
    df_lowest_result = df_lowest_result

# sort by [Store Name]  NaN rows last (if column exists)
if 'Store Name' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.sort_values(by=['Store Name'], na_position='last')

# drop duplicates by SKU
# Fix SKU column reference for final deduplication
if 'SKU' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.drop_duplicates(subset=['SKU'])
elif 'sku' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.drop_duplicates(subset=['sku'])
elif 'sku_x' in df_lowest_result.columns:
    df_lowest_result = df_lowest_result.drop_duplicates(subset=['sku_x'])
else:
    df_lowest_result = df_lowest_result.drop_duplicates(subset=['joined_sku'])
    print("Warning: Using joined_sku for final deduplication as SKU columns not found")

# sort by Name
df_lowest_result = df_lowest_result.sort_values(by=['name'])
display(df_lowest_result.head())
print(df_lowest_result.shape)


# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
healthy_planet = result_df[result_df['domain'] == 'Healthy Planet']
# rename healthy_planet[price_CAD]  to "Healthy Planet" - check if price_CAD exists
if 'price_CAD' in healthy_planet.columns:
    healthy_planet = healthy_planet.rename(columns={'price_CAD': 'Healthy Planet'})
    # keep columns [SKU, Healthy Planet] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in healthy_planet.columns else 'SKU'
    healthy_planet = healthy_planet[[sku_col, 'Healthy Planet']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Healthy Planet, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in healthy_planet.columns else 'SKU'
    healthy_planet = healthy_planet[[sku_col]].rename(columns={sku_col: 'SKU'})
    healthy_planet['Healthy Planet'] = None

# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
Well = result_df[result_df['domain'] == 'Well']
# rename Well[price_CAD] to "Well" - check if price_CAD exists
if 'price_CAD' in Well.columns:
    Well = Well.rename(columns={'price_CAD': 'Well'})
    # keep columns [SKU, Well] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in Well.columns else 'SKU'
    Well = Well[[sku_col, 'Well']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Well, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in Well.columns else 'SKU'
    Well = Well[[sku_col]].rename(columns={sku_col: 'SKU'})
    Well['Well'] = None



# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
NatureSante = result_df[result_df['domain'] == 'NatureSante']
# rename NatureSante[price_CAD] to "NatureSante" - check if price_CAD exists
if 'price_CAD' in NatureSante.columns:
    NatureSante = NatureSante.rename(columns={'price_CAD': 'NatureSante'})
    # keep columns [SKU, NatureSante] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in NatureSante.columns else 'SKU'
    NatureSante = NatureSante[[sku_col, 'NatureSante']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for NatureSante, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in NatureSante.columns else 'SKU'
    NatureSante = NatureSante[[sku_col]].rename(columns={sku_col: 'SKU'})
    NatureSante['NatureSante'] = None

# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
Goodness_Me = result_df[result_df['domain'] == 'Goodness Me']
# rename Goodness_Me[price_CAD] to "Goodness Me" - check if price_CAD exists
if 'price_CAD' in Goodness_Me.columns:
    Goodness_Me = Goodness_Me.rename(columns={'price_CAD': 'Goodness Me'})
    # keep columns [SKU, Goodness Me] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in Goodness_Me.columns else 'SKU'
    Goodness_Me = Goodness_Me[[sku_col, 'Goodness Me']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Goodness Me, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in Goodness_Me.columns else 'SKU'
    Goodness_Me = Goodness_Me[[sku_col]].rename(columns={sku_col: 'SKU'})
    Goodness_Me['Goodness Me'] = None



# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
Amazon_US = result_df[result_df['domain'] == 'Amazon US']
# rename Amazon_US[price_CAD] to "Amazon US" - check if price_CAD exists
if 'price_CAD' in Amazon_US.columns:
    Amazon_US = Amazon_US.rename(columns={'price_CAD': 'Amazon US'})
    # keep columns [SKU, Amazon US] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in Amazon_US.columns else 'SKU'
    Amazon_US = Amazon_US[[sku_col, 'Amazon US']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Amazon US, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in Amazon_US.columns else 'SKU'
    Amazon_US = Amazon_US[[sku_col]].rename(columns={sku_col: 'SKU'})
    Amazon_US['Amazon US'] = None

# Assuming 'result_df' is your DataFrame and it has a column named 'Market'
Thrive_Market = result_df[result_df['domain'] == 'Thrive Market']
# rename Thrive_Market[price_CAD] to "Thrive Market" - check if price_CAD exists
if 'price_CAD' in Thrive_Market.columns:
    Thrive_Market = Thrive_Market.rename(columns={'price_CAD': 'Thrive Market'})
    # keep columns [SKU, Thrive Market] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in Thrive_Market.columns else 'SKU'
    Thrive_Market = Thrive_Market[[sku_col, 'Thrive Market']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Thrive Market, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in Thrive_Market.columns else 'SKU'
    Thrive_Market = Thrive_Market[[sku_col]].rename(columns={sku_col: 'SKU'})
    Thrive_Market['Thrive Market'] = None


# rename df_lowest_USA[market] to [US Stores]
df_lowest_USA = df_lowest_USA.rename(columns={ 'high_CAD': 'high' , 'low_CAD': 'low', 'as of (date)': '(date)' })

df_lowest_USA['US Stores'] = '=HYPERLINK("' + df_lowest_USA['link_y'].astype(str) + '","' + df_lowest_USA['domain'].astype(str) + '")'

df_lowest_USA['Diff_CAD'] = df_lowest_USA.apply(lambda row: row['price_y'] - row['price_x'] if row['price_x'] > 0 else None, axis=1)

# Check which columns actually exist in df_lowest_USA
available_columns = df_lowest_USA.columns.tolist()
print("Available columns in df_lowest_USA:", available_columns)

# Build column_order with only existing columns
column_order = []
for col in ['SKU', 'US Stores', 'price_CAD', 'Diff_CAD', "high", "low", '(date)']:
    if col in available_columns:
        column_order.append(col)
    else:
        print(f"Warning: Column '{col}' not found in df_lowest_USA")

print("Using columns for SKU_USA:", column_order)

# Assuming 'match_df' is your DataFrame
SKU_USA = df_lowest_USA[column_order] if column_order else df_lowest_USA

# Create Walmart_US DataFrame (missing from original script)
Walmart_US = result_df[result_df['domain'] == 'Walmart US']
# rename Walmart_US[price_CAD] to "Walmart US" - check if price_CAD exists
if 'price_CAD' in Walmart_US.columns:
    Walmart_US = Walmart_US.rename(columns={'price_CAD': 'Walmart US'})
    # keep columns [SKU, Walmart US] - use sku_x as the SKU column
    sku_col = 'sku_x' if 'sku_x' in Walmart_US.columns else 'SKU'
    Walmart_US = Walmart_US[[sku_col, 'Walmart US']].rename(columns={sku_col: 'SKU'})
else:
    print("Warning: price_CAD column not found for Walmart US, creating empty DataFrame")
    sku_col = 'sku_x' if 'sku_x' in Walmart_US.columns else 'SKU'
    Walmart_US = Walmart_US[[sku_col]].rename(columns={sku_col: 'SKU'})
    Walmart_US['Walmart US'] = None

# Calculate total_sold_30_days for weighted average margin calculation
total_sold_30_days = df_natura_sku_summary['avg sold 30days'].sum() if 'avg sold 30days' in df_natura_sku_summary.columns else 1

# Determine the correct SKU column name for merging
sku_col_for_merge = 'sku_x' if 'sku_x' in df_lowest_result.columns else 'SKU'
print(f"Using '{sku_col_for_merge}' as the SKU column for merging")

# merge df_lowest result and healthy_planet
Summary_Result = pd.merge(df_lowest_result, healthy_planet, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_hp'))
# Well
Summary_Result = pd.merge(Summary_Result, Well, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_well'))
# NatureSante
Summary_Result = pd.merge(Summary_Result, NatureSante, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_ns'))
# Goodness Me
Summary_Result = pd.merge(Summary_Result, Goodness_Me, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_gm'))
# lowest USA - check if SKU_USA has SKU column
if 'SKU' in SKU_USA.columns:
    Summary_Result = pd.merge(Summary_Result, SKU_USA, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_usa'))
else:
    print("Warning: SKU_USA doesn't have SKU column, skipping USA merge")
# Thrive Market
Summary_Result = pd.merge(Summary_Result, Thrive_Market, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_tm'))
# Walmart US
Summary_Result = pd.merge(Summary_Result, Walmart_US, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_walmart'))
# Amazon US
Summary_Result = pd.merge(Summary_Result, Amazon_US, left_on=sku_col_for_merge, right_on='SKU', how='left', suffixes=('', '_amazon'))


# Apply the condition using .loc (fix column name references)
if 'Store Name' in Summary_Result.columns and 'Compare' in Summary_Result.columns:
    Summary_Result.loc[Summary_Result['compare_with'].notna(), 'price change'] = Summary_Result.loc[Summary_Result['compare_with'].notna(), 'price'] - 0.20

# Fix column name: 'price_change' should be 'Price Change'
if 'Price Change' in Summary_Result.columns and 'cost' in Summary_Result.columns:
    Summary_Result['new_margin'] = ((Summary_Result['price change'] - Summary_Result['cost']) / Summary_Result['price change']) * 100
    Summary_Result['new_margin'] = Summary_Result['new_margin'].round(2)
else:
    print("Warning: Required columns for new_margin calculation not found, setting to 0")
    Summary_Result['new_margin'] = 0

# Calculate 'WA Margin' (fix column name: 'l30d_sales' should be 'avg sold 30days')
if 'avg sold 30days' in Summary_Result.columns and 'new_margin' in Summary_Result.columns:
    Summary_Result['new_wa_margin'] = (Summary_Result['new_margin'] * Summary_Result['avg sold 30days']) / total_sold_30_days
    Summary_Result['new_wa_margin'] = Summary_Result['new_wa_margin'].round(2) # round
else:
    print("Warning: Required columns for new_wa_margin calculation not found, setting to 0")
    Summary_Result['new_wa_margin'] = 0

# Applying the condition: add % sign only to positive values
if 'new_margin' in Summary_Result.columns:
    Summary_Result['new_margin'] = Summary_Result['new_margin'].astype(str) + "%"
if 'new_wa_margin' in Summary_Result.columns:
    Summary_Result['new_wa_margin'] = Summary_Result['new_wa_margin'].astype(str) + "%"

# in instances where [New WA Margin] str includes "nan%"' then set to ""
Summary_Result['new_wa_margin'] = Summary_Result['new_wa_margin'].str.replace('nan%', '')
Summary_Result['new_margin'] = Summary_Result['new_margin'].str.replace('nan%', '')

# Fix column names and create proper list
columns_to_keep = ['sku', 'name', 'brand', 'avg sold 30days', 'cost', 'price_x', 'margin', 'wtd_avg_margin', 
                   'compare_with', 'price_y', 'diff', 'price change', 'new_margin', 'new_wa_margin', 'as of (date)', 
                   'healthy planet', 'well', 'naturesante', 'goodness me', 'thrive market', 'walmart us', 'amazon us']

# Filter to only include columns that exist in the DataFrame
existing_columns = [col for col in columns_to_keep if col in Summary_Result.columns]
Summary_Result = Summary_Result[existing_columns]


# drop rows where Price is 0 - check which price column exists
if 'Price' in Summary_Result.columns:
    Summary_Result = Summary_Result[Summary_Result['Price'] > 0]
elif 'price_x' in Summary_Result.columns:
    Summary_Result = Summary_Result[Summary_Result['price_x'] > 0]
    print("Using price_x column for filtering")
else:
    print("Warning: No price column found for filtering, keeping all rows")


display(Summary_Result.head())
display(Summary_Result.tail())
print(Summary_Result.columns)
print(Summary_Result.shape)


# df to google sheet
upload_df_to_google_sheet(Summary_Result, '1wQ-A-FYELPvvwE4zHB6E-XI1DnPHhaqV6TyHroEFMOQ', 'price_data')





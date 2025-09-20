#!/usr/bin/env python3
"""
Test script to read all CSV files from a test folder
that start with 'shiphero_line_items'
"""

import pandas as pd
import os
import glob
from pathlib import Path

def read_shiphero_csvs():
    """
    Read all CSV files from the specified folder that start with 'shiphero_line_items'
    """
    # Define the target folder path (using local test folder)
    folder_path = "/home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/healthyplanet/test_data/shiphero_test"
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder not found: {folder_path}")
        print("Please check if the drive is mounted and path is correct.")
        return None
    
    # Create pattern to match files starting with 'shiphero_line_items'
    pattern = os.path.join(folder_path, "shiphero_line_items*.csv")
    
    # Find all matching CSV files
    csv_files = glob.glob(pattern)
    
    if not csv_files:
        print(f"No CSV files found starting with 'shiphero_line_items' in: {folder_path}")
        return None
    
    print(f"Found {len(csv_files)} CSV file(s) matching pattern:")
    for file in csv_files:
        print(f"  - {os.path.basename(file)}")
    
    # Dictionary to store all dataframes
    dataframes = {}
    
    # Read each CSV file
    for csv_file in csv_files:
        try:
            filename = os.path.basename(csv_file)
            print(f"\nReading {filename}...")
            
            # Read CSV file
            df = pd.read_csv(csv_file)
            
            # Store in dictionary with filename as key
            dataframes[filename] = df
            
            print(f"  ✓ Successfully loaded {filename}")
            print(f"    Shape: {df.shape}")
            print(f"    Columns: {list(df.columns)}")
            
        except Exception as e:
            print(f"  ✗ Error reading {filename}: {e}")
            continue
    
    return dataframes

def combine_dataframes(dataframes):
    """
    Combine all dataframes into a single dataframe
    """
    if not dataframes:
        print("No dataframes to combine")
        return None
    
    print(f"\nCombining {len(dataframes)} dataframes...")
    
    try:
        # Combine all dataframes
        combined_df = pd.concat(dataframes.values(), ignore_index=True)
        
        print(f"✓ Combined dataframe shape: {combined_df.shape}")
        print(f"  Total rows: {len(combined_df)}")
        print(f"  Columns: {list(combined_df.columns)}")
        
        return combined_df
        
    except Exception as e:
        print(f"✗ Error combining dataframes: {e}")
        return None

def main():
    """
    Main function to execute the CSV reading process
    """
    print("=" * 60)
    print("ShipHero CSV Reader - TEST VERSION")
    print("=" * 60)
    
    # Read all matching CSV files
    dataframes = read_shiphero_csvs()
    
    if dataframes is None or not dataframes:
        print("No data to process. Exiting.")
        return
    
    # Display summary of each file
    print("\n" + "=" * 60)
    print("FILE SUMMARY")
    print("=" * 60)
    
    for filename, df in dataframes.items():
        print(f"\n{filename}:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB")
        
        # Show first few rows
        print(f"  First 3 rows:")
        print(df.head(3).to_string(index=False))
    
    # Combine the data
    print("\n" + "=" * 60)
    print("COMBINING DATA")
    print("=" * 60)
    
    combined_df = combine_dataframes(dataframes)
    
    if combined_df is not None:
        print(f"\nCombined data preview:")
        print(combined_df.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    main()

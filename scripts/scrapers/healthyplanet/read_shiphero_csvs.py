#!/usr/bin/env python3
"""
Script to read all CSV files from D:\\Users\\mrbun\\ShipHero_Data_Local\\ShipHero Data
that start with 'shiphero_line_items'
"""

import pandas as pd
import os
import glob
from pathlib import Path

def read_shiphero_csvs(folder_path=None):
    """
    Read all CSV files from the specified folder that start with 'shiphero_line_items'
    
    Args:
        folder_path (str): Path to the folder containing CSV files. If None, tries multiple common paths.
    """
    # Define possible folder paths (try in order)
    possible_paths = [
        folder_path,  # User-specified path
        r"D:\Users\mrbun\ShipHero_Data_Local\ShipHero Data",  # Original Windows path
        r"C:\Users\mrbun\Google Drive\ShipHero Data",  # Google Drive Desktop Sync (Windows)
        r"C:\Users\mrbun\Google Drive\My Drive\ShipHero Data",  # Alternative Google Drive path
        "/home/mongreldatalab/Google Drive/ShipHero Data",  # Google Drive Desktop Sync (Linux)
        "/home/mongreldatalab/Google Drive/My Drive/ShipHero Data",  # Alternative Google Drive path
        r"\\YOUR_COMPUTER_NAME\ShipHero_Data_Local\ShipHero Data",  # Network share (replace YOUR_COMPUTER_NAME)
        r"\\YOUR_IP_ADDRESS\ShipHero_Data_Local\ShipHero Data",  # Network share by IP (replace YOUR_IP_ADDRESS)
        "/home/mongreldatalab/shiphero_data/",  # Local VM path
        "/mnt/shiphero_data/",  # Mounted drive path
        "./shiphero_data/",  # Relative path in current directory
    ]
    
    # Find the first existing path
    target_folder = None
    for path in possible_paths:
        if path and os.path.exists(path):
            target_folder = path
            break
    
    if target_folder is None:
        print("Error: No accessible folder found. Tried the following paths:")
        for path in possible_paths:
            if path:
                print(f"  - {path}")
        print("\nPlease:")
        print("1. Copy files to the VM's local storage, or")
        print("2. Set up network file sharing, or")
        print("3. Provide the correct path as an argument")
        return None
    
    folder_path = target_folder
    
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

def save_combined_data(combined_df, output_folder=None):
    """
    Save the combined dataframe to a new CSV file
    """
    if combined_df is None:
        print("No data to save")
        return
    
    # Default output folder (same as input)
    if output_folder is None:
        output_folder = r"D:\Users\mrbun\ShipHero_Data_Local\ShipHero Data"
    
    # Create output filename with timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"shiphero_line_items_combined_{timestamp}.csv"
    output_path = os.path.join(output_folder, output_filename)
    
    try:
        combined_df.to_csv(output_path, index=False)
        print(f"✓ Combined data saved to: {output_path}")
    except Exception as e:
        print(f"✗ Error saving combined data: {e}")

def main():
    """
    Main function to execute the CSV reading process
    """
    print("=" * 60)
    print("ShipHero CSV Reader")
    print("=" * 60)
    
    # You can specify a custom path here if needed
    custom_path = None  # Set to your actual path if needed, e.g., "/home/mongreldatalab/shiphero_data/"
    
    # Read all matching CSV files
    dataframes = read_shiphero_csvs(custom_path)
    
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
    
    # Ask user if they want to combine the data
    print("\n" + "=" * 60)
    print("OPTIONS")
    print("=" * 60)
    
    choice = input("\nDo you want to combine all dataframes into one? (y/n): ").lower().strip()
    
    if choice in ['y', 'yes']:
        combined_df = combine_dataframes(dataframes)
        
        if combined_df is not None:
            save_choice = input("\nDo you want to save the combined data? (y/n): ").lower().strip()
            if save_choice in ['y', 'yes']:
                save_combined_data(combined_df)
    
    print("\n" + "=" * 60)
    print("PROCESS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script to read CSV files from Google Drive using PyDrive2
"""

import pandas as pd
import os
import io
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile

def authenticate_google_drive():
    """
    Authenticate with Google Drive using PyDrive2
    """
    gauth = GoogleAuth()
    
    # Try to load saved client credentials
    gauth.LoadCredentialsFile("credentials.json")
    
    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()
    else:
        # Initialize the saved creds
        gauth.Authorize()
    
    # Save the current credentials to a file
    gauth.SaveCredentialsFile("credentials.json")
    
    return GoogleDrive(gauth)

def find_folder_by_name(drive, folder_name):
    """
    Find a folder by name in Google Drive
    """
    # Search for folders with the exact name
    query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    
    if not file_list:
        print(f"No folder found with name: {folder_name}")
        return None
    
    if len(file_list) > 1:
        print(f"Multiple folders found with name '{folder_name}':")
        for i, folder in enumerate(file_list):
            print(f"  {i+1}. {folder['title']} (ID: {folder['id']})")
        return file_list[0]  # Return first match
    
    return file_list[0]

def list_csv_files_in_folder(drive, folder_id, prefix="shiphero_line_items"):
    """
    List all CSV files in a Google Drive folder that start with prefix
    """
    # Search for CSV files in the folder
    query = f"'{folder_id}' in parents and title contains '.csv' and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    
    # Filter files that start with the prefix
    matching_files = [f for f in file_list if f['title'].startswith(prefix)]
    
    return matching_files

def download_csv_from_drive(drive, file_id, file_name):
    """
    Download a CSV file from Google Drive
    """
    try:
        file_obj = drive.CreateFile({'id': file_id})
        file_obj.GetContentFile(file_name)  # Download to local file
        
        # Read the downloaded file
        df = pd.read_csv(file_name)
        
        # Clean up the temporary file
        os.remove(file_name)
        
        return df
    except Exception as e:
        print(f"Error downloading {file_name}: {e}")
        return None

def read_shiphero_csvs_from_drive(folder_name="ShipHero Data"):
    """
    Read all CSV files from Google Drive folder that start with 'shiphero_line_items'
    """
    try:
        # Authenticate
        print("Authenticating with Google Drive...")
        drive = authenticate_google_drive()
        
        # Find the folder
        print(f"Looking for folder: {folder_name}")
        folder = find_folder_by_name(drive, folder_name)
        if not folder:
            return None
        
        print(f"Found folder: {folder['title']} (ID: {folder['id']})")
        
        # List CSV files in the folder
        print("Searching for CSV files starting with 'shiphero_line_items'...")
        csv_files = list_csv_files_in_folder(drive, folder['id'], "shiphero_line_items")
        
        if not csv_files:
            print("No files found starting with 'shiphero_line_items'")
            
            # Show all CSV files for debugging
            all_csv_files = list_csv_files_in_folder(drive, folder['id'], "")
            if all_csv_files:
                print("Available CSV files in folder:")
                for f in all_csv_files:
                    print(f"  - {f['title']}")
            else:
                print("No CSV files found in the folder")
            return None
        
        print(f"Found {len(csv_files)} ShipHero CSV file(s):")
        for f in csv_files:
            print(f"  - {f['title']} ({f['fileSize']} bytes)")
        
        # Download and process each file
        dataframes = {}
        for file_info in csv_files:
            print(f"\nDownloading {file_info['title']}...")
            df = download_csv_from_drive(drive, file_info['id'], file_info['title'])
            
            if df is not None:
                dataframes[file_info['title']] = df
                print(f"  ✓ Successfully loaded {file_info['title']}")
                print(f"    Shape: {df.shape}")
                print(f"    Columns: {list(df.columns)}")
            else:
                print(f"  ✗ Failed to load {file_info['title']}")
        
        return dataframes
        
    except Exception as e:
        print(f"Error accessing Google Drive: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have 'credentials.json' in the same folder")
        print("2. Check your internet connection")
        print("3. Verify the folder name exists in Google Drive")
        return None

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

def save_combined_data(combined_df, output_folder="./"):
    """
    Save the combined dataframe to a new CSV file
    """
    if combined_df is None:
        print("No data to save")
        return
    
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
    Main function to execute the Google Drive CSV reading process
    """
    print("=" * 60)
    print("PyDrive2 ShipHero CSV Reader")
    print("=" * 60)
    
    # Read all matching CSV files from Google Drive
    dataframes = read_shiphero_csvs_from_drive("ShipHero Data")
    
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

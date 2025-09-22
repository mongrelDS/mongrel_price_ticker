#!/usr/bin/env python3
"""
Script to read CSV files from Google Drive folder using Google Drive API
"""

import pandas as pd
import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_google_drive():
    """
    Authenticate with Google Drive API
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def find_folder_by_name(service, folder_name):
    """
    Find a folder by name in Google Drive
    """
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        print(f"No folder found with name: {folder_name}")
        return None
    
    if len(items) > 1:
        print(f"Multiple folders found with name '{folder_name}':")
        for i, item in enumerate(items):
            print(f"  {i+1}. {item['name']} (ID: {item['id']})")
        return items[0]  # Return first match
    
    return items[0]

def list_csv_files_in_folder(service, folder_id):
    """
    List all CSV files in a Google Drive folder
    """
    query = f"'{folder_id}' in parents and mimeType='text/csv' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name, size)").execute()
    items = results.get('files', [])
    
    return items

def download_csv_from_drive(service, file_id, file_name):
    """
    Download a CSV file from Google Drive
    """
    try:
        request = service.files().get_media(fileId=file_id)
        file_content = request.execute()
        
        # Convert bytes to string and create DataFrame
        content_str = file_content.decode('utf-8')
        df = pd.read_csv(io.StringIO(content_str))
        
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
        creds = authenticate_google_drive()
        service = build('drive', 'v3', credentials=creds)
        
        # Find the folder
        print(f"Looking for folder: {folder_name}")
        folder = find_folder_by_name(service, folder_name)
        if not folder:
            return None
        
        print(f"Found folder: {folder['name']} (ID: {folder['id']})")
        
        # List CSV files in the folder
        print("Searching for CSV files...")
        csv_files = list_csv_files_in_folder(service, folder['id'])
        
        if not csv_files:
            print("No CSV files found in the folder")
            return None
        
        # Filter files that start with 'shiphero_line_items'
        shiphero_files = [f for f in csv_files if f['name'].startswith('shiphero_line_items')]
        
        if not shiphero_files:
            print("No files found starting with 'shiphero_line_items'")
            print("Available CSV files:")
            for f in csv_files:
                print(f"  - {f['name']}")
            return None
        
        print(f"Found {len(shiphero_files)} ShipHero CSV file(s):")
        for f in shiphero_files:
            print(f"  - {f['name']} ({f['size']} bytes)")
        
        # Download and process each file
        dataframes = {}
        for file_info in shiphero_files:
            print(f"\nDownloading {file_info['name']}...")
            df = download_csv_from_drive(service, file_info['id'], file_info['name'])
            
            if df is not None:
                dataframes[file_info['name']] = df
                print(f"  ✓ Successfully loaded {file_info['name']}")
                print(f"    Shape: {df.shape}")
                print(f"    Columns: {list(df.columns)}")
            else:
                print(f"  ✗ Failed to load {file_info['name']}")
        
        return dataframes
        
    except Exception as e:
        print(f"Error accessing Google Drive: {e}")
        return None

def main():
    """
    Main function to execute the Google Drive CSV reading process
    """
    print("=" * 60)
    print("Google Drive ShipHero CSV Reader")
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
    
    print("\n" + "=" * 60)
    print("PROCESS COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    main()


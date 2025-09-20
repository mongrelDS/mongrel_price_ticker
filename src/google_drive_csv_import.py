# Google Drive CSV Import Function
# Import necessary libraries
import pandas as pd
import io
import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Import centralized functions from the same directory
from cleanup_column_names import clean_column_names

def import_csv_from_drive(starts_with="product_table", google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"):
    """
    Import CSV files from Google Drive folder and return as a combined DataFrame.
    
    Args:
        starts_with (str or list): String or list of strings to match file prefixes
        google_drive_id (str): Google Drive folder ID containing the CSV files
    
    Returns:
        pandas.DataFrame: Combined DataFrame with all matching CSV data
    """
    
    # --- AUTHENTICATION (SERVICE ACCOUNT) ---
    # Path to your service account key file (relative to project root)
    key_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'tactical-elf-452207-m9-1f0520891d95.json')
    
    # Define the required scope
    scopes = ['https://www.googleapis.com/auth/drive']
    
    # Authenticate using the service account credentials
    try:
        credentials = Credentials.from_service_account_file(key_file_path, scopes=scopes)
        service = build('drive', 'v3', credentials=credentials)
        print("✅ Authentication successful using Service Account.")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None
    
    # --- CONFIGURATION ---
    # Convert starts_with to list if it's a string
    if isinstance(starts_with, str):
        csv_starts_with = [starts_with]
    else:
        csv_starts_with = starts_with
    
    # --- HELPER FUNCTIONS ---
    def get_files_from_folder(folder_id):
        """Get files from Google Drive folder using the Drive API v3"""
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields='nextPageToken, files(id, name, mimeType)').execute()
        return results.get('files', [])
    
    def matches_prefix(filename, prefixes):
        """Check if filename starts with any of the given prefixes"""
        return any(filename.startswith(prefix) for prefix in prefixes)
    
    def download_file_content(file_id):
        """Download file content from Google Drive"""
        try:
            file_content = service.files().get_media(fileId=file_id).execute()
            return file_content.decode('utf-8')
        except Exception as e:
            print(f"    Error downloading file {file_id}: {e}")
            return None
    
    # --- MAIN PROCESSING ---
    all_dfs = []
    
    print(f"\nProcessing folder: {google_drive_id}")
    files = get_files_from_folder(google_drive_id)
    matching_csvs = [
        file for file in files if file['name'].endswith('.csv') and
        matches_prefix(file['name'], csv_starts_with)
    ]
    print(f"Found {len(matching_csvs)} matching CSV file(s) in this folder.")
    
    for file in matching_csvs:
        print(f"  -> Reading file: {file['name']} ({file['id']})")
        file_content = download_file_content(file['id'])
        if file_content:
            try:
                df = pd.read_csv(io.StringIO(file_content), low_memory=False)
                all_dfs.append(df)
                print(f"    ✅ Successfully loaded {df.shape[0]} rows, {df.shape[1]} columns")
            except Exception as e:
                print(f"    ❌ Could not read file {file['name']}. Error: {e}")
    
    # --- FINAL OUTPUT ---
    if all_dfs:
        # Concatenate all DataFrames
        combined_df = pd.concat(all_dfs, ignore_index=True)
        print(f"\n✅ Success! Concatenated {len(all_dfs)} file(s) into DataFrame.")
        print(f"Shape: {combined_df.shape}")
        print(f"Original columns: {list(combined_df.columns)}")
        
        # Clean column names
        combined_df = clean_column_names(combined_df)
        print("✅ Column names cleaned for database compatibility.")
        print(f"Cleaned columns: {list(combined_df.columns)}")
        
        # Show data summary
        print(f"\nData Summary:")
        print(f"Total rows: {len(combined_df)}")
        print(f"Total columns: {len(combined_df.columns)}")
        print(f"\nFirst 5 rows:")
        print(combined_df.head())
        
        print(f"\nData types:")
        print(combined_df.dtypes)
        
        # Check for missing values
        print(f"\nMissing values per column:")
        print(combined_df.isnull().sum())
        
        print(f"\n✅ CSV processing completed successfully!")
        print(f"Processed data is ready for further use or export.")
        
        return combined_df
        
    else:
        print("\n⚠️ No matching CSV files were found to create a DataFrame.")
        return None

# Example usage:
if __name__ == "__main__":
    # Example 1: Using default parameters
    df1 = import_csv_from_drive()
    
    # Example 2: Using custom parameters
    df2 = import_csv_from_drive(
        starts_with="product_table",
        google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
    )
    
    # Example 3: Using multiple prefixes
    df3 = import_csv_from_drive(
        starts_with=["product_table", "ALL_Products"],
        google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
    )
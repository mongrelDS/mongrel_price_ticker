# Google Drive CSV Import Function
# Import necessary libraries
import pandas as pd
import io
import os
import sys
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from typing import Callable, Optional
from dotenv import load_dotenv
import json

# Import centralized functions
from cleanup_column_names import clean_column_names

def import_csv_from_drive(starts_with="product_table", google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn", chunk_size=None, on_chunk: Optional[Callable[[pd.DataFrame], Optional[pd.DataFrame]]] = None, return_combined: bool = True):
    """
    Import CSV files from Google Drive folder and return as a combined DataFrame.
    
    Args:
        starts_with (str or list): String or list of strings to match file prefixes
        google_drive_id (str): Google Drive folder ID containing the CSV files
        chunk_size (int | None): If provided, read CSVs in chunks of this size to reduce memory usage
        on_chunk (callable | None): Optional callback applied to each chunk. If provided, each chunk
            is passed to this function; it may return a transformed DataFrame or None. When set,
            you can set return_combined=False to avoid accumulating all rows in memory.
        return_combined (bool): When chunking, control whether to accumulate chunks into a final
            DataFrame to return. For best memory usage set to False when on_chunk is provided.
    
    Returns:
        pandas.DataFrame | None: Combined DataFrame with all matching CSV data, or None if
            return_combined is False and processing is delegated to on_chunk.
    """
    
    # --- AUTHENTICATION (SERVICE ACCOUNT) ---
    # Load environment variables from .env file
    load_dotenv()
    
    # Get the credentials from environment variables
    # Prefer inline JSON via GOOGLE_APPLICATION_CREDENTIALS_JSON; fallback to file path via GOOGLE_APPLICATION_CREDENTIALS
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    # Fallback: if JSON not provided but a file path is, read it
    if not credentials_json and credentials_path:
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                credentials_json = f.read()
        except Exception as e:
            print(f"⚠️ Could not read credentials from GOOGLE_APPLICATION_CREDENTIALS='{credentials_path}': {e}")
            credentials_json = None

    # Final fallback: use project credentials JSON file if present
    if not credentials_json:
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            default_key_path = os.path.join(
                repo_root,
                'credentials',
                'tactical-elf-452207-m9-1f0520891d95.json'
            )
            
            if not os.path.isfile(default_key_path):
                print(f"❌ Service account key not found at: {default_key_path}")
                print("📋 Please follow the setup instructions in credentials/README.md")
                return None
            
            with open(default_key_path, 'r', encoding='utf-8') as f:
                credentials_json = f.read()
            
            # Check if the file contains placeholder values
            if 'PLACEHOLDER' in credentials_json:
                print(f"⚠️  Credentials file contains placeholder values: {default_key_path}")
                print("📋 Please replace with actual service account credentials (see credentials/README.md)")
                return None
            
            print("🔑 Loaded service account credentials from project credentials directory.")
        except Exception as e:
            print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON/GOOGLE_APPLICATION_CREDENTIALS not set and project credentials file not found.")
            print(f"   Details: {e}")
            print("📋 Please follow the setup instructions in credentials/README.md")
            return None
        
    try:
        credentials_info = json.loads(credentials_json)
    except Exception as e:
        print(f"⚠️ Invalid GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        return None

    # Define the required scope
    scopes = ['https://www.googleapis.com/auth/drive']
    
    # Authenticate using the service account credentials
    try:
        credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
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
    # When chunk_size is provided, stream rows to avoid storing multiple DataFrames at once
    all_dfs = []
    
    print(f"\nProcessing folder: {google_drive_id}")
    files = get_files_from_folder(google_drive_id)
    matching_csvs = [
        file for file in files if file['name'].endswith('.csv') and
        matches_prefix(file['name'], csv_starts_with)
    ]
    print(f"Found {len(matching_csvs)} matching CSV file(s) in this folder.")
    
    import gc
    combined_df = None if chunk_size else []  # placeholder when chunking

    for file in matching_csvs:
        print(f"  -> Reading file: {file['name']} ({file['id']})")
        file_content = download_file_content(file['id'])
        if file_content:
            try:
                if chunk_size:
                    # Stream in chunks
                    for chunk in pd.read_csv(io.StringIO(file_content), chunksize=chunk_size, low_memory=False):
                        # Optionally clean column names per chunk to keep schema consistent
                        try:
                            chunk = clean_column_names(chunk)
                        except Exception:
                            pass

                        if on_chunk is not None:
                            try:
                                processed = on_chunk(chunk)
                            except Exception as e:
                                print(f"    ⚠️ on_chunk processing failed: {e}")
                                processed = None

                            if return_combined:
                                material = processed if processed is not None else chunk
                                if combined_df is None:
                                    combined_df = material.copy()
                                else:
                                    combined_df = pd.concat([combined_df, material], ignore_index=True)
                            # Encourage early memory release
                            del processed
                        else:
                            # Accumulate into combined_df when not using callback
                            if combined_df is None:
                                combined_df = chunk
                            else:
                                combined_df = pd.concat([combined_df, chunk], ignore_index=True)

                        # Encourage early memory release
                        del chunk
                        gc.collect()
                else:
                    df = pd.read_csv(io.StringIO(file_content), low_memory=False)
                    all_dfs.append(df)
                    print(f"    ✅ Successfully loaded {df.shape[0]} rows, {df.shape[1]} columns")
            except Exception as e:
                print(f"    ❌ Could not read file {file['name']}. Error: {e}")
    
    # --- FINAL OUTPUT ---
    # If chunking was enabled, combined_df may already be built incrementally
    if (chunk_size and isinstance(combined_df, pd.DataFrame)) or (not chunk_size and all_dfs):
        # Concatenate only when not chunking
        if not chunk_size:
            combined_df = pd.concat(all_dfs, ignore_index=True)
        print(f"\n✅ Success! Concatenated {len(matching_csvs)} file(s) into DataFrame.")
        print(f"Shape: {combined_df.shape}")
        print(f"Original columns: {list(combined_df.columns)}")
        
        # Clean column names if not already cleaned while chunking
        try:
            combined_df = clean_column_names(combined_df)
            print("✅ Column names cleaned for database compatibility.")
            print(f"Cleaned columns: {list(combined_df.columns)}")
        except Exception:
            pass
        
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


def import_csv_from_drive_iter(starts_with="product_table", google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn", chunk_size=10000):
    """
    Iterator version of the Drive CSV importer. Yields cleaned chunks one-by-one.

    Args:
        starts_with (str or list): File name prefixes to include
        google_drive_id (str): Drive folder ID
        chunk_size (int): Chunk size for streaming CSV reads

    Yields:
        pandas.DataFrame: Each processed chunk as a DataFrame
    """
    # --- AUTHENTICATION (SERVICE ACCOUNT) ---
    load_dotenv()
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if not credentials_json and credentials_path:
        try:
            with open(credentials_path, 'r', encoding='utf-8') as f:
                credentials_json = f.read()
        except Exception as e:
            print(f"⚠️ Could not read credentials from GOOGLE_APPLICATION_CREDENTIALS='{credentials_path}': {e}")
            credentials_json = None

    if not credentials_json:
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            default_key_path = os.path.join(
                repo_root,
                'credentials',
                'tactical-elf-452207-m9-1f0520891d95.json'
            )
            with open(default_key_path, 'r', encoding='utf-8') as f:
                credentials_json = f.read()
            print("🔑 Loaded service account credentials from project credentials directory (iterator).")
        except Exception as e:
            print("⚠️ GOOGLE_APPLICATION_CREDENTIALS_JSON/GOOGLE_APPLICATION_CREDENTIALS not set and project credentials file not found (iterator).")
            print(f"   Details: {e}")
            return

    try:
        credentials_info = json.loads(credentials_json)
    except Exception as e:
        print(f"⚠️ Invalid GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
        return
    
    scopes = ['https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    service = build('drive', 'v3', credentials=credentials)

    # Normalize prefixes
    if isinstance(starts_with, str):
        csv_starts_with = [starts_with]
    else:
        csv_starts_with = starts_with

    def get_files_from_folder(folder_id):
        query = f"'{folder_id}' in parents and trashed=false"
        results = service.files().list(q=query, fields='nextPageToken, files(id, name, mimeType)').execute()
        return results.get('files', [])

    def matches_prefix(filename, prefixes):
        return any(filename.startswith(prefix) for prefix in prefixes)

    def download_file_content(file_id):
        try:
            file_content = service.files().get_media(fileId=file_id).execute()
            return file_content.decode('utf-8')
        except Exception as e:
            print(f"    Error downloading file {file_id}: {e}")
            return None

    print(f"\nProcessing folder: {google_drive_id}")
    files = get_files_from_folder(google_drive_id)
    matching_csvs = [file for file in files if file['name'].endswith('.csv') and matches_prefix(file['name'], csv_starts_with)]
    print(f"Found {len(matching_csvs)} matching CSV file(s) in this folder.")

    import gc
    for file in matching_csvs:
        print(f"  -> Streaming file: {file['name']} ({file['id']})")
        content = download_file_content(file['id'])
        if not content:
            continue
        try:
            for chunk in pd.read_csv(io.StringIO(content), chunksize=chunk_size, low_memory=False):
                try:
                    chunk = clean_column_names(chunk)
                except Exception:
                    pass
                yield chunk
                del chunk
                gc.collect()
        except Exception as e:
            print(f"    ❌ Could not stream file {file['name']}. Error: {e}")

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
"""
Google Sheets to DataFrame Converter

This module provides a function to read data from Google Sheets into pandas DataFrames.
It handles authentication and data retrieval internally using service account credentials.
"""

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials
import pandas as pd
import os

# Define the required scope for Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


def sheets_to_dataframe(sheet_name, data_range, spreadsheet_id, key_file_path=None):
    """
    Reads data from a Google Sheet into a pandas DataFrame using service account credentials.
    
    Args:
        sheet_name (str): The name of the sheet within the spreadsheet.
        data_range (str): The range in A1 notation (e.g., 'O1:FQ1').
        spreadsheet_id (str): The ID of the Google Sheet.
        key_file_path (str, optional): Path to the service account key file. 
                                     Defaults to the same path used in other scripts.
    
    Returns:
        pandas.DataFrame: A DataFrame containing the imported data,
                          or an empty DataFrame if the range is empty or an error occurs.
    """
    # Set default key file path if not provided (same as other scripts)
    if key_file_path is None:
        key_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'tactical-elf-452207-m9-1f0520891d95.json')
    
    # Check if credentials file exists and is valid
    if not os.path.isfile(key_file_path):
        print(f"❌ Service account key not found at: {key_file_path}")
        print("📋 Please follow the setup instructions in credentials/README.md")
        return pd.DataFrame()
    
    # Check if the file contains placeholder values
    try:
        with open(key_file_path, 'r') as f:
            content = f.read()
            if 'PLACEHOLDER' in content:
                print(f"⚠️  Credentials file contains placeholder values: {key_file_path}")
                print("📋 Please replace with actual service account credentials (see credentials/README.md)")
                return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return pd.DataFrame()
    
    # Authenticate using service account credentials
    try:
        credentials = Credentials.from_service_account_file(key_file_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Authentication successful using Service Account.")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("📋 Please check your credentials file and setup (see credentials/README.md)")
        return pd.DataFrame()
    
    try:
        # Construct the full range
        full_range = f"'{sheet_name}'!{data_range}"
        
        print(f"Importing data from range '{full_range}'...")
        
        # Call the Sheets API to get the values from the spreadsheet
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=full_range
        ).execute()
        
        # Extract values from the API response
        values = result.get('values', [])
        
        if not values:
            print("No data found in the specified range.")
            return pd.DataFrame()
        
        # Create the DataFrame, using the first row as the header
        # and subsequent rows as the data.
        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)
        
        print(f"SUCCESS: Imported {len(df)} rows into a DataFrame.")
        return df
        
    except HttpError as error:
        # The API encountered a problem.
        print(f'An API error occurred: {error}')
        # Parse the error message to provide more specific advice
        error_details = error.resp.get('content', '{}')
        if 'Unable to parse range' in error_details:
            print("Hint: Make sure your sheet name in the data range is correct and doesn't contain typos.")
        return pd.DataFrame()
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        return pd.DataFrame()


# Example usage:
# df_week_columns = sheets_to_dataframe(
#     sheet_name='week count',
#     data_range='O1:FQ1',
#     spreadsheet_id='14RyPMn-Az2c2Zvrj-IzDZL9hrgo_U93GYmpPfzuXYMU'
# )


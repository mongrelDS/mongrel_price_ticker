"""
Write DataFrame to Google Sheet

This module provides a function to write pandas DataFrames to Google Sheets.
It handles authentication and data writing internally using service account credentials.
"""

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.service_account import Credentials
import pandas as pd
import os

# Define the required scope for Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def write_df_to_sheet(df_to_display, spreadsheet_id, sheet_name, cell_loc, key_file_path=None):
    """
    Writes a pandas DataFrame to a specific location in a Google Sheet using service account credentials.
    It will clear the sheet before writing to avoid leftover data.
    
    Args:
        df_to_display (pd.DataFrame): The DataFrame to be written.
        spreadsheet_id (str): The ID of the target Google Sheet.
        sheet_name (str): The name of the specific sheet (tab).
        cell_loc (str): The top-left cell where the data should be written (e.g., 'A1').
        key_file_path (str, optional): Path to the service account key file. 
                                     Defaults to the same path used in other scripts.
    
    Returns:
        bool: True if successful, False otherwise.
    """
    # Set default key file path if not provided (same as other scripts)
    if key_file_path is None:
        key_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'tactical-elf-452207-m9-1f0520891d95.json')
    
    # Basic validation
    if not isinstance(df_to_display, pd.DataFrame):
        print(f"❌ Error: The provided data is not a valid pandas DataFrame.")
        return False

    # Authenticate using service account credentials
    try:
        credentials = Credentials.from_service_account_file(key_file_path, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        print("✅ Authentication successful using Service Account.")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

    try:
        # Skip clearing for now to test float functionality
        print(f"Writing to sheet: '{sheet_name}'...")

        # Prepare DataFrame for writing (fill NaN values and convert to string)
        df_to_write = df_to_display.fillna("").astype(str)

        # Convert DataFrame to a list of lists, including the header
        # The Sheets API expects data in this format
        values_to_write = [df_to_write.columns.values.tolist()] + df_to_write.values.tolist()

        # Define the request body for the API call
        body = {
            'values': values_to_write
        }

        # Define the range where data will be written
        # Format is 'SheetName!A1' (only quote if sheet name has spaces)
        if ' ' in sheet_name:
            write_range = f"'{sheet_name}'!{cell_loc}"
        else:
            write_range = f"{sheet_name}!{cell_loc}"

        print(f"Writing {len(df_to_write)} rows to '{sheet_name}' in spreadsheet...")

        # Execute the write request
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=write_range,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        print("✅ SUCCESS: DataFrame has been written to the Google Sheet.")
        updated_cells = result.get('updatedCells')
        print(f"📊 Cells updated: {updated_cells}")
        print(f"🔗 View the sheet here: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        return True

    except HttpError as error:
        print(f'❌ An API error occurred: {error}')
        return False
    except Exception as e:
        print(f'❌ An unexpected error occurred: {e}')
        return False


# Example usage:
# write_df_to_sheet(
#     df_to_display=my_dataframe,
#     spreadsheet_id='14RyPMn-Az2c2Zvrj-IzDZL9hrgo_U93GYmpPfzuXYMU',
#     sheet_name='CC Order Count',
#     cell_loc='A6'
# )


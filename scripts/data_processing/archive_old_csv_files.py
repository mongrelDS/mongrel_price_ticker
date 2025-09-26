# @title Find and Move Old CSV Files to Archive
from googleapiclient.errors import HttpError
from datetime import datetime, timezone, timedelta
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd

# Database utilities
import sys
import importlib.util
_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if _SRC_DIR not in sys.path:
    sys.path.append(_SRC_DIR)

# Dynamically import DB utilities to avoid static import issues in script context
def _import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_mysql_upsert_mod = _import_from_path('mysql_upsert_mod', os.path.join(_SRC_DIR, 'mySQL_Upsert_Function_with_Batch.py'))
_db_config_mod = _import_from_path('db_config_mod', os.path.join(_SRC_DIR, 'database_config.py'))
upsert_df_to_mysql = getattr(_mysql_upsert_mod, 'upsert_df_to_mysql')
get_database_engine = getattr(_db_config_mod, 'get_database_engine')

def archive_old_csv_files(drive_service, source_folder_id, target_folder_id, file_prefixes, hours_old):
    """
    Finds CSV files in a source folder that match given prefixes and are older
    than a specified number of hours, then moves them to a target folder.

    Args:
        drive_service: The authenticated Google Drive service object.
        source_folder_id (str): The ID of the folder to search for files.
        target_folder_id (str): The ID of the folder to move old files to.
        file_prefixes (list): A list of filename prefixes to search for.
        hours_old (int): The age in hours a file must be to be archived.
    """
    # 1. Basic validation
    if drive_service is None:
        print("Error: 'drive_service' is not defined. Please run the initialization cell first.")
        return

    print(f"Searching for files older than {hours_old} hour(s) to archive...")
    now_utc = datetime.now(timezone.utc)
    time_threshold = timedelta(hours=hours_old)
    files_moved = 0

    # 2. Iterate through each specified file prefix
    for prefix in file_prefixes:
        try:
            query = f"'{source_folder_id}' in parents and name starts with '{prefix}' and mimeType='text/csv' and trashed=false"
            # We must request 'createdTime' to check the file's age
            results = drive_service.files().list(
                q=query,
                fields="files(id, name, createdTime)").execute()
            file_list = results.get('files', [])

            if not file_list:
                print(f"- No files found with prefix '{prefix}'.")
                continue

            # 3. Process each found file to check its age
            for file in file_list:
                file_name = file.get('name')
                file_id = file.get('id')
                created_time_str = file.get('createdTime')

                # Convert the API's time string to a timezone-aware datetime object
                created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))

                # 4. If the file is older than the threshold, move it
                if now_utc - created_time > time_threshold:
                    print(f"- Found old file: '{file_name}'. Moving to archive...")
                    # Use files().update to move the file by changing its parent folder
                    drive_service.files().update(
                        fileId=file_id,
                        addParents=target_folder_id,
                        removeParents=source_folder_id,
                        fields='id, parents'
                    ).execute()
                    files_moved += 1
                else:
                    print(f"- Found recent file: '{file_name}'. Skipping.")

        except HttpError as error:
            print(f"An API error occurred while processing prefix '{prefix}': {error}")
            continue

    print(f"\nArchive process complete. Moved {files_moved} file(s).")
    return files_moved


# --- Helpers ---
def build_drive_service_from_service_account():
    """
    Initialize and return a Google Drive service using a service account.

    Respects GOOGLE_APPLICATION_CREDENTIALS if set; otherwise falls back to the
    repository credentials path.
    """
    key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not key_path:
        # Compute repo root: scripts/data_processing/ -> repo root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        key_path = os.path.join(
            repo_root,
            'credentials',
            'tactical-elf-452207-m9-1f0520891d95.json'
        )

    scopes = ['https://www.googleapis.com/auth/drive']
    try:
        if not os.path.isfile(key_path):
            print(f"❌ Service account key not found at: {key_path}")
            print("📋 Please follow the setup instructions in credentials/README.md")
            print("🔧 You can also set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            return None

        # Check if the file contains placeholder values
        with open(key_path, 'r') as f:
            content = f.read()
            if 'PLACEHOLDER' in content:
                print(f"⚠️  Credentials file contains placeholder values: {key_path}")
                print("📋 Please replace with actual service account credentials (see credentials/README.md)")
                return None

        credentials = Credentials.from_service_account_file(key_path, scopes=scopes)
        # Disable discovery cache to avoid cron permission/cache issues
        service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
        print("✅ Initialized Drive service via service account.")
        return service
    except Exception as e:
        print(f"❌ Failed to initialize Drive service: {e}")
        print("📋 Please check your credentials file and setup (see credentials/README.md)")
        return None


# --- Parameters ---
source_folder_id = '1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn' # @param {type:"string"}
target_folder = '1Ew47OLqEvax77ue-y_V10yMpOf_eY8MT' # @param {type:"string"}
csv_starts_with = ['product_table' ,  "line_items_table" ,  "inventory" ,  "ship_orders_table",'df_product_table'] # @param {type:"raw"}
hours_to_archive = 1 # @param {type:"integer"}


# --- Execution ---
# Check if an existing Drive service is provided; otherwise, build one
timestamp_0 = datetime.now()

if locals().get('drive_service') is not None:
    _svc = locals().get('drive_service')
else:
    _svc = build_drive_service_from_service_account()

files_archived = None
if _svc is None:
    print("Execution skipped: could not initialize Google Drive service.")
else:
    files_archived = archive_old_csv_files(_svc, source_folder_id, target_folder, csv_starts_with, hours_to_archive)

# --- Duration and DB upsert ---
try:
    timestamp_1 = datetime.now()
    duration = timestamp_1 - timestamp_0
    duration_in_minutes = duration.total_seconds() / 60

    results_count = int(files_archived) if isinstance(files_archived, int) else 0
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes],
        'date': [datetime.now()],
        'results': [results_count],
        'result_per_minute': [results_count / duration_in_minutes if duration_in_minutes > 0 else 0.0],
        'domain': ['google_drive'],
        'type': ['archive_csv']
    })

    db_engine = get_database_engine()
    upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
    print("Successfully upserted duration data to 'duration' table")
except Exception as e:
    print(f"Failed to upsert duration data: {e}")
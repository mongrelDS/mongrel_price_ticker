# @title Find and Move Old CSV Files to Archive
from googleapiclient.errors import HttpError
from datetime import datetime, timezone, timedelta

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


# --- Parameters ---
source_folder_id = '1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn' # @param {type:"string"}
target_folder = '1Ew47OLqEvax77ue-y_V10yMpOf_eY8MT' # @param {type:"string"}
csv_starts_with = ['product_table' ,  "line_items_table" ,  "inventory" ,  "ship_orders_table",'df_product_table'] # @param {type:"raw"}
hours_to_archive = 1 # @param {type:"integer"}


# --- Execution ---
# Check if the necessary service variable exists
if 'drive_service' in locals() and drive_service is not None:
    archive_old_csv_files(drive_service, source_folder_id, target_folder, csv_starts_with, hours_to_archive)
else:
    print("Execution skipped: 'drive_service' not found. Please run the initialization cell first.")
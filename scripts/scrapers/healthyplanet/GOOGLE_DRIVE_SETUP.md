# Google Drive API Setup Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements_google_drive.txt
```

## Step 2: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Drive API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

## Step 3: Create Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Choose "Desktop application"
4. Download the JSON file
5. Rename it to `credentials.json` and place it in the same folder as the script

## Step 4: Run the Script

```bash
python3 google_drive_csv_reader.py
```

The first time you run it, it will:
1. Open a browser window for authentication
2. Ask you to sign in to Google
3. Ask for permission to access your Drive
4. Save the token for future use

## Alternative Methods

### Method 2: Google Drive Desktop Sync
If you have Google Drive desktop app installed:
1. Sync your folder to local storage
2. Use the local file path in the original script

### Method 3: Google Drive File Stream
1. Install Google Drive File Stream
2. Access files via mounted drive path
3. Update the script to use the mounted path

### Method 4: PyDrive (Simpler but deprecated)
```python
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

# Simpler but less reliable
```

## Troubleshooting

- **Authentication issues**: Delete `token.pickle` and re-authenticate
- **Permission errors**: Make sure the folder is shared with your Google account
- **File not found**: Check the exact folder name in Google Drive
- **API quota exceeded**: Wait or request quota increase

## Security Notes

- Never commit `credentials.json` or `token.pickle` to version control
- Use read-only scope for security
- Consider using service account for production


# PyDrive2 Setup Guide

## Step 1: Install Dependencies

```bash
pip install -r requirements_pydrive2.txt
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
python3 pydrive2_csv_reader.py
```

The first time you run it, it will:
1. Open a browser window for authentication
2. Ask you to sign in to Google
3. Ask for permission to access your Drive
4. Save the credentials for future use

## Troubleshooting

### Common Issues:

1. **"No module named 'pydrive2'"**
   ```bash
   pip install PyDrive2
   ```

2. **"credentials.json not found"**
   - Make sure the file is in the same folder as the script
   - Check the filename is exactly `credentials.json`

3. **"Access denied" or "Permission denied"**
   - Delete `credentials.json` and re-authenticate
   - Make sure the folder is shared with your Google account

4. **"Folder not found"**
   - Check the exact folder name in Google Drive
   - Make sure the folder is in your Google Drive (not shared with you)

### File Structure:
```
your_project/
├── pydrive2_csv_reader.py
├── credentials.json          # Download from Google Cloud Console
├── requirements_pydrive2.txt
└── PYDRIVE2_SETUP.md
```

## Security Notes

- Never commit `credentials.json` to version control
- The script only requests read-only access
- Credentials are stored locally and encrypted

## Features

- ✅ Simple authentication
- ✅ Automatic file discovery
- ✅ Downloads CSV files on-demand
- ✅ Combines multiple files
- ✅ Saves combined data locally
- ✅ Error handling and troubleshooting

#!/usr/bin/env python3
"""
Setup script to help configure Google Drive access
"""

import os
import webbrowser
from urllib.parse import urlencode

def print_setup_instructions():
    """
    Print detailed setup instructions
    """
    print("=" * 60)
    print("Google Drive Setup Instructions")
    print("=" * 60)
    print()
    print("Step 1: Create Google Cloud Project")
    print("-" * 40)
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Click 'Select a project' → 'New Project'")
    print("3. Enter project name: 'ShipHero CSV Reader'")
    print("4. Click 'Create'")
    print()
    
    print("Step 2: Enable Google Drive API")
    print("-" * 40)
    print("1. In the project, go to 'APIs & Services' → 'Library'")
    print("2. Search for 'Google Drive API'")
    print("3. Click on it and press 'Enable'")
    print()
    
    print("Step 3: Create Credentials")
    print("-" * 40)
    print("1. Go to 'APIs & Services' → 'Credentials'")
    print("2. Click 'Create Credentials' → 'OAuth client ID'")
    print("3. If prompted, configure OAuth consent screen:")
    print("   - Choose 'External' user type")
    print("   - Fill in app name: 'ShipHero CSV Reader'")
    print("   - Add your email as test user")
    print("4. Choose 'Desktop application'")
    print("5. Name it: 'ShipHero CSV Reader Client'")
    print("6. Click 'Create'")
    print("7. Download the JSON file")
    print("8. Rename it to 'credentials.json'")
    print("9. Place it in this folder:", os.getcwd())
    print()
    
    print("Step 4: Test the Setup")
    print("-" * 40)
    print("1. Run: python3 pydrive2_csv_reader.py")
    print("2. A browser window will open for authentication")
    print("3. Sign in with your Google account")
    print("4. Grant permission to access Google Drive")
    print()

def check_credentials_file():
    """
    Check if credentials file exists
    """
    credentials_file = "credentials.json"
    
    if os.path.exists(credentials_file):
        print(f"✅ Found {credentials_file}")
        return True
    else:
        print(f"❌ {credentials_file} not found")
        return False

def open_google_cloud_console():
    """
    Open Google Cloud Console in browser
    """
    try:
        webbrowser.open("https://console.cloud.google.com/")
        print("🌐 Opening Google Cloud Console in your browser...")
    except Exception as e:
        print(f"Could not open browser: {e}")
        print("Please manually go to: https://console.cloud.google.com/")

def main():
    """
    Main setup function
    """
    print("🚀 Google Drive Setup Helper")
    print()
    
    # Check if credentials already exist
    if check_credentials_file():
        print("✅ Credentials file found! You can run the script now.")
        print("Run: python3 pydrive2_csv_reader.py")
        return
    
    print("📋 Setup required. Follow these steps:")
    print()
    
    print_setup_instructions()
    
    # Ask if user wants to open Google Cloud Console
    choice = input("Would you like to open Google Cloud Console now? (y/n): ").lower().strip()
    if choice in ['y', 'yes']:
        open_google_cloud_console()
    
    print("\n" + "=" * 60)
    print("Next Steps:")
    print("=" * 60)
    print("1. Complete the setup steps above")
    print("2. Download and place 'credentials.json' in this folder")
    print("3. Run: python3 pydrive2_csv_reader.py")
    print()
    print("Current folder:", os.getcwd())

if __name__ == "__main__":
    main()


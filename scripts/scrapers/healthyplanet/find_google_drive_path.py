#!/usr/bin/env python3
"""
Script to help find the correct Google Drive path for your system
"""

import os
import platform

def find_google_drive_paths():
    """
    Find possible Google Drive paths on the current system
    """
    system = platform.system()
    username = os.getenv('USER', os.getenv('USERNAME', 'unknown'))
    
    print("=" * 60)
    print("Google Drive Path Finder")
    print("=" * 60)
    print(f"System: {system}")
    print(f"Username: {username}")
    print()
    
    # Common Google Drive paths
    possible_paths = []
    
    if system == "Windows":
        possible_paths = [
            f"C:\\Users\\{username}\\Google Drive\\ShipHero Data",
            f"C:\\Users\\{username}\\Google Drive\\My Drive\\ShipHero Data",
            f"C:\\Users\\{username}\\Google Drive\\My Drive\\Public Data Projects\\Natura\\ShipHero Data",
            f"D:\\Users\\{username}\\Google Drive\\ShipHero Data",
            f"D:\\Users\\{username}\\Google Drive\\My Drive\\ShipHero Data",
        ]
    elif system == "Darwin":  # macOS
        possible_paths = [
            f"/Users/{username}/Google Drive/ShipHero Data",
            f"/Users/{username}/Google Drive/My Drive/ShipHero Data",
            f"/Users/{username}/Google Drive/My Drive/Public Data Projects/Natura/ShipHero Data",
        ]
    else:  # Linux
        possible_paths = [
            f"/home/{username}/Google Drive/ShipHero Data",
            f"/home/{username}/Google Drive/My Drive/ShipHero Data",
            f"/home/{username}/Google Drive/My Drive/Public Data Projects/Natura/ShipHero Data",
            f"/home/{username}/google-drive/ShipHero Data",
            f"/home/{username}/google-drive/My Drive/ShipHero Data",
        ]
    
    print("Checking for Google Drive paths...")
    print()
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ FOUND: {path}")
            found_paths.append(path)
            
            # Check for CSV files
            try:
                csv_files = [f for f in os.listdir(path) if f.endswith('.csv')]
                if csv_files:
                    print(f"   📁 Contains {len(csv_files)} CSV files:")
                    for csv_file in csv_files[:5]:  # Show first 5
                        print(f"      - {csv_file}")
                    if len(csv_files) > 5:
                        print(f"      ... and {len(csv_files) - 5} more")
                else:
                    print("   📁 No CSV files found")
            except Exception as e:
                print(f"   ❌ Error reading directory: {e}")
        else:
            print(f"❌ Not found: {path}")
        print()
    
    if found_paths:
        print("=" * 60)
        print("RECOMMENDED PATHS")
        print("=" * 60)
        for i, path in enumerate(found_paths, 1):
            print(f"{i}. {path}")
        
        print("\nTo use with your script:")
        print("1. Copy one of the paths above")
        print("2. Update the script with:")
        print("   custom_path = r'YOUR_CHOSEN_PATH'")
        print("3. Or the script will automatically find it!")
    else:
        print("=" * 60)
        print("NO GOOGLE DRIVE PATHS FOUND")
        print("=" * 60)
        print("Please:")
        print("1. Install Google Drive Desktop app")
        print("2. Sign in and sync your folder")
        print("3. Run this script again")
        print()
        print("Alternative: Check if Google Drive is installed in a different location")
        print("Common locations:")
        if system == "Windows":
            print("  - C:\\Program Files\\Google\\Drive File Stream")
            print("  - C:\\Program Files (x86)\\Google\\Drive File Stream")
        elif system == "Darwin":
            print("  - /Applications/Google Drive.app")
        else:
            print("  - /opt/google/drive")
            print("  - /usr/local/google/drive")

def check_google_drive_processes():
    """
    Check if Google Drive processes are running
    """
    print("\n" + "=" * 60)
    print("GOOGLE DRIVE PROCESS CHECK")
    print("=" * 60)
    
    try:
        import psutil
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'google' in proc.info['name'].lower() or 'drive' in proc.info['name'].lower():
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if processes:
            print("Google Drive related processes found:")
            for proc in processes:
                print(f"  - {proc['name']} (PID: {proc['pid']})")
        else:
            print("No Google Drive processes found")
            print("Make sure Google Drive Desktop is running")
    except ImportError:
        print("psutil not available - cannot check processes")
        print("Install with: pip install psutil")

if __name__ == "__main__":
    find_google_drive_paths()
    check_google_drive_processes()


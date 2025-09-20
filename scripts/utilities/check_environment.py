#!/usr/bin/env python3
"""
Check environment variables and configuration
"""

import os
from dotenv import load_dotenv

def check_environment():
    """Check environment variables and configuration"""
    print("🔍 Checking environment configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Check database configuration
    db_config = {
        'DB_HOST': os.getenv('DB_HOST', 'srv1978.hstgr.io'),
        'DB_USER': os.getenv('DB_USER', 'u488367489_mongrel_data'),
        'DB_PASSWORD': os.getenv('DB_PASSWORD', 'defaultpassword'),
        'DB_NAME': os.getenv('DB_NAME', 'u488367489_Price_Ticker')
    }
    
    print("📊 Database Configuration:")
    for key, value in db_config.items():
        # Mask password for security
        display_value = "***" if "PASSWORD" in key else value
        print(f"  {key}: {display_value}")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"✅ .env file found: {env_file}")
    else:
        print(f"⚠️ .env file not found: {env_file}")
    
    # Check Google Drive credentials
    creds_file = '/home/mongreldatalab/mongrel_price_ticker/credentials/tactical-elf-452207-m9-1f0520891d95.json'
    if os.path.exists(creds_file):
        print(f"✅ Google Drive credentials found: {creds_file}")
    else:
        print(f"⚠️ Google Drive credentials not found: {creds_file}")
    
    return True

if __name__ == "__main__":
    print("🚀 Environment Check")
    print("=" * 30)
    check_environment()
    print("\n✅ Environment check completed!")

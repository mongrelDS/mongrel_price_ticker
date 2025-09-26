#!/usr/bin/env python3
"""
Auto-login to phpMyAdmin
This script will automatically log you into phpMyAdmin
"""

import requests
import webbrowser
import time
from urllib.parse import urljoin

def auto_login_phpmyadmin():
    base_url = "http://localhost/phpmyadmin/"
    login_url = "http://localhost/phpmyadmin/index.php?route=/"
    
    # Get the login page to extract token
    print("🔍 Getting login page...")
    session = requests.Session()
    
    try:
        response = session.get(login_url)
        response.raise_for_status()
        
        # Extract token from the page
        import re
        token_match = re.search(r'token.*?value="([^"]*)"', response.text)
        if not token_match:
            print("❌ Could not find token in login page")
            return False
            
        token = token_match.group(1)
        print(f"✅ Found token: {token[:20]}...")
        
        # Login credentials
        login_data = {
            'route': '/',
            'lang': 'en',
            'token': token,
            'pma_username': 'u488367489_mongrel_data',
            'pma_password': '6r9lHgT9fnfqpQkDjXmoPJbMXINl4Gl3LFLYq9Ke',
            'server': '1',
            'set_session': 'auto_login_session'
        }
        
        print("🚀 Attempting login...")
        login_response = session.post(login_url, data=login_data, allow_redirects=True)
        
        if 'logged_in:true' in login_response.text or 'database' in login_response.text.lower():
            print("✅ Login successful!")
            print("🌐 Opening phpMyAdmin in browser...")
            
            # Open the main phpMyAdmin page
            webbrowser.open("http://localhost/phpmyadmin/index.php?route=/database/structure")
            return True
        else:
            print("❌ Login failed - checking response...")
            print(f"Response status: {login_response.status_code}")
            if 'error' in login_response.text.lower():
                print("Error in response:")
                print(login_response.text[:500])
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Auto-login to phpMyAdmin")
    print("=" * 40)
    
    success = auto_login_phpmyadmin()
    
    if success:
        print("\n🎉 SUCCESS! phpMyAdmin should now be open in your browser")
        print("You should see your database: u488367489_Price_Ticker")
        print("With tables: natura_sku_summary, fixed_fields, df_ticker, market_price_list")
    else:
        print("\n❌ Auto-login failed. Try the manual methods:")
        print("1. Open: file:///home/mongreldatalab/mongrel_price_ticker/scripts/force_phpmyadmin_login.html")
        print("2. Or use command line: mysql -h 127.0.0.1 -P 30306 -u u488367489_mongrel_data -p6r9lHgT9fnfqpQkDjXmoPJbMXINl4Gl3LFLYq9Ke")

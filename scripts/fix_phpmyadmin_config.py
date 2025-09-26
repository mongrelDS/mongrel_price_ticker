#!/usr/bin/env python3
"""
Fix phpMyAdmin Configuration Bug
The issue is that phpMyAdmin is not properly configured for the custom port
"""

import re

def fix_phpmyadmin_config():
    config_file = '/etc/phpmyadmin/config.inc.php'
    
    print("🔍 Analyzing phpMyAdmin configuration...")
    
    # Read current config
    with open(config_file, 'r') as f:
        content = f.read()
    
    # Check if port is properly configured
    if "port.*30306" in content:
        print("✅ Port 30306 is already configured")
    else:
        print("❌ Port 30306 not found in configuration")
    
    # Check if server configuration is complete
    if "Servers.*host.*127.0.0.1" in content:
        print("✅ Host 127.0.0.1 is configured")
    else:
        print("❌ Host 127.0.0.1 not found")
    
    # The real issue: phpMyAdmin needs a proper server configuration
    # Let's create a working configuration
    working_config = '''
// Custom server configuration for Mongrel Price Ticker
$i++;
$cfg['Servers'][$i]['host'] = '127.0.0.1';
$cfg['Servers'][$i]['port'] = '30306';
$cfg['Servers'][$i]['connect_type'] = 'tcp';
$cfg['Servers'][$i]['auth_type'] = 'cookie';
$cfg['Servers'][$i]['user'] = '';
$cfg['Servers'][$i]['password'] = '';
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['AllowRoot'] = false;
$cfg['Servers'][$i]['DisableIS'] = false;

// Advanced features
$cfg['Servers'][$i]['pmadb'] = 'phpmyadmin';
$cfg['Servers'][$i]['bookmarktable'] = 'pma__bookmark';
$cfg['Servers'][$i]['relation'] = 'pma__relation';
$cfg['Servers'][$i]['table_info'] = 'pma__table_info';
$cfg['Servers'][$i]['table_coords'] = 'pma__table_coords';
$cfg['Servers'][$i]['pdf_pages'] = 'pma__pdf_pages';
$cfg['Servers'][$i]['column_info'] = 'pma__column_info';
$cfg['Servers'][$i]['history'] = 'pma__history';
$cfg['Servers'][$i]['table_uiprefs'] = 'pma__table_uiprefs';
$cfg['Servers'][$i]['tracking'] = 'pma__tracking';
$cfg['Servers'][$i]['userconfig'] = 'pma__userconfig';
$cfg['Servers'][$i]['recent'] = 'pma__recent';
$cfg['Servers'][$i]['favorite'] = 'pma__favorites';
$cfg['Servers'][$i]['users'] = 'pma__users';
$cfg['Servers'][$i]['usergroups'] = 'pma__usergroups';
$cfg['Servers'][$i]['navigationhiding'] = 'pma__navigationhiding';
$cfg['Servers'][$i]['savedsearches'] = 'pma__savedsearches';
$cfg['Servers'][$i]['central_columns'] = 'pma__central_columns';
$cfg['Servers'][$i]['designer_settings'] = 'pma__designer_settings';
$cfg['Servers'][$i]['export_templates'] = 'pma__export_templates';
'''
    
    # Check if this configuration already exists
    if "Custom server configuration for Mongrel Price Ticker" in content:
        print("✅ Custom configuration already exists")
        return True
    
    print("🔧 Adding custom server configuration...")
    
    # Add the configuration before the closing PHP tag
    if content.strip().endswith('?>'):
        new_content = content.replace('?>', working_config + '\n?>')
    else:
        new_content = content + working_config
    
    # Write the new configuration
    with open('/tmp/phpmyadmin_config_fixed.php', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed configuration written to /tmp/phpmyadmin_config_fixed.php")
    print("📋 To apply the fix, run:")
    print("   sudo cp /tmp/phpmyadmin_config_fixed.php /etc/phpmyadmin/config.inc.php")
    print("   sudo systemctl restart apache2")
    
    return True

if __name__ == "__main__":
    print("🐛 phpMyAdmin Configuration Bug Fix")
    print("=" * 40)
    fix_phpmyadmin_config()

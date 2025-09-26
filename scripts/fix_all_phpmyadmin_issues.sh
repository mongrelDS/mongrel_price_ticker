#!/bin/bash

echo "🐛 Fixing All phpMyAdmin Issues"
echo "================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo privileges."
    echo "Please run: sudo bash $0"
    exit 1
fi

echo "1. Fixing JavaScript symbolic link issues..."
# Remove broken symlinks and recreate them
find /usr/share/phpmyadmin/js/vendor/ -type l -delete 2>/dev/null || true

# Reinstall phpMyAdmin to fix broken symlinks
apt-get update
apt-get install --reinstall phpmyadmin -y

echo "2. Fixing Apache configuration for phpMyAdmin..."
# Enable FollowSymLinks for phpMyAdmin
cat > /etc/apache2/conf-available/phpmyadmin-symlinks.conf << 'EOF'
<Directory /usr/share/phpmyadmin>
    Options +FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
EOF

a2enconf phpmyadmin-symlinks

echo "3. Fixing phpMyAdmin server configuration..."
# Create a proper configuration that uses the correct server
cat > /etc/phpmyadmin/conf.d/mongrel_fixed.php << 'EOF'
<?php
// Fixed configuration for Mongrel Price Ticker
// This overrides the default server configuration

// Reset server index to 1 (the main server)
$i = 1;

// Configure server 1 for the custom port
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

// Disable the default server (server 2) if it exists
if (isset($cfg['Servers'][2])) {
    $cfg['Servers'][2]['host'] = '';
}
?>
EOF

chown root:root /etc/phpmyadmin/conf.d/mongrel_fixed.php
chmod 644 /etc/phpmyadmin/conf.d/mongrel_fixed.php

echo "4. Restarting services..."
systemctl restart apache2

echo "5. Testing the fix..."
sleep 2

# Test if the configuration is working
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/phpmyadmin/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ phpMyAdmin is accessible"
else
    echo "❌ phpMyAdmin still has issues (HTTP $HTTP_CODE)"
fi

# Test if JavaScript is loading
JS_ERRORS=$(curl -s http://localhost/phpmyadmin/ 2>&1 | grep -c "Symbolic link not allowed" || echo "0")
if [ "$JS_ERRORS" -eq 0 ]; then
    echo "✅ JavaScript files are loading properly"
else
    echo "❌ Still have $JS_ERRORS JavaScript errors"
fi

echo ""
echo "🎯 Fix Complete!"
echo "Now try accessing: http://localhost/phpmyadmin/"
echo "Use credentials: u488367489_mongrel_data / 6r9lHgT9fnfqpQkDjXmoPJbMXINl4Gl3LFLYq9Ke"

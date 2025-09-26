#!/bin/bash

echo "=== Fixing phpMyAdmin Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo privileges."
    echo "Please run: sudo bash $0"
    exit 1
fi

echo "1. Creating Apache configuration for phpMyAdmin..."
cp /home/mongreldatalab/mongrel_price_ticker/scripts/phpmyadmin_apache.conf /etc/apache2/conf-available/phpmyadmin.conf

echo "2. Enabling phpMyAdmin configuration..."
a2enconf phpmyadmin

echo "3. Enabling required Apache modules..."
a2enmod rewrite
a2enmod ssl

echo "4. Checking MySQL status..."
if ! systemctl is-active --quiet mysql; then
    echo "   Starting MySQL..."
    systemctl start mysql
else
    echo "   MySQL is already running"
fi

echo "5. Restarting Apache..."
systemctl restart apache2

echo "6. Copying custom phpMyAdmin configuration..."
cp /home/mongreldatalab/mongrel_price_ticker/scripts/phpmyadmin_config.php /etc/phpmyadmin/conf.d/mongrel_config.php
chown root:root /etc/phpmyadmin/conf.d/mongrel_config.php
chmod 644 /etc/phpmyadmin/conf.d/mongrel_config.php

echo "7. Setting proper permissions..."
chown -R www-data:www-data /usr/share/phpmyadmin
chmod -R 755 /usr/share/phpmyadmin

echo ""
echo "=== Setup Complete ==="
echo "Testing phpMyAdmin access..."

# Test HTTP access
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/phpmyadmin/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ phpMyAdmin is accessible at: http://localhost/phpmyadmin/"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ phpMyAdmin still returns 404 - checking configuration..."
    echo "   Configuration files:"
    ls -la /etc/apache2/conf-enabled/ | grep phpmyadmin
    echo "   Apache error log:"
    tail -5 /var/log/apache2/error.log
else
    echo "⚠️  phpMyAdmin returns HTTP $HTTP_CODE"
fi

echo ""
echo "=== Next Steps ==="
echo "1. Open browser and go to: http://localhost/phpmyadmin/"
echo "2. Login with your MySQL credentials"
echo "3. You should see your project tables:"
echo "   - natura_sku_summary"
echo "   - fixed_fields"
echo "   - df_ticker"
echo "   - market_price_list"
echo ""
echo "If you still have issues, check:"
echo "- sudo tail -f /var/log/apache2/error.log"
echo "- sudo systemctl status apache2"
echo "- sudo systemctl status mysql"

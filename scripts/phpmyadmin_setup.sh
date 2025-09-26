#!/bin/bash

echo "=== phpMyAdmin Setup Script for Mongrel Price Ticker ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo privileges."
    echo "Please run: sudo bash $0"
    exit 1
fi

echo "1. Enabling phpMyAdmin configuration..."
a2enconf phpmyadmin

echo "2. Enabling required Apache modules..."
a2enmod rewrite
a2enmod ssl

echo "3. Restarting Apache..."
systemctl restart apache2

echo "4. Checking Apache status..."
systemctl status apache2 --no-pager -l

echo "5. Checking phpMyAdmin configuration..."
if [ -f "/etc/apache2/conf-enabled/phpmyadmin.conf" ]; then
    echo "✅ phpMyAdmin configuration is enabled"
else
    echo "❌ phpMyAdmin configuration not found"
fi

echo ""
echo "=== Setup Complete ==="
echo "Access phpMyAdmin at: http://localhost/phpmyadmin/"
echo "Or if you have a domain: http://your-domain.com/phpmyadmin/"
echo ""
echo "Your project tables should be visible:"
echo "- natura_sku_summary"
echo "- fixed_fields" 
echo "- df_ticker"
echo "- market_price_list"
echo ""
echo "=== Security Notes ==="
echo "1. Change default passwords"
echo "2. Consider setting up SSL/HTTPS"
echo "3. Restrict access by IP if needed"
echo "4. Regular security updates"

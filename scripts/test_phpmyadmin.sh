#!/bin/bash

echo "=== phpMyAdmin Test Script ==="
echo ""

# Test 1: Check if Apache is running
echo "1. Checking Apache status..."
if systemctl is-active --quiet apache2; then
    echo "✅ Apache2 is running"
else
    echo "❌ Apache2 is not running"
    echo "   Run: sudo systemctl start apache2"
fi

# Test 2: Check if phpMyAdmin configuration is enabled
echo ""
echo "2. Checking phpMyAdmin configuration..."
if [ -f "/etc/apache2/conf-enabled/phpmyadmin.conf" ]; then
    echo "✅ phpMyAdmin configuration is enabled"
else
    echo "❌ phpMyAdmin configuration not enabled"
    echo "   Run: sudo a2enconf phpmyadmin"
fi

# Test 3: Check if phpMyAdmin files exist
echo ""
echo "3. Checking phpMyAdmin installation..."
if [ -d "/usr/share/phpmyadmin" ]; then
    echo "✅ phpMyAdmin is installed"
else
    echo "❌ phpMyAdmin not found"
fi

# Test 4: Test HTTP access
echo ""
echo "4. Testing HTTP access..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/phpmyadmin/ 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ phpMyAdmin is accessible via HTTP"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ phpMyAdmin returns 404 - configuration not enabled"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "❌ Cannot connect to localhost - Apache not running"
else
    echo "⚠️  phpMyAdmin returns HTTP $HTTP_CODE"
fi

# Test 5: Check MySQL connection
echo ""
echo "5. Testing MySQL connection..."
if mysql -e "SELECT 1;" 2>/dev/null; then
    echo "✅ MySQL connection successful"
else
    echo "❌ MySQL connection failed"
    echo "   Check if MySQL is running: sudo systemctl status mysql"
fi

echo ""
echo "=== Summary ==="
echo "If all tests pass, you can access phpMyAdmin at:"
echo "http://localhost/phpmyadmin/"
echo ""
echo "Your project tables should be visible:"
echo "- natura_sku_summary"
echo "- fixed_fields"
echo "- df_ticker" 
echo "- market_price_list"
echo ""
echo "=== Next Steps ==="
echo "1. Open browser and go to http://localhost/phpmyadmin/"
echo "2. Login with your MySQL credentials"
echo "3. Browse your project tables"
echo "4. Test SQL queries before running maintenance scripts"

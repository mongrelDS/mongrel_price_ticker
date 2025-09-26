#!/bin/bash

echo "=== Fixing phpMyAdmin Port Configuration ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to be run with sudo privileges."
    echo "Please run: sudo bash $0"
    exit 1
fi

echo "1. Backing up current phpMyAdmin configuration..."
cp /etc/phpmyadmin/config.inc.php /etc/phpmyadmin/config.inc.php.backup

echo "2. Adding port configuration..."
cat >> /etc/phpmyadmin/config.inc.php << 'EOF'

// Custom port configuration for Mongrel Price Ticker
$cfg['Servers'][$i]['port'] = '30306';
EOF

echo "3. Copying custom port configuration..."
cp /home/mongreldatalab/mongrel_price_ticker/scripts/phpmyadmin_port_config.php /etc/phpmyadmin/conf.d/port_config.php
chown root:root /etc/phpmyadmin/conf.d/port_config.php
chmod 644 /etc/phpmyadmin/conf.d/port_config.php

echo "4. Restarting Apache..."
systemctl restart apache2

echo "5. Testing connection..."
mysql -h 127.0.0.1 -P 30306 -u u488367489_mongrel_data -p6r9lHgT9fnfqpQkDjXmoPJbMXINl4Gl3LFLYq9Ke -e "SHOW DATABASES;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ MySQL connection successful on port 30306"
else
    echo "❌ MySQL connection failed"
fi

echo ""
echo "=== Configuration Complete ==="
echo "Now try accessing phpMyAdmin at:"
echo "http://localhost/phpmyadmin/"
echo ""
echo "Use these credentials:"
echo "Username: u488367489_mongrel_data"
echo "Password: 6r9lHgT9fnfqpQkDjXmoPJbMXINl4Gl3LFLYq9Ke"
echo "Server: 127.0.0.1"
echo "Port: 30306"

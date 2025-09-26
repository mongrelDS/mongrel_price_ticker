# Complete phpMyAdmin Setup Guide for Mongrel Price Ticker

## Current Status
✅ phpMyAdmin is installed  
✅ Apache2 is installed  
✅ PHP 8.3.6 is installed  
✅ MySQL client is installed  
❌ phpMyAdmin Apache configuration needs to be enabled  

## Step-by-Step Setup

### 1. Run the Setup Script
```bash
cd /home/mongreldatalab/mongrel_price_ticker
sudo bash scripts/phpmyadmin_setup.sh
```

### 2. Copy Custom Configuration
```bash
# Copy the custom configuration
sudo cp scripts/phpmyadmin_config.php /etc/phpmyadmin/conf.d/mongrel_config.php

# Set proper permissions
sudo chown root:root /etc/phpmyadmin/conf.d/mongrel_config.php
sudo chmod 644 /etc/phpmyadmin/conf.d/mongrel_config.php
```

### 3. Test Access
```bash
# Test if phpMyAdmin is accessible
curl -I http://localhost/phpmyadmin/

# Or open in browser
echo "Open: http://localhost/phpmyadmin/"
```

### 4. Login to phpMyAdmin
- Open your browser
- Go to: `http://localhost/phpmyadmin/`
- Login with your MySQL credentials
- You should see your project tables:
  - `natura_sku_summary`
  - `fixed_fields`
  - `df_ticker`
  - `market_price_list`

## Troubleshooting

### If you get "404 Not Found":
```bash
# Check if configuration is enabled
ls -la /etc/apache2/conf-enabled/ | grep phpmyadmin

# If not found, enable it manually
sudo a2enconf phpmyadmin
sudo systemctl restart apache2
```

### If you get "Access Denied":
```bash
# Check Apache error logs
sudo tail -f /var/log/apache2/error.log

# Check if Apache is running
sudo systemctl status apache2
```

### If you can't connect to MySQL:
```bash
# Check MySQL status
sudo systemctl status mysql

# Test MySQL connection
mysql -u root -p
```

## Security Recommendations

### 1. Change Default Passwords
```bash
# Connect to MySQL
mysql -u root -p

# Create a dedicated user for phpMyAdmin
CREATE USER 'phpmyadmin'@'localhost' IDENTIFIED BY 'your-secure-password';
GRANT ALL PRIVILEGES ON *.* TO 'phpmyadmin'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
EXIT;
```

### 2. Enable HTTPS (Optional)
```bash
# Install certbot
sudo apt install certbot python3-certbot-apache

# Get SSL certificate (replace with your domain)
sudo certbot --apache -d your-domain.com
```

### 3. Restrict Access by IP (Optional)
```bash
# Edit Apache configuration
sudo nano /etc/apache2/conf-enabled/phpmyadmin.conf

# Add IP restriction (example)
<Directory /usr/share/phpmyadmin>
    Require ip 192.168.1.0/24
    Require ip 127.0.0.1
</Directory>
```

## Using phpMyAdmin with Your Project

### 1. Monitor Your Maintenance Script
- Before running `sql_maintenance.py`, check table status in phpMyAdmin
- After running, verify the results

### 2. Test SQL Queries
- Use phpMyAdmin's SQL interface to test queries before implementing in Python
- Example: Test the domain extraction query from your script

### 3. Data Validation
- Check data integrity after maintenance operations
- Verify row counts and data quality

### 4. Backup and Recovery
- Export tables before major operations
- Import data if needed

## Quick Commands

```bash
# Start/stop services
sudo systemctl start apache2
sudo systemctl stop apache2
sudo systemctl restart apache2

# Check status
sudo systemctl status apache2
sudo systemctl status mysql

# View logs
sudo tail -f /var/log/apache2/error.log
sudo tail -f /var/log/mysql/error.log

# Test phpMyAdmin
curl -I http://localhost/phpmyadmin/
```

## Next Steps

1. Run the setup script
2. Test access in browser
3. Configure your database connection
4. Test with your project tables
5. Set up security measures
6. Create regular backups

## Support

If you encounter issues:
1. Check the error logs
2. Verify all services are running
3. Test MySQL connection separately
4. Check file permissions
5. Review Apache configuration

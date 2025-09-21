#!/bin/bash
# Implementation script for enhanced cron schedule with error checking

echo "Setting up enhanced cron schedule with error checking..."

# Create log directory if it doesn't exist
sudo mkdir -p /var/log/cron_jobs
sudo chown mongreldatalab:mongreldatalab /var/log/cron_jobs

# Create the enhanced cron schedule
cat > /tmp/enhanced_cron_schedule.txt << 'CRON_EOF'
# Enhanced Cron Schedule with Error Checking
# Generated on $(date)

# ShipHero Data Pipeline
# 1. Extract line items (1:00 AM daily)
0 1 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/shiphero_line_items.py >> /var/log/cron_jobs/shiphero_line_items.log 2>&1 && touch /tmp/shiphero_line_items.success

# 2. Process shipped orders (1:50 AM daily) - depends on line items
50 1 * * * [ -f /tmp/shiphero_line_items.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/sh_to_sql_shipped_orders.py >> /var/log/cron_jobs/shipped_orders.log 2>&1 && touch /tmp/shipped_orders.success

# 3. Process product table (2:30 AM daily) - depends on line items
30 2 * * * [ -f /tmp/shiphero_line_items.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/sh_to_sql_product_table.py >> /var/log/cron_jobs/product_table.log 2>&1 && touch /tmp/product_table.success

# 4. Process customer profiles (3:00 AM daily) - independent
0 3 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/natura/natura_customer_profile.py >> /var/log/cron_jobs/natura_customer.log 2>&1 && touch /tmp/natura_customer.success

# 5. Archive old files (4:00 AM daily) - depends on all previous scripts
0 4 * * * [ -f /tmp/shipped_orders.success ] && [ -f /tmp/product_table.success ] && [ -f /tmp/natura_customer.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/archive/archive_old_csv_files.py >> /var/log/cron_jobs/archive_files.log 2>&1

# Cleanup success files daily at 5:00 AM
0 5 * * * rm -f /tmp/shiphero_line_items.success /tmp/shipped_orders.success /tmp/product_table.success /tmp/natura_customer.success

# Well.ca Scraping Pipeline (if needed)
# Brand discovery (weekly - Sunday 2 AM)
0 2 * * 0 /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_brand_link_list.py >> /var/log/cron_jobs/wellca_brand_links.log 2>&1

# Product discovery (3x per week - Mon, Wed, Fri 3 AM)
0 3 * * 1,3,5 /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_links_from_brands.py >> /var/log/cron_jobs/wellca_product_links.log 2>&1

# Price updates (daily - 4 AM)
0 4 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_price_update.py >> /var/log/cron_jobs/wellca_price_update.log 2>&1
CRON_EOF

echo "✅ Enhanced cron schedule created at /tmp/enhanced_cron_schedule.txt"
echo ""
echo "To implement this schedule:"
echo "1. Review the schedule: cat /tmp/enhanced_cron_schedule.txt"
echo "2. Add to crontab: crontab -e"
echo "3. Copy and paste the schedule from the file"
echo "4. Save and exit"
echo ""
echo "To check current crontab: crontab -l"
echo "To remove current crontab: crontab -r"

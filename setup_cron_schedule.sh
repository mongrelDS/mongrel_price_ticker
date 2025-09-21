#!/bin/bash
# Complete Cron Schedule Setup Script

echo "🚀 Setting up Enhanced Cron Schedule with Error Checking"
echo "========================================================"

# Create log directory
echo "📁 Creating log directory..."
mkdir -p logs/cron_jobs
echo "✅ Log directory created: logs/cron_jobs"

# Create the cron schedule file
echo "📝 Creating cron schedule..."
cat > cron_schedule.txt << 'CRON_EOF'
# Enhanced Cron Schedule with Error Checking
# Generated on $(date)

# ShipHero Data Pipeline
# 1. Extract line items (1:00 AM daily)
0 1 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/shiphero_line_items.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/shiphero_line_items.log 2>&1 && touch /tmp/shiphero_line_items.success

# 2. Process shipped orders (1:50 AM daily) - depends on line items
50 1 * * * [ -f /tmp/shiphero_line_items.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/sh_to_sql_shipped_orders.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/shipped_orders.log 2>&1 && touch /tmp/shipped_orders.success

# 3. Process product table (2:30 AM daily) - depends on line items
30 2 * * * [ -f /tmp/shiphero_line_items.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/shiphero/sh_to_sql_product_table.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/product_table.log 2>&1 && touch /tmp/product_table.success

# 4. Process customer profiles (3:00 AM daily) - independent
0 3 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/natura/natura_customer_profile.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/natura_customer.log 2>&1 && touch /tmp/natura_customer.success

# 5. Archive old files (4:00 AM daily) - depends on all previous scripts
0 4 * * * [ -f /tmp/shipped_orders.success ] && [ -f /tmp/product_table.success ] && [ -f /tmp/natura_customer.success ] && /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/archive/archive_old_csv_files.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/archive_files.log 2>&1

# Cleanup success files daily at 5:00 AM
0 5 * * * rm -f /tmp/shiphero_line_items.success /tmp/shipped_orders.success /tmp/product_table.success /tmp/natura_customer.success

# Well.ca Scraping Pipeline
# Brand discovery (weekly - Sunday 2 AM)
0 2 * * 0 /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_brand_link_list.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/wellca_brand_links.log 2>&1

# Product discovery (3x per week - Mon, Wed, Fri 3 AM)
0 3 * * 1,3,5 /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_links_from_brands.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/wellca_product_links.log 2>&1

# Price updates (daily - 4 AM)
0 4 * * * /usr/bin/python3 /home/mongreldatalab/mongrel_price_ticker/scripts/scrapers/wellca/wellca_price_update.py >> /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs/wellca_price_update.log 2>&1
CRON_EOF

echo "✅ Cron schedule created: cron_schedule.txt"

# Show the schedule
echo ""
echo "📋 CRON SCHEDULE PREVIEW:"
echo "========================="
cat cron_schedule.txt

echo ""
echo "🔧 IMPLEMENTATION STEPS:"
echo "========================"
echo "1. Review the schedule above"
echo "2. Run: crontab -e"
echo "3. Copy and paste the entire schedule"
echo "4. Save and exit (Ctrl+X, Y, Enter)"
echo "5. Verify with: crontab -l"
echo "6. Monitor with: ./scripts/monitor_cron_jobs.sh"

echo ""
echo "📊 SCHEDULE SUMMARY:"
echo "==================="
echo "• ShipHero Pipeline: Daily 1:00-5:00 AM"
echo "• Well.ca Scraping: Mixed schedule (daily/weekly)"
echo "• Error Checking: Built-in dependency validation"
echo "• Logging: All output to logs/cron_jobs/"
echo "• Monitoring: Use ./scripts/monitor_cron_jobs.sh"

echo ""
echo "✅ Setup complete! Ready for implementation."

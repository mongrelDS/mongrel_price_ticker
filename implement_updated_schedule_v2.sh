#!/bin/bash
# Implementation script for updated cron schedule v2

echo "🚀 Implementing Updated Cron Schedule v2"
echo "========================================"

# Create log directory if it doesn't exist
echo "📁 Creating log directory..."
mkdir -p /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs
echo "✅ Log directory created: /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs"

# Backup current crontab
echo "💾 Backing up current crontab..."
crontab -l > /home/mongreldatalab/mongrel_price_ticker/current_crontab_backup_v2_$(date +%Y%m%d_%H%M%S).txt
echo "✅ Current crontab backed up"

# Show the new schedule
echo ""
echo "📋 UPDATED CRON SCHEDULE PREVIEW:"
echo "================================="
cat /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt

echo ""
echo "🔧 IMPLEMENTATION STEPS:"
echo "========================"
echo "1. The updated schedule is ready in cron_schedule.txt"
echo "2. To implement, run: crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt"
echo "3. Verify with: crontab -l"
echo "4. Monitor with: ./scripts/monitor_cron_jobs.sh"

echo ""
echo "📊 SCHEDULE SUMMARY:"
echo "==================="
echo "• ShipHero Pipeline: 1:00-2:30 AM (S M T W T F)"
echo "• Natura Processing: 3:00-3:40 AM (S M T W T F)"
echo "• Analytics: 4:30-5:30 AM (S M T W T F)"
echo "• Scraping: 6:00-9:00 AM (S M T W T F)"
echo "• SQL Maintenance: 9:30 AM (S M T W T F)"
echo "• Well.ca Pipeline: Mixed schedule (daily/weekly)"
echo "• Healthy Planet: Mixed schedule (daily/weekly)"

echo ""
echo "🔄 KEY CHANGES IN V2:"
echo "===================="
echo "• healthyplanet_json_method.py: 6:30 AM → 6:00 AM"
echo "• wellca_json_method_from_search.py: 7:00 AM → 6:30 AM"
echo "• goodness_me_initial_crawl.py: 7:30 AM → 7:00 AM"
echo "• goodness_me_item_json_crawl.py: 8:00 AM → 7:30 AM"
echo "• naturesante_crawl.py: 8:30 AM → 8:00 AM"
echo "• naturesante_crawl_results.py: 9:00 AM → 8:30 AM"
echo "• naturesante_json_results.py: 9:30 AM → 9:00 AM"
echo "• sql_maintenance.py: 6:00 AM → 9:30 AM"

echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "==================="
echo "• All scripts run Sunday through Friday (S M T W T F)"
echo "• SQL maintenance moved to end of schedule (9:30 AM)"
echo "• Success file cleanup remains at 10:00 AM"
echo "• Error checking and logging maintained"

echo ""
echo "🚀 Ready to implement! Run the following command:"
echo "crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt"

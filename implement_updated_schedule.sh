#!/bin/bash
# Implementation script for updated cron schedule

echo "🚀 Implementing Updated Cron Schedule"
echo "====================================="

# Create log directory if it doesn't exist
echo "📁 Creating log directory..."
mkdir -p /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs
echo "✅ Log directory created: /home/mongreldatalab/mongrel_price_ticker/logs/cron_jobs"

# Backup current crontab
echo "💾 Backing up current crontab..."
crontab -l > /home/mongreldatalab/mongrel_price_ticker/current_crontab_backup_$(date +%Y%m%d_%H%M%S).txt
echo "✅ Current crontab backed up"

# Show the new schedule
echo ""
echo "📋 NEW CRON SCHEDULE PREVIEW:"
echo "============================="
cat /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt

echo ""
echo "🔧 IMPLEMENTATION STEPS:"
echo "========================"
echo "1. The new schedule is ready in cron_schedule.txt"
echo "2. To implement, run: crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt"
echo "3. Verify with: crontab -l"
echo "4. Monitor with: ./scripts/monitor_cron_jobs.sh"

echo ""
echo "📊 SCHEDULE SUMMARY:"
echo "==================="
echo "• ShipHero Pipeline: 1:00-2:30 AM (S M T W T F)"
echo "• Natura Processing: 3:00-3:40 AM (S M T W T F)"
echo "• Analytics: 4:30-5:30 AM (S M T W T F)"
echo "• SQL Maintenance: 6:00 AM (S M T W T F)"
echo "• Scraping: 6:30-9:30 AM (S M T W T F)"
echo "• Well.ca Pipeline: Mixed schedule (daily/weekly)"
echo "• Healthy Planet: Mixed schedule (daily/weekly)"

echo ""
echo "⚠️  IMPORTANT NOTES:"
echo "==================="
echo "• All scripts run Sunday through Friday (S M T W T F)"
echo "• Naturesante JSON results moved to 9:30 AM to avoid conflict"
echo "• Success file cleanup moved to 10:00 AM"
echo "• Error checking and logging maintained"

echo ""
echo "🚀 Ready to implement! Run the following command:"
echo "crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt"

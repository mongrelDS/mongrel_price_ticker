# Cron Schedule Implementation Guide

## 🚀 Quick Implementation

### Step 1: Review the Schedule
```bash
cat /tmp/enhanced_cron_schedule.txt
```

### Step 2: Implement the Schedule
```bash
# Edit your crontab
crontab -e

# Copy and paste the entire schedule from /tmp/enhanced_cron_schedule.txt
# Save and exit (Ctrl+X, then Y, then Enter in nano)
```

### Step 3: Verify Implementation
```bash
# Check your crontab
crontab -l

# Run monitoring script
./scripts/monitor_cron_jobs.sh
```

## 📋 Schedule Overview

### ShipHero Data Pipeline (Daily)
- **1:00 AM** - Extract line items
- **1:50 AM** - Process shipped orders (depends on line items)
- **2:30 AM** - Process product table (depends on line items)
- **3:00 AM** - Process customer profiles (independent)
- **4:00 AM** - Archive old files (depends on all previous)
- **5:00 AM** - Cleanup success files

### Well.ca Scraping Pipeline
- **Sunday 2:00 AM** - Brand discovery (weekly)
- **Mon/Wed/Fri 3:00 AM** - Product discovery (3x per week)
- **Daily 4:00 AM** - Price updates (daily)

## 🔧 Key Features

### Error Checking
- Each script creates a success file when completed
- Dependent scripts only run if their dependencies succeeded
- Prevents cascading failures

### Logging
- All output logged to `/var/log/cron_jobs/`
- Separate log files for each script
- Easy troubleshooting and monitoring

### Monitoring
- Use `./scripts/monitor_cron_jobs.sh` to check status
- Shows last run times, errors, and success indicators
- Displays current crontab configuration

## 🛠️ Troubleshooting

### Check Logs
```bash
# View specific job logs
tail -f /var/log/cron_jobs/shiphero_line_items.log
tail -f /var/log/cron_jobs/shipped_orders.log

# Check for errors
grep -i "error\|failed\|exception" /var/log/cron_jobs/*.log
```

### Manual Testing
```bash
# Test individual scripts
python3 scripts/shiphero/shiphero_line_items.py
python3 scripts/shiphero/sh_to_sql_shipped_orders.py

# Check success files
ls -la /tmp/*.success
```

### Reset Success Files
```bash
# Clear all success files (force re-run)
rm -f /tmp/shiphero_line_items.success /tmp/shipped_orders.success /tmp/product_table.success /tmp/natura_customer.success
```

## 📊 Monitoring Commands

```bash
# Check cron service status
systemctl status cron

# View cron logs
grep CRON /var/log/syslog | tail -20

# Monitor in real-time
tail -f /var/log/syslog | grep CRON
```

## 🔄 Maintenance

### Weekly Tasks
- Review logs for errors
- Check disk space for log files
- Verify data pipeline integrity

### Monthly Tasks
- Rotate log files if they get too large
- Review and update script paths if needed
- Test disaster recovery procedures

## 📞 Support

If you encounter issues:
1. Check the monitoring script output
2. Review individual log files
3. Verify script paths and permissions
4. Test scripts manually
5. Check system resources (disk space, memory)


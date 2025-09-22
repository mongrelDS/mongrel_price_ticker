# Healthy Planet Scraping Schedule Summary

## 📅 New Schedules Added

### 1. Weekly Crawler (Sunday 1:00 AM)
- **Script**: `healthyplanet_crawler.py`
- **Schedule**: `0 1 * * 0` (Every Sunday at 1:00 AM)
- **Purpose**: Discovers new products and updates the product database
- **Log**: `logs/cron_jobs/healthyplanet_crawler.log`

### 2. Daily Database Updates (6:00 AM)
- **Script**: `healthyplanet_item_update_from_database.py`
- **Schedule**: `0 6 * * *` (Every day at 6:00 AM)
- **Purpose**: Updates product information from existing database records
- **Log**: `logs/cron_jobs/healthyplanet_database_update.log`

### 3. High-Frequency Ticker Updates (Every 90 Minutes)
- **Script**: `healthyplanet_item_update_from_ticker.py`
- **Schedule**: Multiple times daily (7:00 AM, 8:30 AM, 10:00 AM, 11:30 AM, 1:00 PM, 2:30 PM, 4:00 PM, 5:30 PM, 7:00 PM, 8:30 PM, 10:00 PM, 11:30 PM)
- **Purpose**: Updates price and stock information from 30-day ticker data
- **Log**: `logs/cron_jobs/healthyplanet_ticker_update.log`

## 🕐 Complete Daily Timeline

| Time | Script | Purpose |
|------|--------|---------|
| 1:00 AM | ShipHero Line Items | Data extraction |
| 1:50 AM | ShipHero Shipped Orders | Process orders |
| 2:00 AM | Well.ca Brand Discovery | Weekly brand discovery |
| 2:30 AM | ShipHero Product Table | Process products |
| 3:00 AM | Natura Customer Profiles | Customer data |
| 3:00 AM | Well.ca Product Discovery | Product discovery (Mon/Wed/Fri) |
| 4:00 AM | Well.ca Price Updates | Price updates |
| 4:00 AM | ShipHero Archive | File cleanup |
| 5:00 AM | ShipHero Cleanup | Success file cleanup |
| 6:00 AM | **Healthy Planet Database** | **Database updates** |
| 7:00 AM | **Healthy Planet Ticker** | **Ticker updates** |
| 8:30 AM | **Healthy Planet Ticker** | **Ticker updates** |
| 10:00 AM | **Healthy Planet Ticker** | **Ticker updates** |
| 11:30 AM | **Healthy Planet Ticker** | **Ticker updates** |
| 1:00 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 2:30 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 4:00 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 5:30 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 7:00 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 8:30 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 10:00 PM | **Healthy Planet Ticker** | **Ticker updates** |
| 11:30 PM | **Healthy Planet Ticker** | **Ticker updates** |

## 📊 Schedule Statistics

- **Total Daily Executions**: 16 (including existing scripts)
- **Healthy Planet Executions**: 13 per day
- **Weekly Executions**: 1 (Sunday crawler)
- **Log Files**: 3 new log files for monitoring

## 🔍 Monitoring

### Check Log Files
```bash
# View recent Healthy Planet logs
tail -f logs/cron_jobs/healthyplanet_*.log

# Check specific script logs
tail -f logs/cron_jobs/healthyplanet_crawler.log
tail -f logs/cron_jobs/healthyplanet_database_update.log
tail -f logs/cron_jobs/healthyplanet_ticker_update.log
```

### Verify Crontab
```bash
# View current crontab
crontab -l

# Check cron service status
sudo systemctl status cron
```

## ⚠️ Important Notes

1. **High Frequency**: The ticker updates run every 90 minutes, which is quite frequent
2. **Resource Usage**: Monitor system resources as this adds significant load
3. **Log Rotation**: Consider setting up log rotation for the frequent ticker updates
4. **Error Handling**: All scripts include comprehensive error handling and logging
5. **Dependencies**: The ticker script depends on the 30-day price data from `get_price_30d()`

## 🚀 Next Steps

1. **Monitor Execution**: Watch the logs for the first few runs
2. **Adjust Frequency**: Consider reducing ticker frequency if needed
3. **Set Up Alerts**: Configure monitoring for failed executions
4. **Performance Tuning**: Optimize scripts based on execution times

## 📝 Implementation Date
- **Date**: $(date)
- **Status**: ✅ Active
- **Crontab Updated**: ✅ Yes

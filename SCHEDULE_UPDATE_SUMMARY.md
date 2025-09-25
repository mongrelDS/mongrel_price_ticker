# Cron Schedule Update Summary

## Overview
Updated the cron schedule for all scripts to run Sunday through Friday (S M T W T F) with new timing as requested.

## Schedule Changes

### Updated Times (All S M T W T F)

| Script | Old Time | New Time | Cron Schedule |
|--------|----------|----------|---------------|
| shiphero_line_items.py | 1:00 AM | 1:00 AM | `0 1 * * 0,1,2,3,4,5` |
| sh_to_sql_order_line_items.py | 1:30 AM | 1:30 AM | `30 1 * * 0,1,2,3,4,5` |
| sh_to_sql_shipped_orders.py | 2:00 AM | 2:00 AM | `0 2 * * 0,1,2,3,4,5` |
| sh_to_sql_product_table.py | 2:30 AM | 2:30 AM | `30 2 * * 0,1,2,3,4,5` |
| natura_customer_profile.py | 3:00 AM | 3:00 AM | `0 3 * * 0,1,2,3,4,5` |
| archive_old_csv_files.py | 3:20 AM | 3:20 AM | `20 3 * * 0,1,2,3,4,5` |
| natura_sku_summary.py | 3:40 AM | 3:30 AM | `30 3 * * 0,1,2,3,4,5` |
| natura_fixed_fields.py | 3:50 AM | 3:40 AM | `40 3 * * 0,1,2,3,4,5` |
| customer_cohort_chart.py | 4:00 AM | 4:30 AM | `30 4 * * 0,1,2,3,4,5` |
| frozen_customer_cohort_chart.py | 4:30 AM | 5:00 AM | `0 5 * * 0,1,2,3,4,5` |
| new_vs_returning.py | N/A | 5:30 AM | `30 5 * * 0,1,2,3,4,5` |
| sql_maintenance.py | 6:00 AM | 6:00 AM | `0 6 * * 0,1,2,3,4,5` |
| healthyplanet_json_method.py | 5:00 AM | 6:30 AM | `30 6 * * 0,1,2,3,4,5` |
| wellca_json_method_from_search.py | 5:30 AM | 7:00 AM | `0 7 * * 0,1,2,3,4,5` |
| goodness_me_initial_crawl.py | 6:00 AM | 7:30 AM | `30 7 * * 0,1,2,3,4,5` |
| goodness_me_item_json_crawl.py | 6:30 AM | 8:00 AM | `0 8 * * 0,1,2,3,4,5` |
| naturesante_crawl.py | 7:00 AM | 8:30 AM | `30 8 * * 0,1,2,3,4,5` |
| naturesante_crawl_results.py | 7:30 AM | 9:00 AM | `0 9 * * 0,1,2,3,4,5` |
| naturesante_json_results.py | 8:00 AM | 9:30 AM | `30 9 * * 0,1,2,3,4,5` |

### Key Changes

1. **Schedule Pattern**: All scripts now run Sunday through Friday (S M T W T F)
2. **Time Adjustments**: 
   - Natura SKU summary moved from 3:40 AM to 3:30 AM
   - Natura fixed fields moved from 3:50 AM to 3:40 AM
   - Customer cohort chart moved from 4:00 AM to 4:30 AM
   - Frozen customer cohort chart moved from 4:30 AM to 5:00 AM
   - Added new_vs_returning.py at 5:30 AM
   - Healthy Planet JSON method moved from 5:00 AM to 6:30 AM
   - Well.ca JSON method moved from 5:30 AM to 7:00 AM
   - All scraping scripts moved later in the morning (7:30-9:30 AM)
   - Naturesante JSON results moved from 8:00 AM to 9:30 AM to avoid conflict

3. **Conflict Resolution**: 
   - Naturesante JSON results was scheduled at 8:00 AM (same as goodness_me_item_json_crawl.py)
   - Moved to 9:30 AM to avoid timing conflict

4. **Cleanup Time**: Success file cleanup moved to 10:00 AM

## Files Updated

1. **cron_schedule.txt** - Main cron schedule file
2. **updated_cron_schedule.txt** - Backup of new schedule
3. **implement_updated_schedule.sh** - Implementation script
4. **current_crontab_backup_*.txt** - Backup of current crontab

## Implementation

To implement the new schedule:

```bash
# Run the implementation script
./implement_updated_schedule.sh

# Apply the new schedule
crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt

# Verify the schedule
crontab -l
```

## Verification

- All script paths verified and exist
- Cron syntax validated
- No timing conflicts (except resolved naturesante_json_results.py)
- Success file dependencies maintained
- Logging configuration preserved

## Notes

- All scripts maintain their error checking and logging
- Success file cleanup moved to 10:00 AM to accommodate later schedule
- Well.ca and Healthy Planet pipelines maintain their existing mixed schedules
- The schedule now runs from 1:00 AM to 9:30 AM on S M T W T F

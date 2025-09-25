# Cron Schedule Update Summary v2

## Overview
Updated the cron schedule for all scripts with new timing as requested. This is the second iteration of schedule updates.

## Schedule Changes v2

### Updated Times (All S M T W T F)

| Script | Previous Time | New Time | Cron Schedule |
|--------|---------------|----------|---------------|
| shiphero_line_items.py | 1:00 AM | 1:00 AM | `0 1 * * 0,1,2,3,4,5` |
| sh_to_sql_order_line_items.py | 1:30 AM | 1:30 AM | `30 1 * * 0,1,2,3,4,5` |
| sh_to_sql_shipped_orders.py | 2:00 AM | 2:00 AM | `0 2 * * 0,1,2,3,4,5` |
| sh_to_sql_product_table.py | 2:30 AM | 2:30 AM | `30 2 * * 0,1,2,3,4,5` |
| natura_customer_profile.py | 3:00 AM | 3:00 AM | `0 3 * * 0,1,2,3,4,5` |
| archive_old_csv_files.py | 3:20 AM | 3:20 AM | `20 3 * * 0,1,2,3,4,5` |
| natura_sku_summary.py | 3:30 AM | 3:30 AM | `30 3 * * 0,1,2,3,4,5` |
| natura_fixed_fields.py | 3:40 AM | 3:40 AM | `40 3 * * 0,1,2,3,4,5` |
| customer_cohort_chart.py | 4:30 AM | 4:30 AM | `30 4 * * 0,1,2,3,4,5` |
| frozen_customer_cohort_chart.py | 5:00 AM | 5:00 AM | `0 5 * * 0,1,2,3,4,5` |
| new_vs_returning.py | 5:30 AM | 5:30 AM | `30 5 * * 0,1,2,3,4,5` |
| healthyplanet_json_method.py | 6:30 AM | **6:00 AM** | `0 6 * * 0,1,2,3,4,5` |
| wellca_json_method_from_search.py | 7:00 AM | **6:30 AM** | `30 6 * * 0,1,2,3,4,5` |
| goodness_me_initial_crawl.py | 7:30 AM | **7:00 AM** | `0 7 * * 0,1,2,3,4,5` |
| goodness_me_item_json_crawl.py | 8:00 AM | **7:30 AM** | `30 7 * * 0,1,2,3,4,5` |
| naturesante_crawl.py | 8:30 AM | **8:00 AM** | `0 8 * * 0,1,2,3,4,5` |
| naturesante_crawl_results.py | 9:00 AM | **8:30 AM** | `30 8 * * 0,1,2,3,4,5` |
| naturesante_json_results.py | 9:30 AM | **9:00 AM** | `0 9 * * 0,1,2,3,4,5` |
| sql_maintenance.py | 6:00 AM | **9:30 AM** | `30 9 * * 0,1,2,3,4,5` |

### Key Changes in v2

1. **Scraping Schedule Compression**: All scraping scripts moved earlier in the morning
   - Healthy Planet JSON method: 6:30 AM → 6:00 AM
   - Well.ca JSON method: 7:00 AM → 6:30 AM
   - Goodness Me initial crawl: 7:30 AM → 7:00 AM
   - Goodness Me item JSON crawl: 8:00 AM → 7:30 AM
   - Naturesante crawl: 8:30 AM → 8:00 AM
   - Naturesante crawl results: 9:00 AM → 8:30 AM
   - Naturesante JSON results: 9:30 AM → 9:00 AM

2. **SQL Maintenance Repositioning**: 
   - Moved from 6:00 AM to 9:30 AM (end of schedule)
   - This allows all data processing and scraping to complete before maintenance

3. **Schedule Flow**:
   - **1:00-2:30 AM**: ShipHero data pipeline
   - **3:00-3:40 AM**: Natura processing
   - **4:30-5:30 AM**: Analytics and reporting
   - **6:00-9:00 AM**: Web scraping activities
   - **9:30 AM**: SQL maintenance (final cleanup)

## Files Updated

1. **cron_schedule.txt** - Main cron schedule file (updated)
2. **implement_updated_schedule_v2.sh** - New implementation script
3. **current_crontab_backup_v2_*.txt** - Backup of current crontab
4. **SCHEDULE_UPDATE_V2_SUMMARY.md** - This summary document

## Implementation

To implement the updated schedule:

```bash
# Run the implementation script
./implement_updated_schedule_v2.sh

# Apply the new schedule
crontab /home/mongreldatalab/mongrel_price_ticker/cron_schedule.txt

# Verify the schedule
crontab -l
```

## Benefits of v2 Changes

1. **Better Resource Management**: SQL maintenance runs after all data collection is complete
2. **Compressed Scraping Window**: All scraping activities complete by 9:00 AM
3. **Logical Flow**: Data collection → Processing → Analytics → Scraping → Maintenance
4. **Reduced Conflicts**: No timing overlaps between scripts

## Verification

- All script paths verified and exist
- Cron syntax validated
- No timing conflicts
- Success file dependencies maintained
- Logging configuration preserved

## Notes

- All scripts maintain their error checking and logging
- Success file cleanup remains at 10:00 AM
- Well.ca and Healthy Planet pipelines maintain their existing mixed schedules
- The main schedule now runs from 1:00 AM to 9:30 AM on S M T W T F
- SQL maintenance moved to end of schedule for better data integrity

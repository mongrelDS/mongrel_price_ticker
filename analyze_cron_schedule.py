#!/usr/bin/env python3
"""
Analyze the cron schedule for potential issues and dependencies
"""

import re
from datetime import datetime, timedelta

# Parse the cron schedule
schedule_data = [
    {
        'script': 'shiphero_line_items.py',
        'time': '0100H',
        'cron': '0 1 * * 0,1,3,5,6',
        'description': 'ShipHero line items extraction'
    },
    {
        'script': 'sh_to_sql_shipped_orders.py', 
        'time': '0150H',
        'cron': '50 1 * * 0,1,3,5,6',
        'description': 'ShipHero shipped orders to SQL'
    },
    {
        'script': 'sh_to_sql_product_table.py',
        'time': '0230H', 
        'cron': '30 2 * * 0,1,3,5,6',
        'description': 'ShipHero product table to SQL'
    },
    {
        'script': 'natura_customer_profile.py',
        'time': '0300H',
        'cron': '0 3 * * 0,1,3,5,6', 
        'description': 'Natura customer profile processing'
    },
    {
        'script': 'archive_old_csv_files.py',
        'time': '0330H',
        'cron': '30 3 * * 0,1,3,5,6',
        'description': 'Archive old CSV files cleanup'
    }
]

def parse_cron_days(cron_days):
    """Parse cron day format (0,1,3,5,6) to day names"""
    day_map = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 
               4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
    days = [int(d) for d in cron_days.split(',')]
    return [day_map[d] for d in days]

def analyze_schedule():
    print("=" * 80)
    print("CRON SCHEDULE ANALYSIS")
    print("=" * 80)
    
    print("\n📅 SCHEDULE OVERVIEW:")
    print("-" * 50)
    for i, item in enumerate(schedule_data, 1):
        days = parse_cron_days(item['cron'].split()[-1])
        print(f"{i}. {item['script']:<35} | {item['time']} | {', '.join(days)}")
    
    print("\n⏰ TIMING ANALYSIS:")
    print("-" * 50)
    
    # Check for timing conflicts
    times = []
    for item in schedule_data:
        hour = int(item['time'][:2])
        minute = int(item['time'][2:4])
        times.append((hour, minute, item['script']))
    
    times.sort()
    
    for i, (hour, minute, script) in enumerate(times):
        print(f"{hour:02d}:{minute:02d} - {script}")
        
        # Check for potential overlaps
        if i > 0:
            prev_hour, prev_minute, prev_script = times[i-1]
            time_diff = (hour * 60 + minute) - (prev_hour * 60 + prev_minute)
            if time_diff < 30:  # Less than 30 minutes between scripts
                print(f"    ⚠️  WARNING: Only {time_diff} minutes after {prev_script}")
    
    print("\n🔗 DEPENDENCY ANALYSIS:")
    print("-" * 50)
    
    # Analyze logical dependencies
    dependencies = {
        'shiphero_line_items.py': 'Raw data extraction - no dependencies',
        'sh_to_sql_shipped_orders.py': 'Depends on: shiphero_line_items.py (needs line items data)',
        'sh_to_sql_product_table.py': 'Depends on: shiphero_line_items.py (needs product data)',
        'natura_customer_profile.py': 'Independent - processes customer data',
        'archive_old_csv_files.py': 'Cleanup - should run after all data processing'
    }
    
    for script, dep_info in dependencies.items():
        print(f"• {script}:")
        print(f"  {dep_info}")
    
    print("\n⚠️  POTENTIAL ISSUES:")
    print("-" * 50)
    
    issues = []
    
    # Check if dependencies have enough time
    if times[1][0] == times[0][0] and times[1][1] - times[0][1] < 30:
        issues.append("sh_to_sql_shipped_orders.py runs only 50 minutes after shiphero_line_items.py - may not have enough time to complete")
    
    if times[2][0] == times[1][0] and times[2][1] - times[1][1] < 30:
        issues.append("sh_to_sql_product_table.py runs only 40 minutes after sh_to_sql_shipped_orders.py - potential overlap")
    
    if times[3][0] == times[2][0] and times[3][1] - times[2][1] < 30:
        issues.append("natura_customer_profile.py runs only 30 minutes after sh_to_sql_product_table.py - potential overlap")
    
    if times[4][0] == times[3][0] and times[4][1] - times[3][1] < 30:
        issues.append("archive_old_csv_files.py runs only 30 minutes after natura_customer_profile.py - potential overlap")
    
    # Check for missing days
    all_days = set()
    for item in schedule_data:
        days = [int(d) for d in item['cron'].split()[-1].split(',')]
        all_days.update(days)
    
    missing_days = set(range(7)) - all_days
    if missing_days:
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        missing_day_names = [day_names[d] for d in missing_days]
        issues.append(f"Scripts don't run on: {', '.join(missing_day_names)}")
    
    if issues:
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    else:
        print("✅ No obvious issues detected")
    
    print("\n💡 RECOMMENDATIONS:")
    print("-" * 50)
    print("1. Consider adding 15-30 minute buffers between dependent scripts")
    print("2. Monitor script execution times to ensure no overlaps")
    print("3. Add error handling and logging to detect failures")
    print("4. Consider running archive_old_csv_files.py later (e.g., 4:00 AM)")
    print("5. Add health checks to ensure dependencies completed successfully")
    
    print("\n📊 EXECUTION FREQUENCY:")
    print("-" * 50)
    days_per_week = len(parse_cron_days(schedule_data[0]['cron'].split()[-1]))
    print(f"Scripts run {days_per_week} days per week")
    print(f"Total daily execution time: ~3.5 hours (1:00 AM - 4:30 AM)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    analyze_schedule()

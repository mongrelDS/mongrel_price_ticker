#!/bin/bash
# Cron Job Monitoring Script
# Checks the status of all scheduled jobs

echo "=========================================="
echo "CRON JOB MONITORING REPORT"
echo "=========================================="
echo "Generated: $(date)"
echo ""

# Check if log directory exists
if [ ! -d "/var/log/cron_jobs" ]; then
    echo "⚠️  Log directory /var/log/cron_jobs not found"
    echo "Creating local log directory..."
    mkdir -p logs/cron_jobs
    LOG_DIR="logs/cron_jobs"
else
    LOG_DIR="/var/log/cron_jobs"
fi

echo "📁 Log Directory: $LOG_DIR"
echo ""

# Function to check job status
check_job() {
    local job_name="$1"
    local log_file="$2"
    local success_file="$3"
    
    echo "🔍 $job_name:"
    
    # Check if log file exists
    if [ -f "$log_file" ]; then
        # Get last run time
        last_run=$(stat -c %y "$log_file" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo "   Last run: $last_run"
        
        # Check for errors in last 10 lines
        errors=$(tail -10 "$log_file" 2>/dev/null | grep -i "error\|failed\|exception" | wc -l)
        if [ "$errors" -gt 0 ]; then
            echo "   ❌ Status: ERRORS FOUND ($errors error lines)"
        else
            echo "   ✅ Status: No recent errors"
        fi
        
        # Check file size
        size=$(du -h "$log_file" 2>/dev/null | cut -f1)
        echo "   📊 Log size: $size"
    else
        echo "   ⚠️  No log file found"
    fi
    
    # Check success file if provided
    if [ -n "$success_file" ]; then
        if [ -f "$success_file" ]; then
            success_time=$(stat -c %y "$success_file" 2>/dev/null | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo "   ✅ Success file: $success_time"
        else
            echo "   ❌ Success file: NOT FOUND"
        fi
    fi
    echo ""
}

# Check ShipHero jobs
echo "🚢 SHIPHERO DATA PIPELINE:"
echo "------------------------"
check_job "Line Items" "$LOG_DIR/shiphero_line_items.log" "/tmp/shiphero_line_items.success"
check_job "Shipped Orders" "$LOG_DIR/shipped_orders.log" "/tmp/shipped_orders.success"
check_job "Product Table" "$LOG_DIR/product_table.log" "/tmp/product_table.success"

# Check Natura jobs
echo "👥 NATURA CUSTOMER PROFILES:"
echo "---------------------------"
check_job "Customer Profiles" "$LOG_DIR/natura_customer.log" "/tmp/natura_customer.success"

# Check Archive jobs
echo "🗄️  ARCHIVE OPERATIONS:"
echo "---------------------"
check_job "Archive Files" "$LOG_DIR/archive_files.log" ""

# Check Well.ca jobs
echo "🛒 WELL.CA SCRAPING:"
echo "------------------"
check_job "Brand Links" "$LOG_DIR/wellca_brand_links.log" ""
check_job "Product Links" "$LOG_DIR/wellca_product_links.log" ""
check_job "Price Updates" "$LOG_DIR/wellca_price_update.log" ""

# Check current crontab
echo "⏰ CURRENT CRONTAB:"
echo "-----------------"
if crontab -l >/dev/null 2>&1; then
    job_count=$(crontab -l | grep -v '^#' | grep -v '^$' | wc -l)
    echo "Active cron jobs: $job_count"
    echo ""
    echo "Recent entries:"
    crontab -l | tail -5
else
    echo "❌ No crontab found or error accessing crontab"
fi

echo ""
echo "=========================================="
echo "MONITORING COMPLETE"
echo "=========================================="

#!/usr/bin/env python3
"""
Well.ca Price Ticker Pipeline Runner

This script runs the complete Well.ca price tracking pipeline:
1. Get brand links
2. Extract product links from brands
3. Update product prices and metadata
4. Generate 30-day price analysis

Usage:
    python run_wellca_pipeline.py [--step STEP] [--all]
    
Options:
    --step STEP    Run specific step (brands, products, prices, analysis)
    --all          Run all steps in sequence
"""

import sys
import os
import argparse
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_brand_links():
    """Step 1: Get brand links from Well.ca"""
    print("🔗 Step 1: Getting brand links...")
    os.system("python3 scrapers/wellca_brand_link_list.py")
    print("✅ Brand links completed\n")

def run_product_links():
    """Step 2: Extract product links from brand pages"""
    print("📦 Step 2: Extracting product links...")
    os.system("python3 scrapers/wellca_links_from_brands.py")
    print("✅ Product links completed\n")

def run_price_update():
    """Step 3: Update product prices and metadata"""
    print("💰 Step 3: Updating product prices...")
    os.system("python3 scrapers/wellca_price_update.py")
    print("✅ Price update completed\n")

def run_analysis():
    """Step 4: Generate 30-day price analysis"""
    print("📊 Step 4: Generating price analysis...")
    os.system("python3 analytics/df_price_30d.py")
    print("✅ Analysis completed\n")

def main():
    parser = argparse.ArgumentParser(description='Well.ca Price Ticker Pipeline')
    parser.add_argument('--step', choices=['brands', 'products', 'prices', 'analysis'], 
                       help='Run specific step')
    parser.add_argument('--all', action='store_true', 
                       help='Run all steps in sequence')
    
    args = parser.parse_args()
    
    print(f"🚀 Well.ca Price Ticker Pipeline - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if args.all:
        print("🔄 Running complete pipeline...")
        run_brand_links()
        run_product_links()
        run_price_update()
        run_analysis()
        print("🎉 Complete pipeline finished!")
        
    elif args.step:
        if args.step == 'brands':
            run_brand_links()
        elif args.step == 'products':
            run_product_links()
        elif args.step == 'prices':
            run_price_update()
        elif args.step == 'analysis':
            run_analysis()
    else:
        print("❌ Please specify --step or --all")
        parser.print_help()

if __name__ == "__main__":
    main()

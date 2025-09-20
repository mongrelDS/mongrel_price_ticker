#!/usr/bin/env python3
"""
Upsert Healthy Planet Links to MySQL Database

This script scrapes Healthy Planet links and upserts them to the cat_link_list table.
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(project_root)

from src.mySQL_Upsert_Function_v2 import upsert_df_to_mysql
from src.database_config import get_database_engine
from scripts.scrapers.healthyplanet.healthyplanet_scraper import get_healthyplanet_links

def prepare_links_for_upsert(df_links):
    """
    Prepare the links DataFrame for database upsert.
    Adds necessary columns for the cat_link_list table.
    """
    if df_links is None or df_links.empty:
        print("❌ No links to upsert")
        return None
    
    print("📊 Preparing links for database upsert...")
    
    # Create a copy of the DataFrame
    df_prepared = df_links.copy()
    
    # Add required columns for cat_link_list table
    df_prepared['id'] = range(1, len(df_prepared) + 1)  # Simple auto-increment ID
    df_prepared['source'] = 'healthyplanet'
    df_prepared['scraped_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    df_prepared['status'] = 'active'
    df_prepared['category'] = 'general'  # Default category
    
    # Rename 'link' to 'url' if that's the expected column name
    if 'link' in df_prepared.columns:
        df_prepared = df_prepared.rename(columns={'link': 'url'})
    
    # Reorder columns
    column_order = ['id', 'url', 'source', 'category', 'status', 'scraped_date']
    df_prepared = df_prepared[column_order]
    
    print(f"✅ Prepared {len(df_prepared)} links for upsert")
    print(f"📋 Columns: {list(df_prepared.columns)}")
    
    return df_prepared

def upsert_healthyplanet_links():
    """
    Main function to scrape Healthy Planet links and upsert to database.
    """
    print("🚀 Healthy Planet Links Upsert Process")
    print("=" * 60)
    
    try:
        # Step 1: Get database engine
        print("\n" + "="*60)
        print("STEP 1: DATABASE CONNECTION")
        print("="*60)
        engine = get_database_engine()
        print("✅ Database engine created successfully")
        
        # Step 2: Scrape Healthy Planet links
        print("\n" + "="*60)
        print("STEP 2: SCRAPING HEALTHY PLANET LINKS")
        print("="*60)
        df_links = get_healthyplanet_links()
        
        if df_links is None or df_links.empty:
            print("❌ No links scraped. Exiting.")
            return False
        
        print(f"✅ Successfully scraped {len(df_links)} links")
        
        # Step 3: Prepare data for upsert
        print("\n" + "="*60)
        print("STEP 3: PREPARING DATA FOR UPSERT")
        print("="*60)
        df_prepared = prepare_links_for_upsert(df_links)
        
        if df_prepared is None:
            print("❌ Failed to prepare data. Exiting.")
            return False
        
        # Step 4: Upsert to database
        print("\n" + "="*60)
        print("STEP 4: UPSERTING TO DATABASE")
        print("="*60)
        
        # Define custom data types for the table using SQLAlchemy types
        from sqlalchemy import types
        
        custom_dtypes = {
            'id': types.Integer,
            'url': types.Text,
            'source': types.String(50),
            'category': types.String(100),
            'status': types.String(20),
            'scraped_date': types.DateTime
        }
        
        # Upsert to cat_link_list table
        upsert_df_to_mysql(
            df=df_prepared,
            engine=engine,
            target_table='cat_link_list',
            key_col='id',
            custom_dtypes=custom_dtypes,
            max_retries=3
        )
        
        print("\n" + "="*60)
        print("UPSERT COMPLETE - FINAL SUMMARY")
        print("="*60)
        print(f"✅ Successfully upserted {len(df_prepared)} Healthy Planet links!")
        print(f"📊 Table: cat_link_list")
        print(f"📊 Source: healthyplanet")
        print(f"📊 Status: active")
        print(f"📊 Scraped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during upsert process: {e}")
        return False

def main():
    """Main execution function"""
    success = upsert_healthyplanet_links()
    
    if success:
        print("\n🎉 Healthy Planet links upsert completed successfully!")
    else:
        print("\n❌ Healthy Planet links upsert failed!")
    
    return success

if __name__ == "__main__":
    main()

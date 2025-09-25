#!/usr/bin/env python3
"""
Test script for market_price_list creation with a small subset of data
"""

import mysql.connector
import pandas as pd
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_market_price_list():
    """Test creating market_price_list with a small subset of data"""
    
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'srv1978.hstgr.io'),
            port=int(os.getenv('DB_PORT', '3306')),
            user=os.getenv('DB_USER', 'u488367489_mongrel_data'),
            password=os.getenv('DB_PASSWORD', 'taan2#IbizaI'),
            database=os.getenv('DB_NAME', 'u488367489_Price_Ticker')
        )
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        create_table_query = """
        CREATE TABLE IF NOT EXISTS market_price_list (
            sku VARCHAR(255) PRIMARY KEY,
            brand TEXT,
            title TEXT,
            barcode TEXT,
            vol TEXT,
            keywords TEXT,
            imgurl TEXT,
            price DOUBLE,
            tag TEXT,
            link TEXT,
            domain TEXT,
            `key` VARCHAR(255),
            date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        logger.info("Table created or already exists")
        
        # Get sample from fixed_fields that have matches in df_ticker (excluding naturamarket)
        logger.info("Fetching sample data from fixed_fields with non-naturamarket matches...")
        fixed_fields_query = """
        SELECT DISTINCT f.sku, f.brand, f.title, f.barcode, f.vol, f.keywords, f.imgurl
        FROM fixed_fields f
        INNER JOIN df_ticker t ON f.sku = t.sku
        WHERE f.sku IS NOT NULL AND f.sku != ''
        AND (t.domain IS NULL OR t.domain != 'naturamarket.ca')
        AND (t.link IS NULL OR t.link NOT LIKE '%naturamarket%')
        LIMIT 100
        """
        cursor.execute(fixed_fields_query)
        fixed_fields_data = cursor.fetchall()
        fixed_fields_columns = [desc[0] for desc in cursor.description]
        df_fixed_fields = pd.DataFrame(fixed_fields_data, columns=fixed_fields_columns)
        
        logger.info(f"Retrieved {len(df_fixed_fields)} records from fixed_fields")
        
        # Get matching data from df_ticker (excluding naturamarket links)
        logger.info("Fetching matching data from df_ticker (excluding naturamarket links)...")
        if len(df_fixed_fields) > 0:
            skus = "', '".join(df_fixed_fields['sku'].astype(str))
            ticker_query = f"""
            SELECT sku, price, tag, link, domain, `key`, date
            FROM df_ticker
            WHERE sku IN ('{skus}')
            AND (domain IS NULL OR domain != 'naturamarket.ca')
            AND (link IS NULL OR link NOT LIKE '%naturamarket%')
            """
            cursor.execute(ticker_query)
            ticker_data = cursor.fetchall()
            ticker_columns = [desc[0] for desc in cursor.description]
            df_price_30d = pd.DataFrame(ticker_data, columns=ticker_columns)
            
            logger.info(f"Retrieved {len(df_price_30d)} records from df_ticker")
            
            # Merge data
            df_market_price_list = pd.merge(
                df_fixed_fields, 
                df_price_30d, 
                on='sku', 
                how='inner',
                suffixes=('_fixed', '_ticker')
            )
            
            logger.info(f"Merged data contains {len(df_market_price_list)} records")
            
            if len(df_market_price_list) > 0:
                # Insert data
                upsert_query = """
                INSERT INTO market_price_list (
                    sku, brand, title, barcode, vol, keywords, imgurl,
                    price, tag, link, domain, `key`, date
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON DUPLICATE KEY UPDATE
                    brand = VALUES(brand),
                    title = VALUES(title),
                    barcode = VALUES(barcode),
                    vol = VALUES(vol),
                    keywords = VALUES(keywords),
                    imgurl = VALUES(imgurl),
                    price = VALUES(price),
                    tag = VALUES(tag),
                    link = VALUES(link),
                    domain = VALUES(domain),
                    `key` = VALUES(`key`),
                    date = VALUES(date)
                """
                
                # Prepare data
                upsert_data = []
                for _, row in df_market_price_list.iterrows():
                    upsert_data.append((
                        row['sku'],
                        row.get('brand', None),
                        row.get('title', None),
                        row.get('barcode', None),
                        row.get('vol', None),
                        row.get('keywords', None),
                        row.get('imgurl', None),
                        row.get('price', None),
                        row.get('tag', None),
                        row.get('link', None),
                        row.get('domain', None),
                        row.get('key', None),
                        row.get('date', None)
                    ))
                
                # Insert in small batches
                batch_size = 10
                total_inserted = 0
                
                for i in range(0, len(upsert_data), batch_size):
                    batch = upsert_data[i:i + batch_size]
                    try:
                        cursor.executemany(upsert_query, batch)
                        total_inserted += len(batch)
                        logger.info(f"Inserted batch {i//batch_size + 1}, total: {total_inserted}")
                    except Exception as e:
                        logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
                
                conn.commit()
                logger.info(f"Successfully inserted {total_inserted} records")
                
                # Verify data
                cursor.execute("SELECT COUNT(*) FROM market_price_list")
                count = cursor.fetchone()[0]
                logger.info(f"Total records in market_price_list: {count}")
                
                # Show sample
                cursor.execute("SELECT sku, brand, title, price, domain FROM market_price_list LIMIT 3")
                samples = cursor.fetchall()
                logger.info("Sample records:")
                for sample in samples:
                    logger.info(f"  SKU: {sample[0]}, Brand: {sample[1]}, Title: {sample[2][:30]}..., Price: {sample[3]}, Domain: {sample[4]}")
            else:
                logger.warning("No matching records found")
        else:
            logger.warning("No data found in fixed_fields")
            
        cursor.close()
        conn.close()
        logger.info("Test completed successfully")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    test_market_price_list()

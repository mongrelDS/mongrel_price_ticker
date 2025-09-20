#!/usr/bin/env python3
"""
Example script showing how to use the google_drive_csv_import function.
This script demonstrates different ways to import CSV data from Google Drive.
"""

import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))

from google_drive_csv_import import import_csv_from_drive

def main():
    """Example usage of the google_drive_csv_import function."""
    
    print("=== Google Drive CSV Import Example ===\n")
    
    # Example 1: Using default parameters
    print("1. Importing with default parameters:")
    df1 = import_csv_from_drive()
    
    if df1 is not None:
        print(f"   ✅ Successfully imported {len(df1)} rows")
        print(f"   Columns: {list(df1.columns)}")
    else:
        print("   ❌ No data imported")
    
    print("\n" + "="*50 + "\n")
    
    # Example 2: Using custom parameters
    print("2. Importing with custom parameters:")
    df2 = import_csv_from_drive(
        starts_with="product_table",
        google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
    )
    
    if df2 is not None:
        print(f"   ✅ Successfully imported {len(df2)} rows")
        print(f"   Sample data:")
        print(df2.head(3))
    else:
        print("   ❌ No data imported")
    
    print("\n" + "="*50 + "\n")
    
    # Example 3: Using multiple file prefixes
    print("3. Importing with multiple file prefixes:")
    df3 = import_csv_from_drive(
        starts_with=["product_table", "ALL_Products"],
        google_drive_id="1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn"
    )
    
    if df3 is not None:
        print(f"   ✅ Successfully imported {len(df3)} rows")
        print(f"   Data types:")
        print(df3.dtypes)
    else:
        print("   ❌ No data imported")
    
    print("\n=== Example completed ===")

if __name__ == "__main__":
    main()

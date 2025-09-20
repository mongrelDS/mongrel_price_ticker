#!/usr/bin/env python3
"""
Show the organized scraper structure
"""

import os
import sys

def show_directory_structure(path, prefix="", max_depth=3, current_depth=0):
    """Display directory structure"""
    
    if current_depth >= max_depth:
        return
    
    try:
        items = sorted(os.listdir(path))
        for i, item in enumerate(items):
            if item.startswith('.'):
                continue
                
            item_path = os.path.join(path, item)
            is_last = i == len(items) - 1
            
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item}")
            
            if os.path.isdir(item_path):
                next_prefix = prefix + ("    " if is_last else "│   ")
                show_directory_structure(item_path, next_prefix, max_depth, current_depth + 1)
                
    except PermissionError:
        print(f"{prefix}└── [Permission Denied]")

def main():
    """Main function to show structure"""
    print("📁 Organized Scraper Structure")
    print("=" * 50)
    
    # Get the scripts directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"📂 {script_dir}")
    show_directory_structure(script_dir, max_depth=2)
    
    print("\n🚀 Quick Usage Examples:")
    print("=" * 50)
    
    print("1. Healthy Planet DataFrame Pipeline:")
    print("   from scripts.scrapers.healthyplanet.healthyplanet_dataframe_only import get_healthyplanet_links")
    print("   df_links = get_healthyplanet_links()")
    
    print("\n2. Well.ca Price Update:")
    print("   from scripts.scrapers.wellca.wellca_price_update import main as wellca_main")
    print("   wellca_main()")
    
    print("\n3. Examples:")
    print("   python3 scripts/examples/example_dataframe_usage.py")
    
    print("\n✅ Structure organized successfully!")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Debug script for link processing logic
"""

import pandas as pd

def debug_link_processing():
    """Debug the link processing logic."""
    print("🔍 Debugging link processing logic...")
    
    # Create test data
    test_links = [
        "https://www.healthyplanetcanada.com/products/test.html",
        "https://www.healthyplanetcanada.com/categories/supplements",
        "https://www.healthyplanetcanada.com/blog/article",
        "https://www.healthyplanetcanada.com/products/another.html"
    ]
    
    df_link = pd.DataFrame({'link': test_links})
    print("Original links:")
    print(df_link)
    print()
    
    # Process links as the crawler does
    df_link['link'] = df_link['link'].str.rstrip('/')
    df_link['slash_count'] = df_link['link'].str.count('/')
    
    print("After processing:")
    print(df_link)
    print()
    
    print("Slash counts:")
    for i, row in df_link.iterrows():
        print(f"  {row['link']} -> {row['slash_count']} slashes")
    print()
    
    # Test product links (slash_count == 3 and contains 'html')
    df_link_item = df_link[(df_link['slash_count'] == 3) & (df_link['link'].str.contains('html', na=False))]
    print("Product links (slash_count == 3 and contains 'html'):")
    print(df_link_item)
    print()
    
    # Test category links (slash_count > 3 or doesn't contain 'html')
    df_catlink = df_link[(df_link['slash_count'] > 3) | (~df_link['link'].str.contains('html', na=False))]
    print("Category links (slash_count > 3 or doesn't contain 'html'):")
    print(df_catlink)
    print()
    
    # Remove blog links
    df_catlink = df_catlink[~df_catlink['link'].str.contains('/blog/', na=False)]
    print("Category links after removing blog links:")
    print(df_catlink)

if __name__ == "__main__":
    debug_link_processing()

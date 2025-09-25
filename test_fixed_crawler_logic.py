#!/usr/bin/env python3
"""
Test script for the fixed crawler logic
"""

import pandas as pd

def test_fixed_crawler_logic():
    """Test the fixed crawler logic with realistic URLs."""
    print("🧪 Testing fixed crawler logic...")
    
    # Create realistic test data based on actual Healthy Planet URL structure
    test_links = [
        # Product links (4 slashes, contains .html)
        "https://www.healthyplanetcanada.com/products/vitamin-d3-1000-iu.html",
        "https://www.healthyplanetcanada.com/products/omega-3-fish-oil.html",
        
        # Category links (4 slashes, no .html)
        "https://www.healthyplanetcanada.com/categories/vitamins",
        "https://www.healthyplanetcanada.com/categories/supplements",
        
        # Subcategory links (5+ slashes)
        "https://www.healthyplanetcanada.com/categories/vitamins/vitamin-d",
        "https://www.healthyplanetcanada.com/categories/supplements/omega-3",
        
        # Blog links (should be filtered out)
        "https://www.healthyplanetcanada.com/blog/health-tips",
        "https://www.healthyplanetcanada.com/blog/nutrition-guide",
        
        # Other pages
        "https://www.healthyplanetcanada.com/about-us",
        "https://www.healthyplanetcanada.com/contact"
    ]
    
    df_link = pd.DataFrame({'link': test_links})
    print("Original links:")
    for i, link in enumerate(test_links):
        print(f"  {i+1}. {link}")
    print()
    
    # Process links as the crawler does
    df_link['link'] = df_link['link'].str.rstrip('/')
    df_link['slash_count'] = df_link['link'].str.count('/')
    
    print("Slash counts:")
    for i, row in df_link.iterrows():
        print(f"  {row['link']} -> {row['slash_count']} slashes")
    print()
    
    # Test product links (slash_count == 4 and contains 'html')
    df_link_item = df_link[(df_link['slash_count'] == 4) & (df_link['link'].str.contains('html', na=False))]
    print("Product links (slash_count == 4 and contains 'html'):")
    for i, row in df_link_item.iterrows():
        print(f"  {row['link']}")
    print(f"Count: {len(df_link_item)}")
    print()
    
    # Test category links (slash_count > 4 or doesn't contain 'html')
    df_catlink = df_link[(df_link['slash_count'] > 4) | (~df_link['link'].str.contains('html', na=False))]
    print("Category links (slash_count > 4 or doesn't contain 'html'):")
    for i, row in df_catlink.iterrows():
        print(f"  {row['link']}")
    print(f"Count: {len(df_catlink)}")
    print()
    
    # Remove blog links
    df_catlink = df_catlink[~df_catlink['link'].str.contains('/blog/', na=False)]
    print("Category links after removing blog links:")
    for i, row in df_catlink.iterrows():
        print(f"  {row['link']}")
    print(f"Count: {len(df_catlink)}")
    print()
    
    # Verify results
    expected_product_links = 2  # Two product links with .html
    expected_category_links = 6  # 2 categories + 2 subcategories + 2 other pages (blog removed)
    
    print("Verification:")
    print(f"  Product links: {len(df_link_item)} (expected: {expected_product_links})")
    print(f"  Category links: {len(df_catlink)} (expected: {expected_category_links})")
    
    success = (len(df_link_item) == expected_product_links and 
               len(df_catlink) == expected_category_links)
    
    if success:
        print("✅ Fixed crawler logic works correctly!")
    else:
        print("❌ Fixed crawler logic needs more adjustment")
    
    return success

if __name__ == "__main__":
    test_fixed_crawler_logic()

#!/usr/bin/env python3
"""
Example usage of the Healthy Planet DataFrame-Only Pipeline
"""

from scripts.scrapers.healthyplanet.healthyplanet_scraper import get_healthyplanet_links

def example_basic_usage():
    """Example: Basic usage - get DataFrame directly"""
    print("🚀 Example: Basic DataFrame Usage")
    print("=" * 50)
    
    # Get the DataFrame directly
    df_links = get_healthyplanet_links()
    
    if df_links is not None:
        print(f"✅ Successfully got DataFrame!")
        print(f"📊 Shape: {df_links.shape}")
        print(f"📊 Columns: {list(df_links.columns)}")
        print(f"🔗 Sample links:")
        for i, url in enumerate(df_links['link'].head(5), 1):
            print(f"  {i}. {url}")
        return df_links
    else:
        print("❌ Failed to get DataFrame")
        return None

def example_filter_categories(df_links):
    """Example: Filter for specific page types"""
    print("\n🚀 Example: Filtering Categories")
    print("=" * 50)
    
    if df_links is None:
        print("❌ No DataFrame to filter")
        return
    
    # Filter for category pages
    category_pages = df_links[df_links['link'].str.contains('/vitamins-supplements/', case=False, na=False)]
    print(f"📂 Found {len(category_pages)} category pages")
    
    # Filter for product pages
    product_pages = df_links[df_links['link'].str.contains('/product/', case=False, na=False)]
    print(f"🛍️ Found {len(product_pages)} product pages")
    
    # Filter for brand pages
    brand_pages = df_links[df_links['link'].str.contains('/brand/', case=False, na=False)]
    print(f"🏷️ Found {len(brand_pages)} brand pages")
    
    return {
        'categories': category_pages,
        'products': product_pages,
        'brands': brand_pages
    }

def example_work_with_dataframe(df_links):
    """Example: Work with the DataFrame"""
    print("\n🚀 Example: Working with DataFrame")
    print("=" * 50)
    
    if df_links is None:
        print("❌ No DataFrame to work with")
        return
    
    # Get basic info
    print(f"📊 Total links: {len(df_links)}")
    print(f"📊 Unique links: {df_links['link'].nunique()}")
    
    # Get domain info
    from urllib.parse import urlparse
    df_links['domain'] = df_links['link'].apply(lambda x: urlparse(x).netloc)
    print(f"📊 Unique domains: {df_links['domain'].nunique()}")
    
    # Get path info
    df_links['path'] = df_links['link'].apply(lambda x: urlparse(x).path)
    print(f"📊 Unique paths: {df_links['path'].nunique()}")
    
    # Show most common paths
    print(f"\n📊 Most common paths:")
    path_counts = df_links['path'].value_counts().head(5)
    for path, count in path_counts.items():
        print(f"  {path}: {count} links")
    
    return df_links

def example_export_if_needed(df_links):
    """Example: Export to CSV only if needed"""
    print("\n🚀 Example: Export Only If Needed")
    print("=" * 50)
    
    if df_links is None:
        print("❌ No DataFrame to export")
        return
    
    # You can export to CSV if needed
    # df_links.to_csv("my_export.csv", index=False)
    # print("💾 Exported to my_export.csv")
    
    # Or work with the DataFrame directly
    print("✅ Working with DataFrame directly - no CSV files created")
    print(f"📊 DataFrame has {len(df_links)} rows and {len(df_links.columns)} columns")

if __name__ == "__main__":
    # Run examples
    df_links = example_basic_usage()
    
    if df_links is not None:
        filtered_data = example_filter_categories(df_links)
        df_links = example_work_with_dataframe(df_links)
        example_export_if_needed(df_links)
        
        print(f"\n🎉 All examples completed!")
        print(f"📊 Final DataFrame shape: {df_links.shape}")
    else:
        print("\n❌ Examples failed - no DataFrame available")

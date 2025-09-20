#!/usr/bin/env python3
"""
Example usage of the Healthy Planet Complete Pipeline
"""

from scripts.scrapers.healthyplanet.healthyplanet_scraper import get_healthyplanet_links, HealthyPlanetScraper

def example_basic_usage():
    """Example: Basic usage of the pipeline"""
    print("🚀 Example: Basic Pipeline Usage")
    print("=" * 50)
    
    # Run the complete pipeline
    df_links = get_healthyplanet_links()
    
    if df_links is not None:
        print(f"\n✅ Pipeline completed successfully!")
        print(f"📊 Found {len(df_links)} clean URLs")
        print(f"🔗 Sample URLs:")
        for i, url in enumerate(df_links['link'].head(5), 1):
            print(f"  {i}. {url}")
    else:
        print("❌ Pipeline failed")

def example_custom_usage():
    """Example: Custom usage with specific steps"""
    print("\n🚀 Example: Custom Pipeline Usage")
    print("=" * 50)
    
    # Create scraper instance
    scraper = HealthyPlanetScraper()
    scraper.create_session()
    
    # Test proxy
    if scraper.test_proxy_connection():
        print("✅ Proxy is working, ready to scrape")
        
        # You can now use the scraper for custom scraping
        # For example, scrape a specific page:
        # response = scraper.session.get("https://www.healthyplanetcanada.com/vitamins-supplements.html")
        # ... process response ...
        
    else:
        print("❌ Proxy not working")

def example_dataframe_operations():
    """Example: Working with the resulting DataFrame"""
    print("\n🚀 Example: DataFrame Operations")
    print("=" * 50)
    
    try:
        import pandas as pd
        
        # Load the cleaned data
        df_links = pd.read_csv("healthyplanet_cleaned_links.csv")
        print(f"📊 Loaded {len(df_links)} URLs from CSV")
        
        # Filter for specific types of pages
        category_pages = df_links[df_links['link'].str.contains('/vitamins-supplements/', case=False, na=False)]
        print(f"📂 Found {len(category_pages)} category pages")
        
        # Show sample category pages
        print("🔗 Sample category pages:")
        for i, url in enumerate(category_pages['link'].head(3), 1):
            print(f"  {i}. {url}")
            
    except FileNotFoundError:
        print("❌ CSV file not found. Run the pipeline first.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Run examples
    example_basic_usage()
    example_custom_usage()
    example_dataframe_operations()

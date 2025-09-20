# Healthy Planet Scraping Pipeline

A comprehensive Python script that scrapes the Healthy Planet Canada website (front page and sitemap) to collect, filter, and clean all internal links.

## 🚀 Features

- **Proxy Support**: Uses IPBurger residential proxy to bypass anti-bot protection
- **Multi-Page Scraping**: Scrapes both front page and sitemap page
- **Complete Pipeline**: 5-step process from scraping to analysis
- **URL Cleaning**: Removes tracking parameters and normalizes URLs
- **Data Analysis**: Categorizes links by type (categories, products, etc.)
- **Deduplication**: Removes duplicate links across all scraped pages

## 📋 Pipeline Steps

### Step 1: Scrape All Pages
- Scrapes `https://www.healthyplanetcanada.com/` (front page)
- Scrapes `https://www.healthyplanetcanada.com/sitemap` (sitemap page)
- Collects all links from both pages
- Handles compressed content (gzip)
- Uses realistic browser headers
- Removes duplicates across pages

### Step 2: Create DataFrame
- Converts links to pandas DataFrame
- Adds analysis columns (domain, path, internal, etc.)
- Categorizes links by type

### Step 3: Filter Internal Links
- Keeps only `healthyplanetcanada.com` links
- Removes external links (Uber Eats, Instacart, etc.)
- Simplifies to single 'link' column

### Step 4: Clean URLs
- Removes tracking parameters (UTM, gclid, fbclid, etc.)
- Removes session parameters (SID, PHPSESSID, etc.)
- Normalizes paths and removes duplicates
- Removes URL fragments

### Step 5: Analyze Results
- Categorizes links by page type
- Shows statistics and sample URLs
- Provides summary of findings

## 🛠️ Usage

### Basic Usage
```python
from healthyplanet_complete_pipeline import main

# Run the complete pipeline
df_links = main()
```

### Custom Usage
```python
from healthyplanet_complete_pipeline import create_session_with_proxy, test_proxy_connection

# Create session with proxy
session = create_session_with_proxy()

# Test proxy connection
if test_proxy_connection(session):
    # Use session for custom scraping
    response = session.get("https://www.healthyplanetcanada.com/vitamins-supplements.html")
```

## 📁 Output Files

The pipeline creates three CSV files:

1. **`healthyplanet_front_page_links.csv`** - Original data with all columns
2. **`healthyplanet_internal_links.csv`** - Filtered internal links only
3. **`healthyplanet_cleaned_links.csv`** - Final cleaned and deduplicated URLs

## 📊 Sample Results

```
✅ Successfully processed 1355 clean, unique URLs!

📊 URL Categories:
  Homepage: 2 links
  Category Pages: 406 links
  Account Pages: 3 links
  Cart/Checkout: 1 links
  Store Pages: 2 links
  Other Pages: 943 links
```

## 🔧 Requirements

- Python 3.6+
- requests
- beautifulsoup4
- pandas
- urllib3

## 🌐 Proxy Configuration

The script uses IPBurger residential proxy:
- **Host**: residential.ipb.cloud
- **Port**: 7777
- **Protocol**: HTTP
- **Authentication**: Username/Password

## ⚠️ Notes

- The script includes random delays to appear human-like
- Headers are configured to mimic a real browser
- Content compression is handled automatically
- Duplicate URLs are removed after cleaning

## 🚀 Next Steps

After running the pipeline, you can:
1. Filter for specific page types (categories, products)
2. Scrape individual pages for detailed data
3. Set up automated monitoring
4. Integrate with your existing data pipeline

## 📝 Example

```bash
cd /path/to/your/project
python3 scripts/scrapers/healthyplanet_complete_pipeline.py
```

This will run the complete pipeline and create all output files.

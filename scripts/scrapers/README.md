# Scrapers Directory

This directory contains all web scraping scripts organized by website and purpose.

## 📁 Directory Structure

```
scrapers/
├── healthyplanet/          # Healthy Planet Canada scrapers
│   ├── healthyplanet_scraper.py           # Main scraper (all functionality)
│   └── README_healthyplanet_pipeline.md   # Documentation
├── wellca/                 # Well.ca scrapers
│   ├── wellca_price_update.py             # Price update scraper
│   ├── wellca_brand_link_list.py          # Brand links scraper
│   └── wellca_links_from_brands.py        # Links from brands scraper
├── examples/               # Usage examples
│   ├── example_usage.py                   # Basic usage examples
│   └── example_dataframe_usage.py         # DataFrame usage examples
└── utilities/              # Utility scripts
    ├── test_proxy_*.py                    # Proxy testing scripts
    └── test_*.py                          # Various test scripts
```

## 🚀 Quick Start

### Healthy Planet Scraping
```python
# Import the main scraper
from scripts.scrapers.healthyplanet.healthyplanet_scraper import get_healthyplanet_links

# Get DataFrame with cleaned URLs
df_links = get_healthyplanet_links()
```

### Well.ca Scraping
```python
# Import Well.ca scrapers
from scripts.scrapers.wellca.wellca_price_update import main as wellca_main

# Run Well.ca price update
wellca_main()
```

## 📊 Main Pipelines

### 1. Healthy Planet Scraper
- **File:** `healthyplanet/healthyplanet_scraper.py`
- **Purpose:** Complete scraper with all functionality
- **Output:** pandas DataFrame with 1355 unique URLs
- **Features:** Proxy support, URL cleaning, categorization, class-based design

### 2. Well.ca Price Update
- **File:** `wellca/wellca_price_update.py`
- **Purpose:** Updates product prices from Well.ca
- **Output:** Database updates
- **Features:** Database integration, price tracking

## 🔧 Utilities

### Proxy Testing
- `utilities/test_proxy_*.py` - Various proxy connection tests
- `utilities/test_correct_ipburger.py` - IPBurger proxy validation

### Examples
- `examples/example_usage.py` - Basic usage examples
- `examples/example_dataframe_usage.py` - DataFrame-specific examples

## 📝 Usage Examples

See the `examples/` directory for detailed usage examples and best practices.

## 🛠️ Requirements

- Python 3.6+
- requests
- beautifulsoup4
- pandas
- sqlalchemy (for database operations)
- playwright (for advanced scraping)

## 🌐 Proxy Configuration

Most scrapers use IPBurger residential proxy:
- **Host:** residential.ipb.cloud
- **Port:** 7777
- **Protocol:** HTTP
- **Authentication:** Username/Password

## 📈 Data Flow

1. **Scrape** → Collect links from target website
2. **Filter** → Keep only relevant internal links
3. **Clean** → Remove tracking parameters and normalize URLs
4. **Analyze** → Categorize and summarize findings
5. **Export** → Save to DataFrame or CSV (optional)

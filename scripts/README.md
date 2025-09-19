# Scripts Organization

This directory contains organized Python scripts for the Well.ca Price Ticker project.

## 📁 Folder Structure

```
scripts/
├── scrapers/           # Web scraping scripts
│   ├── wellca_brand_link_list.py      # Get brand links from Well.ca
│   ├── wellca_links_from_brands.py    # Extract product links from brands
│   └── wellca_price_update.py         # Update product prices and metadata
├── analytics/          # Data analysis scripts
│   └── df_price_30d.py                # 30-day price trend analysis
├── data_processing/    # Data transformation scripts
│   └── shiphero_line_items.py         # ShipHero data processing
├── utilities/          # Utility scripts (empty for now)
└── run_wellca_pipeline.py             # Main pipeline runner
```

## 🚀 Quick Start

### Run Complete Pipeline
```bash
python run_wellca_pipeline.py --all
```

### Run Individual Steps
```bash
# Step 1: Get brand links
python run_wellca_pipeline.py --step brands

# Step 2: Extract product links
python run_wellca_pipeline.py --step products

# Step 3: Update prices
python run_wellca_pipeline.py --step prices

# Step 4: Generate analysis
python run_wellca_pipeline.py --step analysis
```

### Run Individual Scripts
```bash
# Scrapers
python scrapers/wellca_brand_link_list.py
python scrapers/wellca_links_from_brands.py
python scrapers/wellca_price_update.py

# Analytics
python analytics/df_price_30d.py

# Data Processing
python data_processing/shiphero_line_items.py
```

## 📋 Script Descriptions

### Scrapers (`scrapers/`)
- **`wellca_brand_link_list.py`**: Scrapes all brand links from Well.ca's brand index page
- **`wellca_links_from_brands.py`**: Extracts product links from each brand's page
- **`wellca_price_update.py`**: Scrapes product details, prices, and metadata

### Analytics (`analytics/`)
- **`df_price_30d.py`**: Analyzes 30-day price trends and generates statistics

### Data Processing (`data_processing/`)
- **`shiphero_line_items.py`**: Processes ShipHero order line items data

## 🔧 Dependencies

All scripts depend on the modules in the `../src/` directory:
- `mySQL_Upsert_Function.py` - Database operations
- `generate_key.py` - Key generation for deduplication

## 📊 Data Flow

1. **Brand Links** → `product_links` table
2. **Product Links** → `product_links` table (upsert)
3. **Price Update** → `df_ticker` and `fixed_fields` tables
4. **Analysis** → Generates 30-day price trends DataFrame

## ⚙️ Configuration

Database credentials and settings are configured in each script. The scripts use:
- MySQL database: `u488367489_Price_Ticker`
- Tables: `product_links`, `df_ticker`, `fixed_fields`, `duration`

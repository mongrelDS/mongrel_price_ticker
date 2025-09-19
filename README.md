# Mongrel Price Ticker

An automated price tracking system for Well.ca products with secure environment variable management and comprehensive data analysis capabilities.

## 🚀 Features

- **Automated Web Scraping**: Extracts product information from Well.ca
- **Price Analysis**: 30-day price trend analysis and reporting
- **Database Integration**: Secure MySQL database storage with environment variables
- **Security First**: No hardcoded credentials, comprehensive security measures
- **Modular Design**: Well-organized, maintainable codebase

## 📁 Project Structure

```
mongrel_price_ticker/
├── scripts/
│   ├── analytics/          # Price analysis and reporting
│   ├── scrapers/           # Web scraping modules
│   ├── data_processing/    # Data processing and ETL
│   └── security/           # Security check utilities
├── src/                    # Core source code modules
├── data/                   # Data storage directory
└── docs/                   # Documentation
```

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- MySQL database
- Required Python packages (see `requirements.txt`)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/mongrelDS/mongrel_price_ticker.git
   cd mongrel_price_ticker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   # Copy the environment template
   cp .env.example .env
   
   # Edit with your actual credentials
   nano .env
   ```

4. **Set up your database credentials in `.env`:**
   ```bash
   DB_HOST=your_database_host
   DB_NAME=your_database_name
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   DB_PORT=3306
   ```

## 🚀 Usage

### Run Individual Scripts

```bash
# Get brand links
python3 scripts/scrapers/wellca_brand_link_list.py

# Extract product links
python3 scripts/scrapers/wellca_links_from_brands.py

# Update product prices
python3 scripts/scrapers/wellca_price_update.py

# Generate price analysis
python3 scripts/analytics/df_price_30d.py
```

### Run Complete Pipeline

```bash
# Run all steps in sequence
python3 scripts/run_wellca_pipeline.py --all

# Run specific step
python3 scripts/run_wellca_pipeline.py --step prices
```

## 🔒 Security

This project implements comprehensive security measures:

- **Environment Variables**: All credentials stored securely in `.env` files
- **No Hardcoded Passwords**: Zero sensitive data in source code
- **Security Checks**: Automated tools to detect credential leaks
- **Git Protection**: Sensitive files excluded from version control

### Security Check

Run the security check before committing:

```bash
python3 scripts/security/check_passwords.py
```

## 📊 Data Analysis

The system provides comprehensive price analysis:

- **30-day price trends** for all products
- **Price volatility analysis**
- **Historical data tracking**
- **Automated reporting**

## 🛡️ Environment Variables

Required environment variables (see `.env.example`):

```bash
# Database Configuration
DB_HOST=your_database_host
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_PORT=3306

# Optional: Other API Keys
# API_KEY=your_api_key_here
```

## 📋 Requirements

See `requirements.txt` for complete list. Key dependencies:

- `pandas` - Data manipulation
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `sqlalchemy` - Database ORM
- `python-dotenv` - Environment variable management
- `playwright` - Browser automation

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run security checks
5. Submit a pull request

## 📄 License

This project is for internal use. Please contact the maintainer for licensing information.

## 📞 Support

For questions or issues, please contact the development team.

---

**Built with security and maintainability in mind** 🔒
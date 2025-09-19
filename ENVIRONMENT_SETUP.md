# Environment Variables Setup

This document explains how to set up and use environment variables for secure database credential management in the Mongrel Price Ticker project.

## Files Created

- `.env` - Contains your actual database credentials (DO NOT COMMIT)
- `.env.example` - Template file showing required environment variables
- `src/database_config.py` - Database configuration module
- `src/mySQL_Upsert_Function_v2.py` - Updated MySQL functions using environment variables
- `src/example_usage.py` - Example of how to use the new configuration

## Setup Instructions

### 1. Environment Variables

The `.env` file contains your database credentials:
```bash
DB_HOST=srv1978.hstgr.io
DB_NAME=u488367489_Price_Ticker
DB_USER=u488367489_mongrel_data
DB_PASSWORD=taan2#IbizaI
DB_PORT=3306
```

### 2. Security Features

- ✅ `.env` is already in `.gitignore` (won't be committed to version control)
- ✅ Credentials are loaded from environment variables
- ✅ Fallback values provided for backward compatibility
- ✅ Validation ensures required variables are present

### 3. Usage Examples

#### Basic Usage (Updated MySQL Function)
```python
from src.mySQL_Upsert_Function import upsert_df_to_mysql
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

# Your existing code will work with environment variables
db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')
# ... etc
```

#### Advanced Usage (New Database Config Module)
```python
from src.database_config import get_database_engine, get_database_credentials
from src.mySQL_Upsert_Function_v2 import upsert_df_to_mysql, read_mysql_to_df

# Get configured engine
engine = get_database_engine()

# Use with your existing functions
upsert_df_to_mysql(df, engine, 'your_table', 'id')
df = read_mysql_to_df(engine, 'your_table')
```

### 4. Migration Guide

#### Option 1: Keep Current Code (Minimal Changes)
Your existing `mySQL_Upsert_Function.py` has been updated to use environment variables with fallbacks. No other changes needed.

#### Option 2: Use New Configuration Module (Recommended)
1. Replace imports in your scripts:
   ```python
   # Old
   from src.mySQL_Upsert_Function import upsert_df_to_mysql
   
   # New
   from src.mySQL_Upsert_Function_v2 import upsert_df_to_mysql
   from src.database_config import get_database_engine
   ```

2. Update engine creation:
   ```python
   # Old
   connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
   db_engine = create_engine(connection_string, poolclass=NullPool)
   
   # New
   db_engine = get_database_engine()
   ```

### 5. Testing

Run the example to test your setup:
```bash
cd /home/mongreldatalab/mongrel_price_ticker
python src/example_usage.py
```

### 6. Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DB_HOST` | Database host | `srv1978.hstgr.io` | Yes |
| `DB_NAME` | Database name | `u488367489_Price_Ticker` | Yes |
| `DB_USER` | Database username | `u488367489_mongrel_data` | Yes |
| `DB_PASSWORD` | Database password | `taan2#IbizaI` | Yes |
| `DB_PORT` | Database port | `3306` | No |
| `DB_POOL_SIZE` | Connection pool size | `5` | No |
| `DB_MAX_OVERFLOW` | Max pool overflow | `10` | No |

### 7. Security Best Practices

1. **Never commit `.env` files** - They're already in `.gitignore`
2. **Use strong passwords** - Consider rotating your database password
3. **Limit database permissions** - Use least privilege principle
4. **Monitor access** - Keep logs of database connections
5. **Backup credentials securely** - Store in password manager

### 8. Troubleshooting

#### Common Issues

1. **Missing environment variables**: Check `.env` file exists and has correct format
2. **Connection errors**: Verify database credentials and network access
3. **Import errors**: Ensure `python-dotenv` is installed (`pip install python-dotenv`)

#### Debug Mode

Enable SQL query logging by modifying `database_config.py`:
```python
return create_engine(
    connection_string,
    poolclass=poolclass,
    pool_size=self.pool_size,
    max_overflow=self.max_overflow,
    echo=True  # Enable SQL logging
)
```

## Next Steps

1. Test the environment setup with your existing scripts
2. Consider migrating to the new configuration module for better maintainability
3. Set up different `.env` files for different environments (dev, staging, prod)
4. Implement credential rotation schedule

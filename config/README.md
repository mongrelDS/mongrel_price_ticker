# Configuration Directory

This directory contains configuration files and credentials for the Mongrel Price Ticker project.

## Directory Structure

```
config/
├── README.md                    # This file
└── (configuration files go here)

credentials/
├── tactical-elf-452207-m9-1f0520891d95.json  # Google Drive service account
└── (other credential files go here)
```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database Configuration
DB_HOST=srv1978.hstgr.io
DB_NAME=u488367489_Price_Ticker
DB_USER=u488367489_mongrel_data
DB_PASSWORD=your_actual_password_here

# ShipHero Configuration
SHIPHERO_EMAIL=your_shiphero_email@example.com
SHIPHERO_PASSWORD=your_shiphero_password_here

# Google Drive Configuration
GOOGLE_DRIVE_FOLDER_ID=1_VV9n32idhpCu4H017Z_9ZKo80DLaSbn
```

## Security Notes

- Never commit actual credentials to version control
- Keep the `.env` file in `.gitignore`
- Store sensitive files in the `credentials/` directory
- Use environment variables for all sensitive configuration

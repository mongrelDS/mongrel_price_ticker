# New Project

A clean Python project for data processing and automation.

## Project Structure

```
new_project/
├── src/           # Source code
├── tests/         # Test files
├── docs/          # Documentation
├── data/          # Data files
├── scripts/       # Utility scripts
├── requirements.txt
└── README.md
```

## Setup

1. Install dependencies:
```bash
pip3 install -r requirements.txt --break-system-packages
```

2. For Playwright (if needed):
```bash
sudo playwright install-deps
python3 -m playwright install
```

## Usage

Add your main scripts to the `src/` directory and utility scripts to `scripts/`.

## Dependencies

- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **playwright**: Browser automation
- **sqlalchemy**: Database ORM
- **requests**: HTTP library

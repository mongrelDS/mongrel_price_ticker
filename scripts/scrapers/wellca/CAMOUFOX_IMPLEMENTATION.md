# Camoufox Implementation for Well.ca Scraper

## Overview
This document outlines the implementation of Camoufox (stealth browser) in the Well.ca price update scraper to avoid detection and blocking.

## Changes Made

### 1. Dependencies Updated
- Added `camoufox>=0.1.0` to both `requirements.txt` files
- Updated script documentation to reflect Camoufox usage

### 2. Import Changes
- Replaced `from playwright.async_api import async_playwright` with `from camoufox.async_api import async_playwright`
- Added `import random` for human-like behavior simulation

### 3. Browser Launch Updates
- Changed `p.firefox.launch()` to `p.camoufox.launch()` in both scraping functions
- Enhanced browser options with extensive anti-detection arguments:
  - `--no-sandbox`
  - `--disable-blink-features=AutomationControlled`
  - `--disable-dev-shm-usage`
  - `--disable-gpu`
  - `--disable-web-security`
  - `--disable-features=VizDisplayCompositor`
  - `--disable-extensions`
  - `--disable-plugins`
  - `--disable-images`
  - `--disable-javascript`
  - `--disable-default-apps`
  - `--disable-sync`
  - `--disable-translate`
  - `--hide-scrollbars`
  - `--mute-audio`
  - `--no-first-run`
  - `--no-default-browser-check`
  - `--disable-background-timer-throttling`
  - `--disable-backgrounding-occluded-windows`
  - `--disable-renderer-backgrounding`

### 4. Enhanced Stealth Features
- **Comprehensive HTTP Headers**: Added realistic browser headers including Accept, Accept-Language, DNT, etc.
- **Viewport Simulation**: Set realistic viewport size (1920x1080)
- **Navigator Property Override**: JavaScript injection to hide automation signatures:
  - Hide `navigator.webdriver`
  - Spoof `navigator.plugins`
  - Set realistic `navigator.languages`
  - Add `window.chrome` object
- **Human-like Behavior**: Added random delays:
  - 1-3 seconds after page load
  - 2-5 seconds between batches

### 5. Logging Updates
- Updated log messages to reflect Camoufox usage
- Enhanced script description with stealth capabilities

## Installation

1. Install Camoufox:
```bash
pip install camoufox
```

2. Install other dependencies:
```bash
pip install -r requirements.txt
```

## Testing

Run the test script to verify Camoufox is working:
```bash
python test_camoufox.py
```

## Usage

The script can be run exactly like the original:
```bash
python wellca_price_update_on_camoufox.py
```

## Key Benefits

1. **Anti-Detection**: Camoufox is specifically designed to evade bot detection
2. **Fingerprint Spoofing**: Comprehensive browser fingerprint manipulation
3. **Stealth Browsing**: Enhanced privacy and anonymity features
4. **Human-like Behavior**: Random delays and realistic browser patterns
5. **Compatibility**: Drop-in replacement for Playwright Firefox

## Configuration

The script uses the same environment variables and configuration as the original:
- `SCRAPE_MAX_CONCURRENCY`: Maximum concurrent requests (default: 8)
- `SCRAPE_BATCH_SIZE`: Batch size for processing (default: 50)
- Proxy configuration through `proxy_config` module

## Monitoring

The script includes enhanced logging to track:
- Camoufox browser usage
- Stealth features activation
- Human-like behavior simulation
- Proxy usage statistics

## Troubleshooting

If you encounter issues:
1. Ensure Camoufox is properly installed
2. Check that all dependencies are up to date
3. Verify proxy configuration if using proxies
4. Monitor logs for any detection or blocking issues

## Performance Impact

- Slightly slower than standard Playwright due to stealth features
- Random delays add 1-5 seconds per batch
- Memory usage may be slightly higher due to enhanced fingerprinting
- Overall reliability should be significantly improved due to reduced blocking

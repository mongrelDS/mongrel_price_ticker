#!/usr/bin/env python3
"""
Simple test script to debug the Healthy Planet scraper
"""
import asyncio
from playwright.async_api import async_playwright
import sys
import os

# Add src folder to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir)
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from proxy_config import get_proxy_for_playwright

async def test_scraper():
    """Test the scraper with a single URL"""
    test_url = "https://www.healthyplanetcanada.com/attitude-eye-cream-phyto-glow-8-5g.html"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Must be headless on server
        page = await browser.new_page()
        
        # Set up proxy if available
        try:
            proxy_config = get_proxy_for_playwright()
            if proxy_config:
                await page.context.set_extra_http_headers(proxy_config)
                print("Proxy configuration applied")
        except Exception as e:
            print(f"Proxy setup failed: {e}")
        
        try:
            print(f"Navigating to: {test_url}")
            await page.goto(test_url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Test title scraping
            title_element = await page.query_selector('h1.page-title')
            if title_element:
                title = await title_element.text_content()
                print(f"Title found: {title}")
            else:
                print("Title element not found")
                
            # Test brand scraping
            brand_element = await page.query_selector('span.brand-name a')
            if brand_element:
                brand = await brand_element.text_content()
                print(f"Brand found: {brand}")
            else:
                print("Brand element not found")
                
            # Test price scraping
            price_element = await page.query_selector('span.price')
            if price_element:
                price = await price_element.text_content()
                print(f"Price found: {price}")
            else:
                print("Price element not found")
                
            # Test SKU scraping
            sku_element = await page.query_selector('div.product.attribute.sku .value')
            if sku_element:
                sku = await sku_element.text_content()
                print(f"SKU found: {sku}")
            else:
                print("SKU element not found")
                
            # Test stock status
            add_to_cart_button = await page.query_selector('button#product-addtocart-button')
            if add_to_cart_button:
                is_disabled = await add_to_cart_button.is_disabled()
                stock_status = 'In Stock' if not is_disabled else 'Out of Stock'
                print(f"Stock status: {stock_status}")
            else:
                print("Add to cart button not found")
                
        except Exception as e:
            print(f"Error during scraping: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scraper())

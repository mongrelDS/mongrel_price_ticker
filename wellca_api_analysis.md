# Well.ca API Analysis Results

## Database Query Results
- **Total links in brand_link_list table**: 8,720
- **Well.ca links found**: 5,811 (66.6% of all links)
- **Sample size tested**: 20 links

## Working API Endpoints Discovered

### 1. Main Search API (Primary)
- **URL**: `https://well.ca/api/search/products`
- **Method**: GET
- **Parameters**: `query` (search term)
- **Status**: ✅ Working
- **Response**: Array of product objects

### 2. Products API (All Products)
- **URL**: `https://well.ca/api/products`
- **Method**: GET
- **Parameters**: None (returns all products)
- **Status**: ✅ Working
- **Response**: Array of 32 product objects

### 3. Brands API
- **URL**: `https://well.ca/api/brands`
- **Method**: GET
- **Parameters**: None
- **Status**: ✅ Working
- **Response**: Array of brand objects

### 4. Categories API
- **URL**: `https://well.ca/api/categories`
- **Method**: GET
- **Parameters**: None
- **Status**: ✅ Working
- **Response**: Array of category objects

### 5. Brand-Specific Products API
- **URL**: `https://well.ca/api/products?brand={brand_name}`
- **Method**: GET
- **Parameters**: `brand` (brand name from URL)
- **Status**: ✅ Working
- **Response**: Array of product objects for specific brand

## JSON Field Structure Analysis

### Product Object Fields (Complete List)
Based on the API response, each product contains the following fields:

#### Core Product Information
- `products_id` (str): Unique product identifier
- `products_name` (str): Product name/title
- `products_code` (str|null): Product SKU/code
- `brands_id` (str): Brand identifier
- `master_categories_id` (str): Category identifier

#### Pricing Information
- `products_price` (str): Base price (decimal as string)
- `products_price_formatted` (str): Formatted price with currency
- `products_sale_price` (str): Sale price (decimal as string)
- `products_sale_price_formatted` (str): Formatted sale price
- `products_discount_formatted` (str): Discount information
- `currency_code` (str): Currency (e.g., "CAD")

#### Product Details
- `products_quantity_text` (str): Quantity description (e.g., "15 mL")
- `products_dose_text` (str): Dosage information
- `products_subtitle` (str): Product subtitle
- `products_chemicalname` (str): Chemical name
- `hybris_features` (str): HTML formatted features list
- `hybris_ingredients` (str): Ingredients information
- `nutrition_information` (str): Nutrition facts

#### Images
- `products_image` (str): Main product image URL (32x32)
- `products_image_thumbnail` (str): Thumbnail image URL (100x80)
- `products_image_full` (str): Full-size image URL (806x806)
- `products_image_id` (str): Image filename
- `secondary_images_thumbnail` (list): Array of secondary thumbnail URLs
- `secondary_images_full` (list): Array of secondary full-size URLs
- `secondary_images_large` (list): Array of secondary large URLs
- `secondary_images` (list): Array of secondary image URLs

#### Inventory & Availability
- `products_quantity_order_stock` (int): Available stock quantity
- `products_warehouse_stock` (int): Warehouse stock quantity
- `availability` (dict): Store and fulfillment center availability
- `can_checkout` (bool): Whether product can be purchased

#### Physical Properties
- `products_weight_kg` (str): Weight in kilograms
- `products_height` (str|null): Product height
- `products_width` (str|null): Product width
- `products_length` (str|null): Product length
- `products_upc` (str): UPC code

#### Status & Flags
- `products_status` (str): Product status (1 = active)
- `exclude_from_ppt` (str): Exclude from price tracking
- `is_bundle` (str): Is product a bundle
- `is_gift_box` (str): Is product a gift box
- `products_last_modified` (str): Last modification timestamp

#### Additional Data
- `field_data` (str|null): Additional field data
- `product_level_max_qty` (str): Maximum quantity per order
- `repeat_buying_discount` (str): Repeat purchase discount
- `products_tax_class_id` (str): Tax class identifier
- `percentage` (str): Discount percentage
- `products_average_rating` (int): Average customer rating
- `price_by_store` (list): Store-specific pricing
- `swatches` (list): Color/style swatches
- `content_box` (list): Content box information
- `associated_products` (list): Related products
- `products_attribute_info` (dict|null): Product attributes
- `promotions` (dict|null): Promotional information
- `flags` (dict|null): Product flags
- `bundles` (dict|null): Bundle information
- `selectable_bundles` (dict|null): Selectable bundle options

### Brand Object Fields
- `title` (str): Brand name
- `id` (str): Brand identifier
- `image` (str): Brand logo URL
- `redirect` (str): Redirect URL
- `canonical` (str): Canonical URL
- `product_count` (int): Number of products for this brand

### Category Object Fields
- `title` (str): Category name
- `description` (str): Category description
- `id` (str): Category identifier
- `parent_id` (str): Parent category ID
- `storefront_id` (str): Storefront identifier
- `override_link` (str): Override link
- `product_count` (int): Number of products in category
- `image` (str): Category image URL
- `image_hash` (str): Image hash
- `image_large` (str): Large image URL
- `image_large_hash` (str): Large image hash
- `status` (str): Category status
- `hidden` (bool): Is category hidden
- `sort_order` (int): Sort order
- `leaf_node` (bool): Is leaf category
- `redirect` (str): Redirect URL
- `canonical` (str): Canonical URL
- `rfk_hidden` (bool): RFK hidden flag
- `exclude_hybris_export` (bool): Exclude from Hybris export
- `exclude_hybris_description` (bool): Exclude Hybris description
- `subcategories` (list): Array of subcategory objects

## Recommendations for wellca_json_method.py

### Current Implementation Analysis
The current `wellca_json_method.py` is using the search API correctly but could be enhanced with:

1. **Additional API Endpoints**: Use the products API for comprehensive data collection
2. **Brand-Specific Scraping**: Use the brand-specific API for targeted scraping
3. **Enhanced Field Mapping**: Map more fields from the rich JSON response
4. **Error Handling**: Better handling of API rate limits and errors
5. **Pagination**: Implement pagination for large result sets

### Key Fields for Price Tracking
The most relevant fields for price tracking are:
- `products_id`: Unique identifier
- `products_name`: Product name
- `brands_id`: Brand identifier
- `products_price`: Current price
- `products_sale_price`: Sale price
- `products_price_formatted`: Formatted price
- `products_last_modified`: Last update timestamp
- `products_quantity_order_stock`: Stock availability
- `products_upc`: UPC for product matching

### Next Steps
1. Update the Pydantic model to include more fields
2. Implement multiple API endpoint strategies
3. Add brand-specific scraping capability
4. Enhance error handling and retry logic
5. Add pagination support for large datasets

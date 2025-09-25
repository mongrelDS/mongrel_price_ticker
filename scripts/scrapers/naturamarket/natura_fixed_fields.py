import re
import argparse
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from src.get_domain import get_domain
from src.generate_key import generate_key
from src.function_extract_volume import extract_volume
from src.price_to_float import price_to_float


DOMAIN = "naturamarket.ca"


class Product(BaseModel):
    product_id: int
    name: str
    brand_name: Optional[str] = None
    sku: Optional[str] = None
    price: float
    product_url: str
    stock_status: Optional[str] = None
    imgurl: Optional[str] = None
    weight: Optional[float] = None
    categories: Optional[List[str]] = None
    barcode: Optional[str] = None


def build_brand_mapping(aggregations: Optional[List[dict]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not aggregations:
        return mapping
    for agg in aggregations:
        if agg.get("attribute_code") == "brand":
            for opt in agg.get("options", []) or []:
                value = str(opt.get("value")) if opt.get("value") is not None else None
                label = opt.get("label")
                if value and label:
                    mapping[value] = label
            break
    return mapping


def build_search_terms_from_db(sample_fraction_divider: int = 20) -> List[str]:
    db_engine = get_database_engine()
    df_names = read_mysql_to_df(engine=db_engine, table_name='natura_sku_summary')
    # Handle None or empty upfront
    if df_names is None or df_names.empty:
        print("[bold yellow]⚠️ No names found in natura_sku_summary; falling back to defaults[/bold yellow]")
        return ["vitamin", "supplement", "health"]

    # KEEP ROWS WHERE price is > 0
    df_names = df_names[df_names['price'] > 0]
    # select rows where link is null or brand is null
    df_names = df_names[df_names['link'].isnull() | df_names['brand'].isnull()]
    if df_names.empty:
        print("[bold yellow]⚠️ No names after filters; using defaults[/bold yellow]")
        return ["vitamin", "supplement", "health"]

    # # Sample a subset
    # try:
    #     sample_size = max(1, len(df_names) // sample_fraction_divider)
    #     df_names = df_names.sample(sample_size, random_state=42)
    # except Exception:
    #     pass

    # Ensure only 'name' column is used
    if 'name' not in df_names.columns:
        print("[bold yellow]⚠️ 'name' column not found; using defaults[/bold yellow]")
        return ["vitamin", "supplement", "health"]
    df_names = df_names[['name']].dropna()

    # Transform names to search terms
    def to_search_term(name: str) -> str:
        words = str(name).split()[:5]
        search_term = " ".join(words)
        # Keep alphanumeric and plus; remove other chars
        search_term = re.sub(r'[^a-zA-Z0-9+ ]+', '', search_term)
        search_term = search_term.lower().strip()
        return search_term

    terms = df_names['name'].map(to_search_term)
    terms = terms[terms.str.len() > 0].drop_duplicates()
    return terms.tolist()


def create_df_ticker(products: List[Product]) -> pd.DataFrame:
    data = []
    today_str = datetime.now().strftime('%Y-%m-%d')
    for p in products:
        tag = 'in stock' if (p.stock_status or '').upper() == 'IN_STOCK' else 'add to cart'
        data.append({
            'sku': p.sku or str(p.product_id),
            'link': p.product_url,
            'price': p.price,
            'tag': tag,
            'date': today_str,
        })
    df_ticker = pd.DataFrame(data)
    if df_ticker.empty:
        return df_ticker
    df_ticker = get_domain(df_ticker, link_col='link')
    df_ticker = generate_key(df_ticker, deduplication_columns=['link', 'date'], key_col="key")
    return df_ticker


def create_df_fixed_fields(products: List[Product]) -> pd.DataFrame:
    rows = []
    for p in products:
        breadcrumbs = ' > '.join(sorted(set(p.categories or []), key=lambda x: (p.categories or []).index(x))) if p.categories else None
        rows.append({
            'link': p.product_url,
            'imgurl': p.imgurl,
            'title': p.name,
            'brand': p.brand_name,
            'sku': p.sku or str(p.product_id),
            'barcode': p.barcode,
            # Use title text for volume extraction per requirement
            'weight_kg': p.name,
            'breadcrumbs': breadcrumbs,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = extract_volume(df, vol_col="weight_kg", result_col="vol")
    # Drop helper column after extraction
    if 'weight_kg' in df.columns:
        df = df.drop(columns=['weight_kg'])
    df = df.rename(columns={'breadcrumbs': 'keywords'})
    return df


def main():
    parser = argparse.ArgumentParser(description="Naturamarket scraper")
    parser.add_argument("--max-queries", type=int, default=None, help="Limit number of search queries to process")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to the database or duration table")
    args = parser.parse_args()

    start_ts = time.time()
    print("[bold cyan]🚀 Starting scraper for naturamarket.ca...[/bold cyan]")

    # Session
    session = requests.Session(
        impersonate="chrome110",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    graphql_url = "https://naturamarket.ca/graphql"

    # Build search terms from DB
    search_queries = build_search_terms_from_db(sample_fraction_divider=20)
    if args.max_queries is not None and args.max_queries >= 0:
        search_queries = search_queries[:args.max_queries]
    print(f"🔎 Using {len(search_queries)} search terms from DB sample")

    # GraphQL query with extra fields (Magento 2 schema)
    graphql_query = (
        """
        query Products($search: String, $pageSize: Int!, $currentPage: Int!) {
          products(search: $search, pageSize: $pageSize, currentPage: $currentPage) {
            items {
              id
              name
              sku
              url_key
              url_suffix
              stock_status
              price_range { minimum_price { final_price { value currency } } }
              media_gallery { url }
              categories { name }
              ... on PhysicalProductInterface { weight }
            }
            aggregations { attribute_code options { label value } }
          }
        }
        """
        .strip()
    )

    products: List[Product] = []
    seen_ids: set[int] = set()

    for idx, query in enumerate(search_queries, start=1):
        variables = {"search": query, "pageSize": 50, "currentPage": 1}
        try:
            resp = session.post(graphql_url, json={"query": graphql_query, "variables": variables})
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("errors"):
                continue
            prod_data = payload.get("data", {}).get("products", {})
            # Brand mapping may not be available or needed; we'll prefer JSON-LD brand from PDP
            for item in prod_data.get("items", []) or []:
                try:
                    pid = int(item.get('id', 0))
                    if not pid or pid in seen_ids:
                        continue
                    url_key = item.get('url_key') or ''
                    url_suffix = item.get('url_suffix') or ''
                    link = f"https://naturamarket.ca/{url_key}{url_suffix}" if url_key else ''
                    price_obj = ((item.get('price_range') or {}).get('minimum_price', {}) or {}).get('final_price', {})
                    price = float(price_obj.get('value', 0)) if price_obj else 0.0
                    brand_name = None
                    imgurl = (item.get('media_gallery') or [{}])[0].get('url') if item.get('media_gallery') else None
                    weight = item.get('weight')
                    categories = [c.get('name') for c in (item.get('categories') or []) if c.get('name')]

                    # Fetch PDP JSON-LD to try to get barcode (gtin) and brand
                    barcode = None
                    if link:
                        try:
                            html_resp = session.get(link)
                            if html_resp.status_code == 200:
                                text = html_resp.text
                                # Find JSON-LD Product block(s)
                                for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', text, flags=re.DOTALL|re.IGNORECASE):
                                    try:
                                        data = json.loads(m.group(1))
                                    except Exception:
                                        continue
                                    # Some pages embed arrays of JSON-LD
                                    blocks = data if isinstance(data, list) else [data]
                                    for block in blocks:
                                        if isinstance(block, dict) and str(block.get("@type", "")).lower() == "product":
                                            # Brand can be a string or an object with name
                                            brand_field = block.get("brand")
                                            if brand_field and not brand_name:
                                                if isinstance(brand_field, dict):
                                                    brand_name = brand_field.get("name") or brand_name
                                                elif isinstance(brand_field, str):
                                                    brand_name = brand_field
                                            # Check common gtin keys
                                            for key in ["gtin", "gtin8", "gtin12", "gtin13", "gtin14", "upc", "ean", "barcode"]:
                                                val = block.get(key)
                                                if val:
                                                    barcode = str(val)
                                                    break
                                            if not barcode:
                                                # Some sites put identifier under sku or additionalProperty
                                                add_props = block.get("additionalProperty") or block.get("additionalProperties")
                                                if isinstance(add_props, list):
                                                    for prop in add_props:
                                                        name = (prop or {}).get("name", "").lower()
                                                        if name in {"gtin", "upc", "barcode", "ean"}:
                                                            barcode = str((prop or {}).get("value"))
                                                            break
                                            break
                                    if barcode:
                                        break
                        except Exception:
                            pass

                    product = Product(
                        product_id=pid,
                        name=item.get('name', ''),
                        brand_name=brand_name,
                        sku=item.get('sku') or str(pid),
                        price=price,
                        product_url=link,
                        stock_status=item.get('stock_status'),
                        imgurl=imgurl,
                        weight=weight,
                        categories=categories,
                        barcode=barcode,
                    )
                    products.append(product)
                    seen_ids.add(pid)
                except ValidationError:
                    continue
                except Exception as _e:
                    continue
            time.sleep(0.5)
        except Exception as _e:
            continue
        if idx % 20 == 0:
            print(f"[bold blue]Progress:[/bold blue] processed {idx}/{len(search_queries)} queries; products so far: {len(products)}")

    # Build DataFrames
    df_ticker = create_df_ticker(products)
    # Normalize ticker price values using shared utility
    try:
        df_ticker = price_to_float(df_ticker, price_col="price", currency_marker="$")
    except Exception:
        pass
    df_fixed_fields = create_df_fixed_fields(products)

    # Build natura_sku_summary DataFrame from source table + current scraped fields
    df_natura_sku_summary = pd.DataFrame()
    try:
        engine_for_names = get_database_engine()
        df_names = read_mysql_to_df(engine=engine_for_names, table_name='natura_sku_summary')
    except Exception:
        df_names = None

    required_cols = [
        'sku', 'name', 'l30d_sales', 'cost', 'price', 'margin', 'wtd_avg_margin',
        'barcode', 'brand', 'link', 'imgurl'
    ]

    if df_names is None or df_names.empty:
        # Create empty frame with expected columns plus 'vol'
        df_natura_sku_summary = pd.DataFrame(columns=required_cols + ['vol'])
    else:
        # Ensure required columns exist in df_names
        for c in required_cols:
            if c not in df_names.columns:
                df_names[c] = pd.NA
        # Keep rows with sku
        df_names = df_names.dropna(subset=['sku'])

        # Extract volume from 'name' using shared utility
        try:
            df_names = extract_volume(df_names, vol_col='name', result_col='vol')
        except Exception:
            # If extraction fails, ensure 'vol' exists
            if 'vol' not in df_names.columns:
                df_names['vol'] = pd.NA

        # Map scraped enrichment fields from current run (by sku)
        scraped_fields = df_fixed_fields[['sku', 'barcode', 'brand', 'link', 'imgurl']].copy()
        scraped_fields = scraped_fields.dropna(subset=['sku']).drop_duplicates(subset=['sku'], keep='first')

        merged = df_names.merge(scraped_fields, on='sku', how='left', suffixes=('', '_scraped'))

        # Prefer scraped values when present; otherwise keep existing
        for col in ['barcode', 'brand', 'link', 'imgurl']:
            merged[col] = merged[f'{col}_scraped'].combine_first(merged[col])

        # Final selection and ordering
        df_natura_sku_summary = merged[
            ['sku', 'name', 'l30d_sales', 'cost', 'price', 'margin', 'wtd_avg_margin',
             'barcode', 'brand', 'link', 'imgurl', 'vol']
        ].copy()

    print(f"📊 df_ticker: {len(df_ticker)} rows | df_fixed_fields: {len(df_fixed_fields)} rows")
    if args.dry_run:
        try:
            print("\nSample df_ticker (5 rows):")
            print(df_ticker.head(5).to_string(index=False))
        except Exception:
            pass
        try:
            print("\nSample df_fixed_fields (5 rows):")
            print(df_fixed_fields.head(5).to_string(index=False))
        except Exception:
            pass
        try:
            print("\nSample df_natura_sku_summary (5 rows):")
            print(df_natura_sku_summary.head(5).to_string(index=False))
        except Exception:
            pass

    # Upserts
    if args.dry_run:
        print("[bold yellow]Dry run enabled: skipping database upserts[/bold yellow]")
        db_engine = None
    else:
        db_engine = get_database_engine()
        if not df_ticker.empty:
            upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
        if not df_fixed_fields.empty:
            upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')
        if not df_natura_sku_summary.empty:
            upsert_df_to_mysql(df=df_natura_sku_summary, engine=db_engine, target_table='natura_sku_summary', key_col='sku')

    # Duration metrics
    end_ts = time.time()
    duration_in_minutes = (end_ts - start_ts) / 60.0
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes],
        'date': [datetime.now()],
        'results': [len(df_ticker)],
        'domain': [DOMAIN],
        'type': ['item_update'],
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
    if not args.dry_run:
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
    else:
        print("[bold yellow]Dry run enabled: skipping duration upsert[/bold yellow]")

    print("[bold green]✅ Completed Naturamarket item update[/bold green]")


if __name__ == "__main__":
    main()
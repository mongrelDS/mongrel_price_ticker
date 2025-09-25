import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from curl_cffi import requests
from pydantic import BaseModel, ValidationError
from rich import print

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df, upsert_df_to_mysql
from src.get_domain import get_domain
from src.generate_key import generate_key
from src.function_extract_volume import extract_volume


DOMAIN = "naturesante.ca"


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


def get_brand_links_from_db(sample_fraction_divider: int = 20) -> List[str]:
    """Read brand links from MySQL, filter for naturesante.ca, and sample rows.

    Sampling size follows len(df_names)//sample_fraction_divider if available
    from table 'natura_product_table'; otherwise falls back to len(df_links)//divider.
    """
    db_engine = get_database_engine()
    df_links = read_mysql_to_df(engine=db_engine, table_name='brand_link_list')
    if df_links is None or df_links.empty:
        print("[bold yellow]⚠️ No links found in brand_link_list[/bold yellow]")
        return []

    # Ensure 'brand_url' column exists
    if 'brand_url' not in df_links.columns:
        print("[bold yellow]⚠️ 'brand_url' column not found in brand_link_list[/bold yellow]")
        return []

    # Filter to naturesante.ca only
    df_links = df_links[df_links['brand_url'].astype(str).str.contains(DOMAIN, case=False, na=False)]
    if df_links.empty:
        print("[bold yellow]⚠️ No naturesante.ca links found in brand_link_list[/bold yellow]")
        return []

    # Compute sample size using len(df_names)//divider if available
    sample_size: int
    try:
        df_names = read_mysql_to_df(engine=db_engine, table_name='natura_product_table')
        base_len = len(df_names) if df_names is not None else len(df_links)
        sample_size = max(1, min(len(df_links), base_len // sample_fraction_divider))
    except Exception:
        sample_size = max(1, min(len(df_links), len(df_links) // sample_fraction_divider))

    try:
        df_links = df_links.sample(sample_size, random_state=42)
    except Exception:
        # Fallback to head if sample fails
        df_links = df_links.head(sample_size)

    return df_links['brand_url'].astype(str).dropna().unique().tolist()


def probe_json_endpoints(session: requests.Session, url: str) -> Tuple[bool, List[str]]:
    """Check if JSON endpoints are available for a given URL.

    Returns (has_json, available_endpoints)
    """
    candidates: List[str] = []
    clean_url = url.rstrip('/')

    # Generic Shopify JSON endpoints to try
    candidates.append(f"{clean_url}.json")
    candidates.append(f"{clean_url}?view=json")
    if "/collections/" in clean_url:
        candidates.append(f"{clean_url}/products.json?limit=5")

    available: List[str] = []
    for endpoint in candidates:
        try:
            r = session.get(endpoint, headers={"Accept": "application/json"}, timeout=20)
            if r.status_code == 200:
                # Validate that body looks like JSON
                try:
                    _ = r.json()
                    available.append(endpoint)
                except Exception:
                    # Some endpoints may respond 200 with non-JSON; ignore
                    pass
        except Exception:
            continue

    return (len(available) > 0, available)


def is_collection_link(url: str) -> bool:
    try:
        url_l = (url or "").lower()
        return "/collections/" in url_l and "/collections/vendors" not in url_l
    except Exception:
        return False


def get_collection_handle_from_link(url: str) -> Optional[str]:
    try:
        # Expected formats:
        # https://naturesante.ca/collections/<handle>
        # https://naturesante.ca/collections/<handle>?param=...
        if not is_collection_link(url):
            return None
        path = url.split("/collections/")[-1]
        path = path.split("?")[0].strip("/")
        return path or None
    except Exception:
        return None


def fetch_collection_products(session: requests.Session, base_url: str, collection_handle: str, limit: int = 100) -> List[dict]:
    """Fetch a small set of products from a Shopify collection products.json endpoint."""
    try:
        url = f"{base_url}/collections/{collection_handle}/products.json"
        params = {"limit": str(max(1, min(limit, 250)))}
        r = session.get(url, params=params, headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        data = r.json()
        prods = (data or {}).get("products") or []
        return prods if isinstance(prods, list) else []
    except Exception:
        return []


def fetch_product_js(session: requests.Session, base_url: str, handle: str) -> Optional[dict]:
    try:
        r = session.get(f"{base_url}/products/{handle}.js", headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def build_search_terms_from_db(sample_fraction_divider: int = 20) -> List[str]:
    db_engine = get_database_engine()
    df_names = read_mysql_to_df(engine=db_engine, table_name='natura_product_table')
    if df_names is None or df_names.empty:
        print("[bold yellow]⚠️ No names found in natura_product_table; falling back to defaults[/bold yellow]")
        return ["vitamin", "supplement", "health"]

    # Sample a subset
    try:
        sample_size = max(1, len(df_names) // sample_fraction_divider)
        df_names = df_names.sample(sample_size, random_state=42)
    except Exception:
        pass

    # Ensure only 'name' column is used
    if 'name' not in df_names.columns:
        print("[bold yellow]⚠️ 'name' column not found; using defaults[/bold yellow]")
        return ["vitamin", "supplement", "health"]
    df_names = df_names[['name']].dropna()

    # Transform names to search terms
    def to_search_term(name: str) -> str:
        words = str(name).split()[:3]
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
        tag = 'in stock' if (p.stock_status or '').upper() == 'IN_STOCK' else 'out of stock'
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
    start_ts = time.time()
    print("[bold cyan]🚀 Starting naturesante.ca item update from collection JSON...[/bold cyan]")

    # Session
    session = requests.Session(
        impersonate="chrome110",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    base_url = "https://naturesante.ca"

    # Helper: extract breadcrumbs from PDP HTML via JSON-LD BreadcrumbList
    def extract_breadcrumbs_from_html(html: str) -> List[str]:
        try:
            # Find all JSON-LD scripts
            scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
            def try_objects(obj) -> Optional[List[str]]:
                try:
                    if isinstance(obj, dict):
                        # Handle @graph wrapper
                        if "@graph" in obj and isinstance(obj["@graph"], list):
                            for node in obj["@graph"]:
                                names = try_objects(node)
                                if names:
                                    return names
                        if obj.get("@type") == "BreadcrumbList" and isinstance(obj.get("itemListElement"), list):
                            names: List[str] = []
                            for el in obj["itemListElement"]:
                                if isinstance(el, dict):
                                    # Schema variations
                                    if isinstance(el.get("item"), dict) and el["item"].get("name"):
                                        names.append(str(el["item"]["name"]).strip())
                                    elif el.get("name"):
                                        names.append(str(el["name"]).strip())
                            # Clean breadcrumbs (drop Home, empties)
                            names = [n for n in names if n and n.lower() != "home"]
                            return names or None
                    elif isinstance(obj, list):
                        for node in obj:
                            names = try_objects(node)
                            if names:
                                return names
                except Exception:
                    return None
                return None

            for s in scripts:
                try:
                    data = json.loads(s.strip())
                except Exception:
                    # Some themes include multiple JSON objects concatenated; try to salvage
                    # Split by closing brace and attempt incremental loads
                    candidates = re.findall(r'\{[\s\S]*?\}', s)
                    names: Optional[List[str]] = None
                    for cand in candidates:
                        try:
                            obj = json.loads(cand)
                            names = try_objects(obj)
                            if names:
                                break
                        except Exception:
                            continue
                    if names:
                        return names
                    continue
                names = try_objects(data)
                if names:
                    return names
        except Exception:
            return []
        return []

    # Read brand links from DB and sample
    brand_links = get_brand_links_from_db(sample_fraction_divider=20)
    print(f"🔎 Using {len(brand_links)} sampled brand links from DB")

    # Collect products from collections
    products: List[Product] = []
    seen_skus: set[str] = set()

    for link in brand_links:
        if not is_collection_link(link):
            continue
        handle = get_collection_handle_from_link(link)
        if not handle:
            continue
        prod_summaries = fetch_collection_products(session, base_url, handle, limit=50)
        for item in prod_summaries:
            try:
                title = item.get('title', '')
                vendor = item.get('vendor')
                handle_p = item.get('handle') or ''
                product_url = f"{base_url}/products/{handle_p}" if handle_p else ''
                images = item.get('images') or []
                imgurl = (images[0] or {}).get('src') if images and isinstance(images[0], dict) else None
                tags = item.get('tags')

                # Enrich from product.js to get reliable variant data
                pjs = fetch_product_js(session, base_url, handle_p) if handle_p else None
                variants = (pjs or {}).get('variants') if isinstance(pjs, dict) else None
                if not variants:
                    variants = item.get('variants') or []

                # Attempt barcode via product.js first
                page_barcode = None
                if isinstance(variants, list) and variants:
                    for v in variants:
                        if not isinstance(v, dict):
                            continue
                        candidate = v.get('barcode') or v.get('gtin') or v.get('ean') or v.get('upc')
                        if candidate:
                            page_barcode = str(candidate)
                            break

                for v in variants or []:
                    try:
                        if not isinstance(v, dict):
                            continue
                        sku = v.get('sku') or None
                        if not sku:
                            continue
                        if sku in seen_skus:
                            continue
                        seen_skus.add(sku)

                        # Price: product.js returns cents (int); products.json returns str dollars
                        raw_price = v.get('price')
                        price: float
                        if isinstance(raw_price, (int, float)):
                            # Assume cents
                            price = float(raw_price) / 100.0
                        else:
                            try:
                                price = float(raw_price)
                            except Exception:
                                price = 0.0

                        available = bool(v.get('available') or v.get('in_stock'))
                        barcode = v.get('barcode') or page_barcode

                        product = Product(
                            product_id=int(item.get('id', 0)) if item.get('id') else 0,
                            name=title,
                            brand_name=vendor,
                            sku=sku,
                            price=price,
                            product_url=product_url,
                            stock_status="IN_STOCK" if available else "OUT_OF_STOCK",
                            imgurl=imgurl,
                            weight=None,
                            categories=tags if isinstance(tags, list) else [t.strip() for t in str(tags).split(',') if t.strip()],
                            barcode=str(barcode) if barcode else None,
                        )
                        products.append(product)
                    except ValidationError:
                        continue
                    except Exception:
                        continue
            except Exception:
                continue
        time.sleep(0.2)

    # Build DataFrames
    df_ticker = create_df_ticker(products)
    df_fixed_fields = create_df_fixed_fields(products)

    print(f"📊 df_ticker: {len(df_ticker)} rows | df_fixed_fields: {len(df_fixed_fields)} rows")

    # Upserts
    db_engine = get_database_engine()
    if not df_ticker.empty:
        upsert_df_to_mysql(df=df_ticker, engine=db_engine, target_table='df_ticker', key_col='key')
    if not df_fixed_fields.empty:
        upsert_df_to_mysql(df=df_fixed_fields, engine=db_engine, target_table='fixed_fields', key_col='link')

    # Duration metrics
    end_ts = time.time()
    duration_in_minutes = (end_ts - start_ts) / 60.0
    df_duration = pd.DataFrame({
        'duration_min': [duration_in_minutes],
        'date': [datetime.now()],
        'results': [len(df_ticker)],
        'domain': [DOMAIN],
        'type': ['item_crawl'],
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
    db_engine = get_database_engine()
    upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')

    print("[bold green]✅ Completed naturesante.ca item update[/bold green]")


if __name__ == "__main__":
    main()


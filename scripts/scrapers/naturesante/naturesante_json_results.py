import re
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
    print("[bold cyan]🚀 Starting scraper for naturesante.ca (Shopify)...[/bold cyan]")

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

    # Build search terms from DB
    search_queries = build_search_terms_from_db(sample_fraction_divider=20)
    print(f"🔎 Using {len(search_queries)} search terms from DB sample")

    products: List[Product] = []
    seen_skus: set[str] = set()

    # Helper: get product handles from Shopify suggest
    def search_product_handles(term: str) -> List[str]:
        try:
            params = {
                "q": term,
                "resources[type]": "product",
                "resources[limit]": "50",
                "resources[options][unavailable_products]": "last",
                "resources[options][fields]": "title,product_type,variants.title,vendor"
            }
            resp = session.get(f"{base_url}/search/suggest.json", params=params)
            resp.raise_for_status()
            data = resp.json()
            products_res = (((data or {}).get("resources") or {}).get("results") or {}).get("products") or []
            handles: List[str] = []
            for item in products_res:
                handle = (item.get("handle") or item.get("url") or "").strip("/")
                if not handle:
                    continue
                if handle.startswith("products/"):
                    handle = handle.split("products/")[-1]
                handles.append(handle)
            return handles
        except Exception:
            return []

    # Helper: fetch product .js detail
    def fetch_product_detail(handle: str) -> Optional[dict]:
        try:
            resp = session.get(f"{base_url}/products/{handle}.js")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    # Helper: prefer real breadcrumbs from PDP over tags
    def get_breadcrumbs_for_product(url: str) -> List[str]:
        try:
            r = session.get(
                url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                },
            )
            r.raise_for_status()
            names = extract_breadcrumbs_from_html(r.text)
            # Ensure unique while preserving order
            seen: set[str] = set()
            ordered: List[str] = []
            for n in names:
                if n not in seen:
                    seen.add(n)
                    ordered.append(n)
            return ordered
        except Exception:
            return []

    for query in search_queries:
        try:
            handles = search_product_handles(query)
            for handle in handles:
                prod = fetch_product_detail(handle)
                if not prod:
                    continue
                vendor = prod.get("vendor")
                title = prod.get("title", "")
                images = prod.get("images") or []
                imgurl = images[0] if images else None
                tags = prod.get("tags") or []
                product_url = f"{base_url}/products/{handle}"
                product_id = int(prod.get("id", 0)) if prod.get("id") else 0

                # Categories from breadcrumbs if available; fallback to tags
                breadcrumbs = get_breadcrumbs_for_product(product_url)
                if breadcrumbs:
                    categories = breadcrumbs
                else:
                    categories = tags if isinstance(tags, list) else [t.strip() for t in str(tags).split(",") if t.strip()]

                for variant in prod.get("variants", []) or []:
                    try:
                        sku = variant.get("sku") or None
                        if not sku:
                            continue
                        if sku in seen_skus:
                            continue
                        seen_skus.add(sku)
                        price_cents = variant.get("price")
                        price = float(price_cents) / 100.0 if isinstance(price_cents, (int, float, str)) else 0.0
                        available = bool(variant.get("available"))
                        barcode = variant.get("barcode") or None

                        product = Product(
                            product_id=product_id,
                            name=title,
                            brand_name=vendor,
                            sku=sku,
                            price=price,
                            product_url=product_url,
                            stock_status="IN_STOCK" if available else "OUT_OF_STOCK",
                            imgurl=imgurl,
                            weight=None,
                            categories=categories,
                            barcode=barcode,
                        )
                        products.append(product)
                    except ValidationError:
                        continue
                    except Exception:
                        continue
            time.sleep(0.5)
        except Exception:
            continue

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
        'type': ['item_update'],
    })
    df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
    upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')

    print("[bold green]✅ Completed naturesante.ca item update[/bold green]")


if __name__ == "__main__":
    main()


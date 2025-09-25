import re
import json
import time
from datetime import datetime
import argparse
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


DOMAIN = "healthyplanetcanada.com"


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


def fetch_attribute_option_maps(session: requests.Session, base_url: str, wanted_codes: Optional[List[str]] = None) -> Dict[str, Dict[str, str]]:
    """Fetch Magento aggregations and return {attribute_code: {value: label}} maps."""
    result: Dict[str, Dict[str, str]] = {}
    try:
        graphql_url = f"{base_url}/graphql"
        q = (
            "{ products(search: \"\", pageSize: 1) { aggregations { attribute_code options { label value } } } }"
        )
        r = session.post(graphql_url, json={"query": q}, timeout=40)
        data = r.json() if r is not None else None
        aggs = (((data or {}).get("data") or {}).get("products") or {}).get("aggregations") or []
        for agg in aggs:
            code = (agg or {}).get("attribute_code")
            if not code:
                continue
            if wanted_codes and code not in wanted_codes:
                continue
            options = (agg or {}).get("options") or []
            m: Dict[str, str] = {}
            for opt in options:
                v = opt.get("value")
                lab = opt.get("label")
                if v in (None, "", "0"):
                    continue
                m[str(v)] = str(lab) if lab is not None else str(v)
            if m:
                result[code] = m
    except Exception:
        pass
    return result


def graphql_products_total_count(session: requests.Session, base_url: str, attr_code: str, attr_value: str) -> int:
    """Quickly get total_count for a given attribute filter."""
    try:
        graphql_url = f"{base_url}/graphql"
        q = (
            f"query {{ products(search: \"\", filter: {{ {attr_code}: {{ eq: \"{attr_value}\" }} }}, pageSize: 1, currentPage: 1) {{ total_count }} }}"
        )
        r = session.post(graphql_url, json={"query": q}, timeout=30)
        data = r.json() if r is not None else None
        total = (((data or {}).get("data") or {}).get("products") or {}).get("total_count")
        return int(total or 0)
    except Exception:
        return 0


def get_brand_links_from_db(sample_fraction_divider: int = 20) -> List[str]:
    """Read brand links from MySQL, filter for healthyplanetcanada.com, and sample rows.

    Sampling size: len(df_links)//sample_fraction_divider (at least 1).
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

    # Filter to healthyplanetcanada.com only
    df_links = df_links[df_links['brand_url'].astype(str).str.contains(DOMAIN, case=False, na=False)]
    if df_links.empty:
        print("[bold yellow]⚠️ No healthyplanetcanada.com links found in brand_link_list[/bold yellow]")
        return []

    # Compute sample size from df_links only
    sample_size: int = max(1, min(len(df_links), len(df_links) // sample_fraction_divider))

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

    # This function is retained for compatibility; Magento usually won't expose these
    candidates.append(f"{clean_url}.json")
    candidates.append(f"{clean_url}?view=json")

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


def parse_brand_filter_from_url(url: str) -> Optional[Tuple[str, str]]:
    """Extract Magento brand/manufacturer filter from a catalogsearch URL.

    Expected formats:
    - .../catalogsearch/result/?q=&brand=<OPTION_ID>
    - .../catalogsearch/result/?q=&manufacturer=<OPTION_ID>
    Returns (attribute_code, value) or None.
    """
    try:
        if not url:
            return None
        # Normalize
        q = url.split('?', 1)[-1] if '?' in url else ''
        parts = q.split('&') if q else []
        params: Dict[str, str] = {}
        for p in parts:
            if '=' in p:
                k, v = p.split('=', 1)
                params[k.strip().lower()] = v.strip()
        for code in ("brand", "manufacturer"):
            if code in params and params[code]:
                return code, params[code]
        return None
    except Exception:
        return None


def fetch_products_via_graphql(session: requests.Session, base_url: str, attr_code: str, attr_value: str, page_size: int = 50, max_pages: int = 4) -> List[dict]:
    """Fetch products for a given attribute filter using Magento GraphQL.

    Returns a list of product item dicts.
    """
    items: List[dict] = []
    try:
        graphql_url = f"{base_url}/graphql"
        current_page = 1
        # Build dynamic filter by attribute code
        # GraphQL variables allow us to pass code/value via string interpolation for the filter
        query = (
            "query productsByBrand($code: String!, $value: String!, $pageSize: Int!, $currentPage: Int!) {\n"
            "  products(search: \"\", filter: { } pageSize: $pageSize, currentPage: $currentPage) {\n"
            "    items { id sku name url_key url_suffix\n"
            "      image { url } small_image { url }\n"
            "      price_range { minimum_price { final_price { value } } }\n"
            "      stock_status\n"
            "      categories { name }\n"
            "    }\n"
            "    page_info { total_pages current_page }\n"
            "    total_count\n"
            "  }\n"
            "}"
        )
        # We'll inject the attribute filter by simple string replace technique since Magento GraphQL filter input type is not dynamic by variable name
        # Replace the empty filter with the actual filter
        # eq works as well as in for single values; prefer eq
        filter_fragment = f'{attr_code}: {{ eq: "{attr_value}" }}'
        query = query.replace("filter: { }", f"filter: {{ {filter_fragment} }}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        while current_page <= max_pages:
            payload = {
                "query": query,
                "variables": {
                    "code": attr_code,
                    "value": attr_value,
                    "pageSize": int(page_size),
                    "currentPage": int(current_page),
                },
            }
            r = session.post(graphql_url, headers=headers, json=payload, timeout=45)
            data = r.json() if r is not None else None
            products = (((data or {}).get("data") or {}).get("products") or {}).get("items") or []
            if isinstance(products, list) and products:
                items.extend(products)
            page_info = (((data or {}).get("data") or {}).get("products") or {}).get("page_info") or {}
            total_pages = int(page_info.get("total_pages") or 1)
            if current_page >= total_pages:
                break
            current_page += 1
            time.sleep(0.2)
    except Exception:
        pass
    return items


def get_products_for_brand_link(session: requests.Session, base_url: str, link: str) -> List[dict]:
    """Given a brand link (catalogsearch with brand/manufacturer param),
    fetch products via GraphQL. Tries both brand and manufacturer when needed.
    """
    try:
        pf = parse_brand_filter_from_url(link)
        if not pf:
            return []
        code, val = pf
        items = fetch_products_via_graphql(session, base_url, code, val, page_size=50, max_pages=3)
        if not items and code == 'brand':
            # Fallback: some stores use manufacturer attribute instead
            items = fetch_products_via_graphql(session, base_url, 'manufacturer', val, page_size=50, max_pages=3)
        if not items and code == 'manufacturer':
            items = fetch_products_via_graphql(session, base_url, 'brand', val, page_size=50, max_pages=3)
        return items or []
    except Exception:
        return []


def map_graphql_item_to_product(base_url: str, item: dict) -> Optional[dict]:
    try:
        url_key = (item or {}).get("url_key") or ""
        url_suffix = (item or {}).get("url_suffix") or ""
        if url_key and not url_suffix:
            # Default Magento URL suffix
            url_suffix = ".html"
        product_url = f"{base_url}/{url_key}{url_suffix}" if url_key else ""
        image = (((item or {}).get("image") or {}) or {}).get("url")
        if not image:
            image = (((item or {}).get("small_image") or {}) or {}).get("url")
        price = ((((item or {}).get("price_range") or {}).get("minimum_price") or {}).get("final_price") or {}).get("value")
        cats = [(c or {}).get("name") for c in ((item or {}).get("categories") or []) if (c or {}).get("name")]
        return {
            "id": int((item or {}).get("id") or 0),
            "sku": (item or {}).get("sku"),
            "name": (item or {}).get("name") or "",
            "product_url": product_url,
            "imgurl": image,
            "price": float(price) if price is not None else 0.0,
            "stock_status": (item or {}).get("stock_status") or None,
            "categories": cats,
        }
    except Exception:
        return None


def fetch_product_js(session: requests.Session, base_url: str, handle: str) -> Optional[dict]:
    # Not applicable for Magento; kept for compatibility
    return None


def fetch_root_products(session: requests.Session, base_url: str, limit: int = 100) -> List[dict]:
    # Not used for Magento
    return []


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
            # per spec: sku same value as product_id
            'sku': str(p.product_id),
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
            # per spec: sku same value as product_id
            'sku': str(p.product_id),
            'barcode': p.barcode,
            # Use title text for volume extraction per requirement
            'size': p.name,
            'breadcrumbs': breadcrumbs,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = extract_volume(df, vol_col="size", result_col="vol")
    # Drop helper column after extraction
    if 'size' in df.columns:
        df = df.drop(columns=['size'])
    df = df.rename(columns={'breadcrumbs': 'keywords'})
    return df


def main():
    parser = argparse.ArgumentParser(description="GoodnessMe JSON crawler")
    parser.add_argument("--discover", action="store_true", help="Probe JSON endpoints and print available fields")
    parser.add_argument("--limit", type=int, default=50, help="Max number of links to probe in discovery mode")
    args = parser.parse_args()

    start_ts = time.time()
    if args.discover:
        print("[bold cyan]🔎 Discovery mode: probing JSON endpoints and summarizing fields...[/bold cyan]")
    else:
        print("[bold cyan]🚀 Starting healthyplanetcanada.com item update from JSON...[/bold cyan]")

    # Session
    session = requests.Session(
        impersonate="chrome110",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    # Use canonical base without trailing slash to avoid '//'
    base_url = "https://www.healthyplanetcanada.com"

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

    # Enforce requested filters:
    # - only links from healthyplanetcanada.com
    # - include pattern '?q=&brand='
    brand_links = [
        u for u in brand_links
        if isinstance(u, str)
        and (DOMAIN in u)
        and ('?q=&brand=' in u.lower())
    ]
    print(f"✅ {len(brand_links)} links after domain and '?q=&brand=' filter")

    # Filter sampled links to those whose brand/manufacturer value exists in current aggregations
    option_maps = fetch_attribute_option_maps(session, base_url, wanted_codes=["brand", "manufacturer", "brands"])
    valid_values_by_code: Dict[str, set] = {code: set(vals.keys()) for code, vals in option_maps.items()}
    filtered_links: List[str] = []
    for link in brand_links:
        pf = parse_brand_filter_from_url(link)
        if not pf:
            continue
        code, val = pf
        if (code in valid_values_by_code and val in valid_values_by_code[code]):
            filtered_links.append(link)

    if filtered_links:
        brand_links = filtered_links
        print(f"✅ {len(brand_links)} links matched current Magento aggregation values")
    else:
        print("⚠️ No sampled links matched current aggregation values; proceeding with original sample")

    # Discovery branch: probe endpoints and summarize JSON fields
    if args.discover:
        probed = 0
        endpoints_found = 0
        from collections import Counter
        top_level_keys_counter: Counter = Counter()
        product_field_keys_counter: Counter = Counter()
        variant_field_keys_counter: Counter = Counter()
        product_js_keys_counter: Counter = Counter()
        variant_js_keys_counter: Counter = Counter()
        sample_outputs: List[str] = []

        for link in brand_links:
            if probed >= max(1, args.limit):
                break
            try:
                has_json, eps = probe_json_endpoints(session, link)
                probed += 1
                if not has_json:
                    continue
                for ep in eps:
                    try:
                        r = session.get(ep, headers={"Accept": "application/json"}, timeout=20)
                        data = r.json()
                        endpoints_found += 1
                        # Tally top-level keys
                        if isinstance(data, dict):
                            for k in list(data.keys())[:50]:
                                top_level_keys_counter[k] += 1
                        # Special handling for Shopify collection products.json
                        products = None
                        if isinstance(data, dict) and isinstance(data.get("products"), list) and data.get("products"):
                            products = data["products"]
                        elif isinstance(data, list) and data:
                            products = data
                        elif isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
                            # pick first list
                            for v in data.values():
                                if isinstance(v, list) and v:
                                    products = v
                                    break
                        # Summarize one product
                        if isinstance(products, list) and products:
                            p0 = products[0]
                            if isinstance(p0, dict):
                                for k in list(p0.keys())[:50]:
                                    product_field_keys_counter[k] += 1
                                vars0 = p0.get("variants")
                                if isinstance(vars0, list) and vars0:
                                    v0 = vars0[0]
                                    if isinstance(v0, dict):
                                        for k in list(v0.keys())[:50]:
                                            variant_field_keys_counter[k] += 1

                        # Keep a short sample record
                        sample_outputs.append(f"Endpoint: {ep}\nTop-level type: {type(data).__name__}\nKeys: {list(data.keys())[:10] if isinstance(data, dict) else 'n/a'}\n")
                    except Exception:
                        continue
                time.sleep(0.1)
            except Exception:
                continue

            # Additionally, try to extract product handles from the page HTML and fetch product.js
            try:
                r_html = session.get(link, timeout=30)
                if r_html.status_code == 200 and r_html.text:
                    handles = re.findall(r'href=["\']/(?:products)/([^"\'?/#]+)', r_html.text, flags=re.IGNORECASE)
                    # Deduplicate while preserving order
                    seen_h = set()
                    uniq_handles: List[str] = []
                    for h in handles:
                        if h not in seen_h:
                            seen_h.add(h)
                            uniq_handles.append(h)
                    for h in uniq_handles[:5]:
                        try:
                            pjs = fetch_product_js(session, base_url, h)
                            if isinstance(pjs, dict):
                                for k in list(pjs.keys())[:50]:
                                    product_js_keys_counter[k] += 1
                                vars0 = pjs.get("variants")
                                if isinstance(vars0, list) and vars0:
                                    v0 = vars0[0]
                                    if isinstance(v0, dict):
                                        for k in list(v0.keys())[:50]:
                                            variant_js_keys_counter[k] += 1
                        except Exception:
                            continue
            except Exception:
                pass

        # Print summary
        print(f"\nDiscovered {endpoints_found} JSON endpoints after probing {probed} links.")
        if endpoints_found == 0:
            print("No JSON endpoints found. Consider widening URL types or increasing sample size.")
        else:
            def top_n(counter, n=20):
                return ", ".join([f"{k}({v})" for k, v in counter.most_common(n)])
            print("\nTop-level keys seen:")
            print(top_n(top_level_keys_counter, 20))
            print("\nProduct fields seen:")
            print(top_n(product_field_keys_counter, 20))
            print("\nVariant fields seen:")
            print(top_n(variant_field_keys_counter, 20))
            print("\nSample endpoints:")
            for s in sample_outputs[:10]:
                print(s)
            print("\nproduct.js top-level keys:")
            print(", ".join([f"{k}({v})" for k, v in product_js_keys_counter.most_common(20)]))
            print("\nproduct.js variant keys:")
            print(", ".join([f"{k}({v})" for k, v in variant_js_keys_counter.most_common(20)]))

        # GraphQL probe for fields
        print("\nProbing GraphQL products fields...")
        try:
            # Use first brand filter if available
            test_filter = None
            for link in brand_links:
                pf = parse_brand_filter_from_url(link)
                if pf:
                    test_filter = pf
                    break
            if test_filter:
                code, val = test_filter
                test_items = fetch_products_via_graphql(session, base_url, code, val, page_size=5, max_pages=1)
                if test_items:
                    p0 = test_items[0]
                    print("GraphQL item keys:", ", ".join(list(p0.keys())[:30]))
        except Exception:
            pass

        # Probe sitemaps to extract product handles
        print("\nProbing product sitemaps for handles...")
        sitemap_urls = [f"{base_url}/sitemap_products_{i}.xml" for i in range(1, 6)]
        found_handles: List[str] = []
        for sm in sitemap_urls:
            try:
                r = session.get(sm, timeout=30)
                if r.status_code != 200:
                    continue
                locs = re.findall(r"<loc>\s*([^<]+)\s*</loc>", r.text)
                for loc in locs:
                    if "/products/" in loc:
                        try:
                            handle = loc.split("/products/")[-1].split("/")[0]
                            if handle and handle not in found_handles:
                                found_handles.append(handle)
                        except Exception:
                            continue
                if len(found_handles) >= 50:
                    break
            except Exception:
                continue

        # Fetch product.js for sampled handles
        handles_to_fetch = found_handles[:50]
        print(f"Found {len(found_handles)} handles from sitemaps; sampling {len(handles_to_fetch)} for product.js")
        for h in handles_to_fetch:
            try:
                pjs = fetch_product_js(session, base_url, h)
                if isinstance(pjs, dict):
                    for k in list(pjs.keys())[:50]:
                        product_js_keys_counter[k] += 1
                    vars0 = pjs.get("variants")
                    if isinstance(vars0, list) and vars0:
                        v0 = vars0[0]
                        if isinstance(v0, dict):
                            for k in list(v0.keys())[:50]:
                                variant_js_keys_counter[k] += 1
            except Exception:
                continue

        print("\nAggregate product fields (incl. root endpoints):")
        print(", ".join([f"{k}({v})" for k, v in product_field_keys_counter.most_common(30)]))
        print("\nAggregate variant fields (incl. root endpoints):")
        print(", ".join([f"{k}({v})" for k, v in variant_field_keys_counter.most_common(30)]))
        print("\nAggregate product.js top-level keys:")
        print(", ".join([f"{k}({v})" for k, v in product_js_keys_counter.most_common(30)]))
        print("\nAggregate product.js variant keys:")
        print(", ".join([f"{k}({v})" for k, v in variant_js_keys_counter.most_common(30)]))
        # Only duration logging in discovery mode
        end_ts = time.time()
        duration_in_minutes = (end_ts - start_ts) / 60.0
        df_duration = pd.DataFrame({
            'duration_min': [duration_in_minutes],
            'date': [datetime.now()],
            'results': [endpoints_found],
            'domain': [DOMAIN],
            'type': ['discovery'],
        })
        df_duration['result_per_minute'] = df_duration['results'] / df_duration['duration_min'].replace(0, 1)
        db_engine = get_database_engine()
        upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')
        print("[bold green]✅ Discovery completed[/bold green]")
        return

    # Collect products via Magento GraphQL by brand/manufacturer filters
    products: List[Product] = []
    seen_links: set[str] = set()

    # Build valid option maps to filter out stale IDs and get labels
    option_maps = fetch_attribute_option_maps(session, base_url, wanted_codes=["brand", "manufacturer", "brands"])
    valid_values_by_code: Dict[str, set] = {code: set(vals.keys()) for code, vals in option_maps.items()}
    label_by_code_value: Dict[Tuple[str, str], str] = {}
    for code, mapping in option_maps.items():
        for v, lab in mapping.items():
            label_by_code_value[(code, v)] = lab

    for link in brand_links:
        pf = parse_brand_filter_from_url(link)
        if not pf:
            continue
        code, val = pf
        # Skip if value not recognized by current aggregations
        if (code in valid_values_by_code) and (val not in valid_values_by_code[code]):
            continue
        # Skip brands with zero products
        if graphql_products_total_count(session, base_url, code, val) <= 0:
            continue
        items = fetch_products_via_graphql(session, base_url, code, val, page_size=50, max_pages=3)
        for it in items:
            mapped = map_graphql_item_to_product(base_url, it)
            if not mapped:
                continue
            try:
                p = Product(
                    product_id=int(mapped.get('id') or 0),
                    name=mapped.get('name') or '',
                    brand_name=label_by_code_value.get((code, val)),
                    sku=mapped.get('sku') or None,
                    price=float(mapped.get('price') or 0.0),
                    product_url=mapped.get('product_url') or '',
                    stock_status=mapped.get('stock_status') or None,
                    imgurl=mapped.get('imgurl') or None,
                    weight=None,
                    categories=mapped.get('categories') or None,
                    barcode=None,
                )
                # Deduplicate by product_url
                if p.product_url and p.product_url in seen_links:
                    continue
                if p.product_url:
                    seen_links.add(p.product_url)
                products.append(p)
            except ValidationError:
                continue
            except Exception:
                continue
        time.sleep(0.1)

    # If none collected, fallback: pick a few current aggregation values with products
    if not products:
        try:
            # Prefer 'brand' aggregation; fallback to 'manufacturer' if absent
            for pref_code in ("brand", "manufacturer"):
                vals_map = option_maps.get(pref_code) or {}
                if not vals_map:
                    continue
                picked = 0
                for val in list(vals_map.keys())[:50]:
                    if graphql_products_total_count(session, base_url, pref_code, val) <= 0:
                        continue
                    items = fetch_products_via_graphql(session, base_url, pref_code, val, page_size=50, max_pages=2)
                    for it in items:
                        mapped = map_graphql_item_to_product(base_url, it)
                        if not mapped:
                            continue
                        try:
                            p = Product(
                                product_id=int(mapped.get('id') or 0),
                                name=mapped.get('name') or '',
                                brand_name=(label_by_code_value.get((pref_code, val)) if 'label_by_code_value' in locals() else None),
                                sku=mapped.get('sku') or None,
                                price=float(mapped.get('price') or 0.0),
                                product_url=mapped.get('product_url') or '',
                                stock_status=mapped.get('stock_status') or None,
                                imgurl=mapped.get('imgurl') or None,
                                weight=None,
                                categories=mapped.get('categories') or None,
                                barcode=None,
                            )
                            if p.product_url and p.product_url in seen_links:
                                continue
                            if p.product_url:
                                seen_links.add(p.product_url)
                            products.append(p)
                        except ValidationError:
                            continue
                        except Exception:
                            continue
                    picked += 1
                    if picked >= 3 and len(products) >= 20:
                        break
                if products:
                    break
            if not products:
                print("[bold yellow]⚠️ No products collected via GraphQL[/bold yellow]")
        except Exception:
            print("[bold yellow]⚠️ No products collected via GraphQL[/bold yellow]")

    # Build DataFrames
    df_ticker = create_df_ticker(products)
    df_fixed_fields = create_df_fixed_fields(products)

    # Enrich keywords from HTML breadcrumbs when possible
    if not df_fixed_fields.empty:
        try:
            def extract_breadcrumbs_from_html(html: str) -> List[str]:
                try:
                    scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
                    def try_objects(obj) -> Optional[List[str]]:
                        try:
                            if isinstance(obj, dict):
                                if "@graph" in obj and isinstance(obj["@graph"], list):
                                    for node in obj["@graph"]:
                                        names = try_objects(node)
                                        if names:
                                            return names
                                if obj.get("@type") == "BreadcrumbList" and isinstance(obj.get("itemListElement"), list):
                                    names: List[str] = []
                                    for el in obj["itemListElement"]:
                                        if isinstance(el, dict):
                                            if isinstance(el.get("item"), dict) and el["item"].get("name"):
                                                names.append(str(el["item"]["name"]).strip())
                                            elif el.get("name"):
                                                names.append(str(el["name"]).strip())
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

            keywords_map: Dict[str, str] = {}
            for link in df_fixed_fields['link'].dropna().unique().tolist():
                try:
                    r = session.get(link, timeout=30)
                    if r.status_code == 200:
                        names = extract_breadcrumbs_from_html(r.text)
                        if names:
                            keywords_map[link] = ' > '.join(names)
                    time.sleep(0.1)
                except Exception:
                    continue
            if keywords_map:
                df_fixed_fields['keywords'] = df_fixed_fields['link'].map(lambda x: keywords_map.get(x) or df_fixed_fields.loc[df_fixed_fields['link'] == x, 'keywords'].values[0] if 'keywords' in df_fixed_fields.columns else keywords_map.get(x))
        except Exception:
            pass

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
    db_engine = get_database_engine()
    upsert_df_to_mysql(df=df_duration, engine=db_engine, target_table='duration', key_col='date')

    print("[bold green]✅ Completed healthyplanetcanada.com item update[/bold green]")


if __name__ == "__main__":
    main()


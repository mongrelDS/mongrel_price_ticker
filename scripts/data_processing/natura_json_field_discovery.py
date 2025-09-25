import re
import json
import time
import argparse
from typing import List, Optional, Tuple, Dict, Any

import sys
sys.path.append('/home/mongreldatalab/mongrel_price_ticker')

import pandas as pd
from curl_cffi import requests

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df


def read_unique_target_urls(limit: Optional[int] = None) -> List[str]:
    engine = get_database_engine()
    df = read_mysql_to_df(engine=engine, table_name='natura_link_pairs')
    if df is None or df.empty:
        return []
    if 'target_url' not in df.columns:
        return []
    urls = (
        df['target_url']
        .astype(str)
        .fillna('')
        .str.strip()
        .str.rstrip('/')
        .str.replace('www.', '', regex=False)
        .replace('', pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )
    if limit is not None and limit > 0:
        urls = urls[:limit]
    return urls


def probe_json_endpoints(session: requests.Session, url: str) -> Tuple[bool, List[str]]:
    candidates: List[str] = []
    clean_url = (url or '').rstrip('/')
    if not clean_url:
        return False, []

    # Generic JSON endpoints to try
    candidates.append(f"{clean_url}.json")
    candidates.append(f"{clean_url}?view=json")
    if "/collections/" in clean_url:
        candidates.append(f"{clean_url}/products.json?limit=5")

    available: List[str] = []
    for endpoint in candidates:
        try:
            r = session.get(endpoint, headers={"Accept": "application/json"}, timeout=20)
            if r.status_code == 200:
                try:
                    _ = r.json()
                    available.append(endpoint)
                except Exception:
                    pass
        except Exception:
            continue
    return (len(available) > 0, available)


def fetch_product_js(session: requests.Session, base_origin: str, handle: str) -> Optional[dict]:
    try:
        r = session.get(f"{base_origin}/products/{handle}.js", headers={"Accept": "application/json"}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def extract_origin(url: str) -> Optional[str]:
    try:
        m = re.match(r"^(https?://[^/]+)", url.strip())
        return m.group(1) if m else None
    except Exception:
        return None


def extract_jsonld_objects(html: str) -> List[Any]:
    try:
        scripts = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>([\s\S]*?)</script>', html, flags=re.IGNORECASE)
        found: List[Any] = []
        for s in scripts:
            try:
                data = json.loads(s.strip())
            except Exception:
                candidates = re.findall(r'\{[\s\S]*?\}', s)
                for cand in candidates:
                    try:
                        obj = json.loads(cand)
                        found.append(obj)
                    except Exception:
                        continue
                continue
            found.append(data)
    except Exception:
        return []
    return found


def tally_jsonld_objects(objs: List[Any], product_counter: Dict[str, int], offer_counter: Dict[str, int], top_counter: Dict[str, int]) -> None:
    def visit(obj: Any) -> None:
        try:
            if isinstance(obj, dict):
                for k in list(obj.keys())[:100]:
                    top_counter[k] += 1
                atype = obj.get("@type")
                atype_l = [atype] if isinstance(atype, str) else (atype or [])
                if any(str(t).lower() == "product" for t in atype_l):
                    for k in list(obj.keys())[:100]:
                        product_counter[k] += 1
                    offers = obj.get("offers")
                    if isinstance(offers, dict):
                        for k in list(offers.keys())[:100]:
                            offer_counter[k] += 1
                    elif isinstance(offers, list) and offers:
                        first = offers[0]
                        if isinstance(first, dict):
                            for k in list(first.keys())[:100]:
                                offer_counter[k] += 1
                if "@graph" in obj and isinstance(obj["@graph"], list):
                    for node in obj["@graph"]:
                        visit(node)
            elif isinstance(obj, list):
                for node in obj:
                    visit(node)
        except Exception:
            return
    for o in objs:
        visit(o)


def main():
    parser = argparse.ArgumentParser(description="Discover JSON fields from natura_link_pairs target_url")
    parser.add_argument("--limit", type=int, default=100, help="Max unique links to probe")
    args = parser.parse_args()

    session = requests.Session(
        impersonate="chrome110",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "application/json, text/html;q=0.9",
        },
    )

    urls = read_unique_target_urls(limit=None)
    if not urls:
        print("No URLs found.")
        return

    # Counters
    from collections import Counter
    top_level_keys_counter: Counter = Counter()
    product_field_keys_counter: Counter = Counter()
    variant_field_keys_counter: Counter = Counter()
    product_js_keys_counter: Counter = Counter()
    variant_js_keys_counter: Counter = Counter()
    jsonld_top_keys_counter: Counter = Counter()
    jsonld_product_keys_counter: Counter = Counter()
    jsonld_offer_keys_counter: Counter = Counter()
    sample_endpoints: List[str] = []
    probed_origins: set[str] = set()

    probed = 0
    for link in urls:
        if probed >= max(1, args.limit):
            break
        try:
            has_json, eps = probe_json_endpoints(session, link)
            probed += 1
            for ep in eps:
                try:
                    r = session.get(ep, headers={"Accept": "application/json"}, timeout=20)
                    data = r.json()
                    if isinstance(data, dict):
                        for k in list(data.keys())[:50]:
                            top_level_keys_counter[k] += 1
                    # Identify a representative product list
                    products = None
                    if isinstance(data, dict) and isinstance(data.get("products"), list) and data.get("products"):
                        products = data["products"]
                    elif isinstance(data, list) and data:
                        products = data
                    elif isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
                        for v in data.values():
                            if isinstance(v, list) and v:
                                products = v
                                break
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
                    sample_endpoints.append(f"{ep}")
                except Exception:
                    continue

            # Try to derive product handles and fetch product.js as well
            try:
                r_html = session.get(link, timeout=30)
                if r_html.status_code == 200 and r_html.text:
                    # JSON-LD tally
                    objs = extract_jsonld_objects(r_html.text)
                    if objs:
                        tally_jsonld_objects(objs, jsonld_product_keys_counter, jsonld_offer_keys_counter, jsonld_top_keys_counter)
                    # Extract product handles relative to origin
                    origin = extract_origin(link)
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
                            if not origin:
                                break
                            pjs = fetch_product_js(session, origin, h)
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

            # Probe root product endpoints per origin once
            try:
                origin = extract_origin(link)
                if origin and origin not in probed_origins:
                    probed_origins.add(origin)
                    for ep in [f"{origin}/products.json?limit=10", f"{origin}/collections/all/products.json?limit=10"]:
                        try:
                            r = session.get(ep, headers={"Accept": "application/json"}, timeout=20)
                            data = r.json()
                            if isinstance(data, dict) and isinstance(data.get("products"), list) and data["products"]:
                                sample_endpoints.append(ep)
                                p0 = data["products"][0]
                                if isinstance(p0, dict):
                                    for k in list(p0.keys())[:50]:
                                        product_field_keys_counter[k] += 1
                                    vars0 = p0.get("variants")
                                    if isinstance(vars0, list) and vars0:
                                        v0 = vars0[0]
                                        if isinstance(v0, dict):
                                            for k in list(v0.keys())[:50]:
                                                variant_field_keys_counter[k] += 1
                        except Exception:
                            continue
            except Exception:
                pass

            time.sleep(0.05)
        except Exception:
            continue

    def fmt(counter: Dict[str, int], n: int = 30) -> str:
        return ", ".join([f"{k}({v})" for k, v in counter.most_common(n)])

    print("\nDiscovered endpoints (sample):")
    for ep in sample_endpoints[:15]:
        print(ep)

    print("\nTop-level keys seen:")
    print(fmt(top_level_keys_counter, 25))

    print("\nProduct fields seen:")
    print(fmt(product_field_keys_counter, 25))

    print("\nVariant fields seen:")
    print(fmt(variant_field_keys_counter, 25))

    print("\nproduct.js top-level keys:")
    print(fmt(product_js_keys_counter, 25))

    print("\nproduct.js variant keys:")
    print(fmt(variant_js_keys_counter, 25))

    print("\nJSON-LD top-level keys:")
    print(fmt(jsonld_top_keys_counter, 25))

    print("\nJSON-LD Product keys:")
    print(fmt(jsonld_product_keys_counter, 25))

    print("\nJSON-LD Offer keys:")
    print(fmt(jsonld_offer_keys_counter, 25))


if __name__ == "__main__":
    main()



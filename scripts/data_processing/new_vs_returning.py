#!/usr/bin/env python3
import sys
from datetime import datetime
import pandas as pd
import os

ROOT_DIR = '/home/mongreldatalab/mongrel_price_ticker'
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df
from src.write_df_to_sheet import write_df_to_sheet
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheet configuration
SPREADSHEET_ID = '14RyPMn-Az2c2Zvrj-IzDZL9hrgo_U93GYmpPfzuXYMU'
READ_SHEET = 'new_vs_ret'
READ_RANGE = 'A2:A'
WRITE_SHEET_ORDER_COUNT = 'new_vs_ret_data'
WRITE_SHEET_ORDER_QTY = 'new_vs_ret_data_order_qty'
WRITE_CELL = 'A2'

SERVICE_ACCOUNT_KEY = os.path.join(
    ROOT_DIR, 'credentials', 'tactical-elf-452207-m9-1f0520891d95.json'
)


def read_sheet_values(spreadsheet_id: str, sheet_name: str, range_a1: str) -> list[list[str]]:
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    # Check if credentials file exists and is valid
    if not os.path.isfile(SERVICE_ACCOUNT_KEY):
        print(f"❌ Service account key not found at: {SERVICE_ACCOUNT_KEY}")
        print("📋 Please follow the setup instructions in credentials/README.md")
        return []
    
    # Check if the file contains placeholder values
    try:
        with open(SERVICE_ACCOUNT_KEY, 'r') as f:
            content = f.read()
            if 'PLACEHOLDER' in content:
                print(f"⚠️  Credentials file contains placeholder values: {SERVICE_ACCOUNT_KEY}")
                print("📋 Please replace with actual service account credentials (see credentials/README.md)")
                return []
    except Exception as e:
        print(f"❌ Error reading credentials file: {e}")
        return []
    
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)
        rng = f"'{sheet_name}'!{range_a1}" if ' ' in sheet_name else f"{sheet_name}!{range_a1}"
        resp = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
        return resp.get('values', [])
    except Exception as e:
        print(f"❌ Failed to read from Google Sheets: {e}")
        print("📋 Please check your credentials and sheet permissions (see credentials/README.md)")
        return []


def _normalize_email_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()


def _prep_orders_with_flags(
    df_shipped_orders: pd.DataFrame,
    df_customer_profile: pd.DataFrame,
    weeks: int = 6,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    ords = df_shipped_orders[[
        'order_date', 'email', 'order_number'
    ]].copy()
    prof = df_customer_profile[[
        'email', 'first_order_date'
    ]].copy()

    ords['order_date'] = pd.to_datetime(ords['order_date'], errors='coerce')
    prof['first_order_date'] = pd.to_datetime(prof['first_order_date'], errors='coerce')
    ords['email'] = _normalize_email_series(ords['email'])
    prof['email'] = _normalize_email_series(prof['email'])

    ords = ords.dropna(subset=['order_date', 'email', 'order_number']).drop_duplicates(subset=['order_number'])
    prof = prof.dropna(subset=['first_order_date'])

    orders = ords.merge(prof, on='email', how='inner')
    # New if order date equals first order date (date-level compare)
    orders['is_new'] = orders['order_date'].dt.floor('D').eq(orders['first_order_date'].dt.floor('D'))

    # Week bucketing: Monday anchored; wk_0 = most recent week
    if as_of is None:
        as_of = pd.Timestamp.utcnow().tz_localize(None)
    current_week_start = (as_of - pd.to_timedelta(as_of.weekday(), unit='D')).normalize()
    order_week_start = (orders['order_date'] - pd.to_timedelta(orders['order_date'].dt.weekday, unit='D')).dt.normalize()
    orders['weeks_ago'] = ((current_week_start - order_week_start) / pd.Timedelta(days=7)).astype(int)

    orders = orders[(orders['weeks_ago'] >= 0) & (orders['weeks_ago'] < weeks)].copy()
    return orders


def build_new_vs_return_by_sku_order_count(
    df_shipped_orders: pd.DataFrame,
    df_line_items: pd.DataFrame,
    df_customer_profile: pd.DataFrame,
    sku_list: list[str] | set[str] | None = None,
    weeks: int = 6,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    orders = _prep_orders_with_flags(
        df_shipped_orders=df_shipped_orders,
        df_customer_profile=df_customer_profile,
        weeks=weeks,
        as_of=as_of,
    )

    li = df_line_items[['order_number', 'sku']].dropna(subset=['order_number']).copy()
    data = li.merge(orders[['order_number', 'weeks_ago', 'is_new']], on='order_number', how='inner')
    if sku_list is not None:
        data = data[data['sku'].isin(set(sku_list))]
    # Count each order once per SKU
    data = data.drop_duplicates(subset=['sku', 'order_number'])

    grp = data.groupby(['sku', 'weeks_ago', 'is_new'], as_index=False).agg(order_count=('order_number', 'nunique'))

    p_new = grp[grp['is_new']].pivot(index='sku', columns='weeks_ago', values='order_count').add_prefix('wk_').add_suffix('_new')
    p_ret = grp[~grp['is_new']].pivot(index='sku', columns='weeks_ago', values='order_count').add_prefix('wk_').add_suffix('_ret')
    out = pd.concat([p_new, p_ret], axis=1).fillna(0).astype(int)
    cols = [c for k in range(weeks) for c in (f'wk_{k}_new', f'wk_{k}_ret')]
    out = out.reindex(columns=[c for c in cols if c in out.columns]).reset_index().rename(columns={'index': 'sku'})
    return out


def build_new_vs_return_by_sku_order_qty(
    df_shipped_orders: pd.DataFrame,
    df_line_items: pd.DataFrame,
    df_customer_profile: pd.DataFrame,
    sku_list: list[str] | set[str] | None = None,
    weeks: int = 6,
    as_of: datetime | None = None,
) -> pd.DataFrame:
    orders = _prep_orders_with_flags(
        df_shipped_orders=df_shipped_orders,
        df_customer_profile=df_customer_profile,
        weeks=weeks,
        as_of=as_of,
    )

    li = df_line_items[['order_number', 'sku', 'quantity']].copy()
    li['quantity'] = pd.to_numeric(li['quantity'], errors='coerce').fillna(0)
    data = li.merge(orders[['order_number', 'weeks_ago', 'is_new']], on='order_number', how='inner')
    if sku_list is not None:
        data = data[data['sku'].isin(set(sku_list))]

    grp = data.groupby(['sku', 'weeks_ago', 'is_new'], as_index=False).agg(order_qty=('quantity', 'sum'))

    p_new = grp[grp['is_new']].pivot(index='sku', columns='weeks_ago', values='order_qty').add_prefix('wk_').add_suffix('_qty_new')
    p_ret = grp[~grp['is_new']].pivot(index='sku', columns='weeks_ago', values='order_qty').add_prefix('wk_').add_suffix('_qty_ret')
    out = pd.concat([p_new, p_ret], axis=1).fillna(0).astype(int)
    cols = [c for k in range(weeks) for c in (f'wk_{k}_qty_new', f'wk_{k}_qty_ret')]
    out = out.reindex(columns=[c for c in cols if c in out.columns]).reset_index().rename(columns={'index': 'sku'})
    return out


def main():
    engine = get_database_engine()

    # Read SKU list from sheet
    raw = read_sheet_values(SPREADSHEET_ID, READ_SHEET, READ_RANGE)
    sku_list = [r[0].strip() for r in raw if len(r) > 0 and str(r[0]).strip()]

    # Load required tables
    df_shipped_orders = read_mysql_to_df(engine=engine, table_name='natura_shipped_orders')
    df_line_items = read_mysql_to_df(engine=engine, table_name='natura_line_items')
    df_customer_profile = read_mysql_to_df(engine=engine, table_name='natura_customer_profile')
    df_products = read_mysql_to_df(engine=engine, table_name='natura_product_table')

    # Build outputs
    order_count = build_new_vs_return_by_sku_order_count(
        df_shipped_orders=df_shipped_orders,
        df_line_items=df_line_items,
        df_customer_profile=df_customer_profile,
        sku_list=sku_list,
        weeks=6,
    )

    order_qty = build_new_vs_return_by_sku_order_qty(
        df_shipped_orders=df_shipped_orders,
        df_line_items=df_line_items,
        df_customer_profile=df_customer_profile,
        sku_list=sku_list,
        weeks=6,
    )

    # Join product name and order by input SKU list
    if df_products is not None and not df_products.empty and 'sku' in df_products.columns:
        prod_cols = [c for c in ['sku', 'name', 'product_title'] if c in df_products.columns]
        prod = df_products[prod_cols].drop_duplicates('sku')
        if 'name' not in prod.columns and 'product_title' in prod.columns:
            prod = prod.rename(columns={'product_title': 'name'})
        order_count = order_count.merge(prod[['sku', 'name']], on='sku', how='left')
        order_qty = order_qty.merge(prod[['sku', 'name']], on='sku', how='left')

        def reorder_cols(df: pd.DataFrame) -> pd.DataFrame:
            base_cols = ['sku', 'name']
            others = [c for c in df.columns if c not in base_cols]
            return df[base_cols + others]

        order_count = reorder_cols(order_count)
        order_qty = reorder_cols(order_qty)

    order_map = {s: i for i, s in enumerate(sku_list)}
    for df in (order_count, order_qty):
        df['_order'] = df['sku'].map(order_map).fillna(1e9).astype(int)
        df.sort_values('_order', inplace=True)
        df.drop(columns=['_order'], inplace=True)

    # Write to Google Sheets
    write_df_to_sheet(order_count, SPREADSHEET_ID, WRITE_SHEET_ORDER_COUNT, WRITE_CELL)
    write_df_to_sheet(order_qty, SPREADSHEET_ID, WRITE_SHEET_ORDER_QTY, WRITE_CELL)

    print(f"Wrote {len(order_count)} rows to '{WRITE_SHEET_ORDER_COUNT}' and {len(order_qty)} rows to '{WRITE_SHEET_ORDER_QTY}'.")


if __name__ == '__main__':
    main()

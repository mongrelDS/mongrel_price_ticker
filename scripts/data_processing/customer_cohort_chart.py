#!/usr/bin/env python3
import sys
from datetime import datetime
import pandas as pd
import numpy as np
import os

ROOT_DIR = '/home/mongreldatalab/mongrel_price_ticker'
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df
from src.write_df_to_sheet import write_df_to_sheet
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '14RyPMn-Az2c2Zvrj-IzDZL9hrgo_U93GYmpPfzuXYMU'
SHEET_WEEK_COUNT = 'week count'
RANGE_WEEK_HEADERS = 'O1:FQ2'

SHEET_REVENUE = 'CC_Revenue'
SHEET_ORDERS = 'CC Order Count'
SHEET_CUSTOMERS = 'CC Customer Count'
WRITE_CELL = 'A6'

SERVICE_ACCOUNT_KEY = os.path.join(
    ROOT_DIR, 'credentials', 'tactical-elf-452207-m9-1f0520891d95.json'
)


def read_sheet_values(spreadsheet_id: str, sheet_name: str, range_a1: str) -> list[list[str]]:
    scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_KEY, scopes=scopes)
    service = build('sheets', 'v4', credentials=creds)
    rng = f"'{sheet_name}'!{range_a1}" if ' ' in sheet_name else f"{sheet_name}!{range_a1}"
    resp = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    return resp.get('values', [])


def get_week_headers() -> list[str]:
    rows = read_sheet_values(SPREADSHEET_ID, SHEET_WEEK_COUNT, RANGE_WEEK_HEADERS)
    if not rows:
        return []
    max_len = max(len(r) for r in rows)
    headers: list[str] = []
    for j in range(max_len):
        cell_val = None
        for r in reversed(rows):  # prefer lower row if present
            if j < len(r):
                s = str(r[j]).strip()
                if s:
                    cell_val = s
                    break
        if cell_val:
            headers.append(cell_val)
    return headers


def add_cohort_fields(df: pd.DataFrame, as_of: datetime | None = None) -> pd.DataFrame:
    required = ['order_date', 'order_number', 'customer_email']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')
    # Drop rows missing critical fields
    df = df.dropna(subset=['order_date', 'order_number', 'customer_email'])
    if 'subtotal' in df.columns:
        df['subtotal'] = pd.to_numeric(df['subtotal'], errors='coerce')

    dedup_cols = [c for c in ['order_date', 'sku', 'quantity', 'order_number', 'subtotal'] if c in df.columns]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols, keep='first')

    if as_of is None:
        as_of = pd.Timestamp.utcnow().normalize()

    first_order = (
        df.groupby('customer_email', as_index=False)['order_date']
          .min()
          .rename(columns={'order_date': 'cohort_start_date'})
    )
    df = df.merge(first_order, on='customer_email', how='left')

    df['days_since_cohort_start'] = (df['order_date'] - df['cohort_start_date']).dt.days
    # Handle any residual NaNs safely before integer conversion
    df['nth_week'] = ((df['days_since_cohort_start'].fillna(0).clip(lower=0)) // 7).astype(int)
    df['nth_week_str'] = df['nth_week'].astype(str).str.zfill(2)

    iso = df['cohort_start_date'].dt.isocalendar()
    df['start_week_no'] = df['cohort_start_date'].dt.strftime('%y') + ' Wk ' + iso.week.astype(int).astype(str).str.zfill(2)
    df['cohort_year'] = df['cohort_start_date'].dt.year.astype(int)

    df['new_customer'] = (df['nth_week'] == 0).astype(int)
    df['return_customer'] = 1 - df['new_customer']

    if 'quantity' in df.columns:
        q = pd.to_numeric(df['quantity'], errors='coerce').fillna(0)
        df['shipped_to_new_customer'] = q * df['new_customer']
        df['shipped_to_return_customer'] = q * df['return_customer']

    return df


def apply_fixed_order(p: pd.DataFrame, max_weeks: int = 156) -> pd.DataFrame:
    p = p.copy()
    desired_cols = ['Cohort Week', 'Year'] + list(range(0, max_weeks + 1))
    # Ensure all desired columns exist
    for col in desired_cols:
        if col not in p.columns:
            p[col] = np.nan
    # Order columns
    p = p[desired_cols]
    # Sort newest cohorts first
    p = p.sort_values(['Cohort Week'], ascending=False)
    return p


def generate_cohort_row_labels(min_date: pd.Timestamp, max_date: pd.Timestamp) -> list[str]:
    # Normalize to dates
    start = pd.to_datetime(min_date).normalize()
    end = pd.to_datetime(max_date).normalize()
    if pd.isna(start) or pd.isna(end) or start > end:
        return []
    # Generate Mondays across range
    # Align start to Monday
    start_monday = start - pd.to_timedelta((start.weekday() + 6) % 7, unit='D')
    weeks = pd.date_range(start=start_monday, end=end, freq='W-MON')
    labels: list[str] = []
    for d in weeks:
        iso = d.isocalendar()
        iso_year = int(iso.year)
        iso_week = int(iso.week)
        # Apply same January remap rule
        if d.month == 1 and iso_week in (52, 53):
            iso_year += 1
            iso_week = 1
        label = f"{iso_year % 100:02d} Wk {iso_week:02d}"
        if not labels or labels[-1] != label:
            labels.append(label)
    return labels


def apply_row_labels(p: pd.DataFrame, labels: list[str]) -> pd.DataFrame:
    if not labels:
        return p
    p = p.copy()
    # Ensure Cohort Week exists
    if 'Cohort Week' not in p.columns:
        return p
    # Build frame with desired rows
    base = pd.DataFrame({'Cohort Week': labels})
    p = base.merge(p, on='Cohort Week', how='left')
    return p


def _parse_label_year_week(label: str) -> tuple[int, int]:
    try:
        parts = str(label).split()
        yy = int(parts[0])
        ww = int(parts[2])
        year = 2000 + yy
        return year, ww
    except Exception:
        return (None, None)


def _format_week_range(year: int, week: int) -> str:
    from datetime import date, timedelta
    try:
        start = date.fromisocalendar(year, week, 1)
        end = start + pd.Timedelta(days=6)
        # If same month: "Sep 14 to 20", else: "Sep 30 to Oct 6"
        if start.month == end.month:
            return f"{start:%b} {start.day} to {end.day}"
        else:
            return f"{start:%b} {start.day} to {end:%b} {end.day}"
    except Exception:
        return ""


def finalize_display_format(p: pd.DataFrame) -> pd.DataFrame:
    p = p.copy()
    # Derive Year from Cohort Week label
    parsed = p['Cohort Week'].apply(_parse_label_year_week)
    p['_year'] = parsed.apply(lambda t: t[0])
    p['_week'] = parsed.apply(lambda t: t[1])
    p['Year'] = p['_year']
    # Append date range suffix
    p['Cohort Week'] = p.apply(
        lambda r: f"{r['Cohort Week']}  |  {_format_week_range(int(r['_year']), int(r['_week']))}" if pd.notna(r['_year']) and pd.notna(r['_week']) else r['Cohort Week'],
        axis=1
    )
    # Sort by year/week descending
    p = p.sort_values(by=['_year', '_week'], ascending=False)
    p = p.drop(columns=['_year', '_week'])
    return p


def make_cohort_pivots(df: pd.DataFrame, max_weeks: int = 156) -> dict[str, pd.DataFrame]:
    df = df.copy()

    def pivot(values, aggfunc):
        p = df.pivot_table(
            index=['start_week_no', 'cohort_year'],
            columns='nth_week',
            values=values,
            aggfunc=aggfunc,
            dropna=False,
).reset_index()
        p = p.rename(columns={'start_week_no': 'Cohort Week', 'cohort_year': 'Year'})
        p = p.sort_values(['Cohort Week'], ascending=False)
        p = apply_fixed_order(p, max_weeks=max_weeks)
        return p

    pivots = {}
    if 'subtotal' in df.columns:
        pivots['revenue'] = pivot('subtotal', 'sum')
    pivots['orders'] = pivot('order_number', pd.Series.nunique)
    pivots['customers'] = pivot('customer_email', pd.Series.nunique)
    return pivots


def normalize_email_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()


def build_pivots_from_sources(engine) -> dict[str, pd.DataFrame]:
    # Load sources
    prof = read_mysql_to_df(engine=engine, table_name='natura_customer_profile')
    ords = read_mysql_to_df(engine=engine, table_name='natura_shipped_orders')
    lines = read_mysql_to_df(engine=engine, table_name='natura_line_items')

    if prof is None or prof.empty or ords is None or ords.empty or lines is None or lines.empty:
        raise ValueError("One or more required tables are empty: natura_customer_profile, natura_shipped_orders, natura_line_items")

    # Profile: keep email, first_order_date
    prof_cols = [c for c in ['email', 'first_order_date'] if c in prof.columns]
    prof = prof[prof_cols].dropna().copy()
    prof['email'] = normalize_email_series(prof['email'])
    prof['first_order_date'] = pd.to_datetime(prof['first_order_date'], errors='coerce')
    prof = prof.dropna(subset=['first_order_date'])

    # Orders: keep email, order_date, order_number
    ord_cols = [c for c in ['email', 'order_date', 'order_number'] if c in ords.columns]
    ords = ords[ord_cols].dropna(subset=['email', 'order_date', 'order_number']).copy()
    ords['email'] = normalize_email_series(ords['email'])
    ords['order_date'] = pd.to_datetime(ords['order_date'], errors='coerce')
    ords = ords.dropna(subset=['order_date'])
    ords = ords.drop_duplicates(subset=['order_number'])

    # Lines: keep order_date, order_number, quantity, price, subtotal
    line_cols = [c for c in ['order_date', 'order_number', 'quantity', 'price', 'subtotal'] if c in lines.columns]
    lines = lines[line_cols].dropna(subset=['order_number']).copy()
    lines['order_date'] = pd.to_datetime(lines['order_date'], errors='coerce')
    lines = lines.dropna(subset=['order_date'])
    lines['subtotal'] = pd.to_numeric(lines['subtotal'], errors='coerce').fillna(0.0)

    # Orders with cohort
    ow = ords.merge(prof, on='email', how='inner')
    ow['nth_week'] = ((ow['order_date'] - ow['first_order_date']).dt.days // 7).clip(lower=0).astype(int)
    iso = ow['first_order_date'].dt.isocalendar()
    # Default ISO label
    iso_year = iso.year.astype(int)
    iso_week = iso.week.astype(int)
    # Business rule: if month is January but ISO week is 52/53, map to next-year Wk 01
    jan_mask = ow['first_order_date'].dt.month.eq(1) & iso_week.isin([52, 53])
    adj_year = iso_year.where(~jan_mask, iso_year + 1)
    adj_week = iso_week.where(~jan_mask, 1)
    iso_year_2 = (adj_year % 100).astype(int).astype(str).str.zfill(2)
    ow['Cohort Week'] = iso_year_2 + ' Wk ' + adj_week.astype(int).astype(str).str.zfill(2)

    # Revenue lines with cohort: join email via orders
    ow_map = ow[['order_number', 'email', 'order_date']].drop_duplicates()
    lw = lines.merge(ow_map, on='order_number', how='inner', suffixes=('_line', '_order'))
    lw = lw.merge(prof, on='email', how='inner')
    # Use the order-level date for cohort week calculation
    if 'order_date_order' in lw.columns:
        lw['order_date_order'] = pd.to_datetime(lw['order_date_order'], errors='coerce')
        order_dt = lw['order_date_order']
    else:
        # Fallback to line-level date if order-level not present
        lw['order_date_line'] = pd.to_datetime(lw.get('order_date_line'), errors='coerce')
        order_dt = lw['order_date_line']
    lw['first_order_date'] = pd.to_datetime(lw['first_order_date'], errors='coerce')
    lw['nth_week'] = ((order_dt - lw['first_order_date']).dt.days // 7).clip(lower=0).astype(int)
    iso_l = lw['first_order_date'].dt.isocalendar()
    l_iso_year = iso_l.year.astype(int)
    l_iso_week = iso_l.week.astype(int)
    l_jan_mask = lw['first_order_date'].dt.month.eq(1) & l_iso_week.isin([52, 53])
    l_adj_year = l_iso_year.where(~l_jan_mask, l_iso_year + 1)
    l_adj_week = l_iso_week.where(~l_jan_mask, 1)
    iso_l_year_2 = (l_adj_year % 100).astype(int).astype(str).str.zfill(2)
    lw['Cohort Week'] = iso_l_year_2 + ' Wk ' + l_adj_week.astype(int).astype(str).str.zfill(2)

    # Pivots
    orders_p = (
        ow.pivot_table(index=['Cohort Week'], columns='nth_week', values='order_number', aggfunc=pd.Series.nunique, dropna=False)
          .reset_index()
    )
    # Row labels spanning overall cohort date range
    min_first = min(ow['first_order_date'].min(), lw['first_order_date'].min())
    max_first = max(ow['first_order_date'].max(), lw['first_order_date'].max())
    row_labels = generate_cohort_row_labels(min_first, max_first)
    orders_p = apply_row_labels(orders_p, row_labels)
    orders_p = apply_fixed_order(orders_p, max_weeks=156)

    customers_p = (
        ow.pivot_table(index=['Cohort Week'], columns='nth_week', values='email', aggfunc=pd.Series.nunique, dropna=False)
          .reset_index()
    )
    customers_p = apply_row_labels(customers_p, row_labels)
    customers_p = apply_fixed_order(customers_p, max_weeks=156)

    revenue_p = (
        lw.pivot_table(index=['Cohort Week'], columns='nth_week', values='subtotal', aggfunc='sum', dropna=False)
          .reset_index()
    )
    revenue_p = apply_row_labels(revenue_p, row_labels)
    revenue_p = apply_fixed_order(revenue_p, max_weeks=156)

    return {'orders': orders_p, 'customers': customers_p, 'revenue': revenue_p}


def main():
    print("Connecting to DB...")
    engine = get_database_engine()

    print("Building pivots from customer profile + shipped_orders + line_items...")
    pivots = build_pivots_from_sources(engine)

    if 'revenue' in pivots:
        print(f"Writing revenue -> {SHEET_REVENUE}")
        write_df_to_sheet(finalize_display_format(pivots['revenue']), SPREADSHEET_ID, SHEET_REVENUE, WRITE_CELL)

    print(f"Writing orders -> {SHEET_ORDERS}")
    write_df_to_sheet(finalize_display_format(pivots['orders']), SPREADSHEET_ID, SHEET_ORDERS, WRITE_CELL)

    print(f"Writing customers -> {SHEET_CUSTOMERS}")
    write_df_to_sheet(finalize_display_format(pivots['customers']), SPREADSHEET_ID, SHEET_CUSTOMERS, WRITE_CELL)

    print("Done.")


if __name__ == '__main__':
    main()



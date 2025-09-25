#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np

ROOT_DIR = '/home/mongreldatalab/mongrel_price_ticker'
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.database_config import get_database_engine
from src.mySQL_Upsert_Function_with_Batch import read_mysql_to_df


def normalize_email(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower()


def cohort_label_with_jan_remap(d: pd.Series) -> pd.Series:
    d = pd.to_datetime(d, errors='coerce')
    iso = d.dt.isocalendar()
    iso_year = iso.year.astype(int)
    iso_week = iso.week.astype(int)
    jan_mask = d.dt.month.eq(1) & iso_week.isin([52, 53])
    adj_year = iso_year.where(~jan_mask, iso_year + 1)
    adj_week = iso_week.where(~jan_mask, 1)
    return (adj_year % 100).astype(int).astype(str).str.zfill(2) + ' Wk ' + adj_week.astype(int).astype(str).str.zfill(2)


def main():
    engine = get_database_engine()
    prof = read_mysql_to_df(engine, 'natura_customer_profile')
    ords = read_mysql_to_df(engine, 'natura_shipped_orders')

    prof = prof[['email', 'first_order_date']].dropna()
    prof['email'] = normalize_email(prof['email'])
    prof['first_order_date'] = pd.to_datetime(prof['first_order_date'], errors='coerce')
    prof = prof.dropna(subset=['first_order_date'])
    prof['Cohort Week'] = cohort_label_with_jan_remap(prof['first_order_date'])

    ords = ords[['email', 'order_date', 'order_number']].dropna(subset=['email', 'order_date', 'order_number'])
    ords['email'] = normalize_email(ords['email'])
    ords['order_date'] = pd.to_datetime(ords['order_date'], errors='coerce')
    ords = ords.dropna(subset=['order_date'])
    ords = ords.drop_duplicates(subset=['order_number'])

    ow = ords.merge(prof, on='email', how='inner')
    ow['nth_week'] = ((ow['order_date'] - ow['first_order_date']).dt.days // 7).clip(lower=0)
    ow['Cohort Week'] = cohort_label_with_jan_remap(ow['first_order_date'])

    # Targets to inspect
    targets = ['24 Wk 01', '23 Wk 51', '23 Wk 52', '24 Wk 02']

    print("\n=== Cohort size vs shipped-orders week0 counts ===")
    for label in targets:
        cohort_emails = prof.loc[prof['Cohort Week'] == label, 'email'].nunique()
        week0_orders = (
            ow.loc[(ow['Cohort Week'] == label) & (ow['nth_week'] == 0), 'order_number']
              .nunique()
        )
        any_order_emails = ow.loc[ow['Cohort Week'] == label, 'email'].nunique()
        avg_diff_days = (
            ow.loc[(ow['Cohort Week'] == label) & (ow['nth_week'] == 0), ['order_date','first_order_date']]
              .assign(diff=lambda x: (x['order_date'] - x['first_order_date']).dt.days)
              ['diff']
              .mean()
        )
        print(f"{label}: cohort_emails={cohort_emails}, week0_orders={week0_orders}, any_order_emails={any_order_emails}, avg_day_diff_first_vs_order={avg_diff_days}")

    # Check emails in cohort but missing any shipped order
    label = '24 Wk 01'
    cset = set(prof.loc[prof['Cohort Week'] == label, 'email'])
    oset = set(ow.loc[ow['Cohort Week'] == label, 'email'])
    missing = sorted(list(cset - oset))[:10]
    print(f"\nSample emails in {label} missing in shipped_orders (first 10): {missing}")


if __name__ == '__main__':
    main()



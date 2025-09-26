#!/usr/bin/env python3
import pandas as pd
import numpy as np

import sys
import os
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from database_config import get_database_engine
from cleanup_column_names import clean_column_names
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from function_extract_volume import extract_volume


def get_30d_sales(engine) -> pd.DataFrame:
    query = (
        """
        SELECT
            sku,
            SUM(COALESCE(quantity, 0)) AS l30d_sales
        FROM natura_line_items
        WHERE order_date >= NOW() - INTERVAL 30 DAY
        GROUP BY sku
        """
    )
    df = pd.read_sql_query(query, con=engine)
    return df


def get_sku_data(engine) -> pd.DataFrame:
    query = (
        """
        SELECT
            sku, name, value, price, barcode, product_note
        FROM natura_product_table
        """
    )
    df = pd.read_sql_query(query, con=engine)

    # Rename and filter
    df = df.rename(columns={"value": "cost"})
    if "product_note" in df.columns:
        df = df[~df["product_note"].astype(str).str.contains("discontinued", case=False, na=False)]
        df = df.drop(columns=["product_note"])

    # Ensure types
    df["price"] = pd.to_numeric(df.get("price"), errors="coerce")
    df["cost"] = pd.to_numeric(df.get("cost"), errors="coerce")

    # Deduplicate by sku
    if "sku" in df.columns:
        df = df.dropna(subset=["sku"]).drop_duplicates(subset=["sku"], keep="first")

    return df


def build_natura_sku_summary(engine) -> pd.DataFrame:
    df_30d_sales = get_30d_sales(engine)
    df_sku_data = get_sku_data(engine)

    # Left merge on sku
    df = df_sku_data.merge(df_30d_sales, on="sku", how="left")
    df["l30d_sales"] = pd.to_numeric(df.get("l30d_sales"), errors="coerce").fillna(0).astype(int)

    # Cleanup column names
    df = clean_column_names(df)

    # Compute margin as percent string
    price = pd.to_numeric(df.get("price"), errors="coerce")
    cost = pd.to_numeric(df.get("cost"), errors="coerce")
    margin_num = (price - cost) / price
    margin_num = margin_num.replace([np.inf, -np.inf], np.nan).fillna(0)
    df["margin"] = (margin_num * 100).round(2).map(lambda x: f"{x:.2f}%")

    # Weighted average margin contribution by last 30d sales, as percent string
    total_sales = df["l30d_sales"].sum()
    if total_sales > 0:
        wtd = (margin_num * df["l30d_sales"] / total_sales).fillna(0)
    else:
        wtd = pd.Series(0, index=df.index, dtype=float)
    df["wtd_avg_margin"] = (wtd * 100).round(2).map(lambda x: f"{x:.2f}%")

    # Extract volume from product name
    if "name" in df.columns:
        df = extract_volume(df, vol_col="name", result_col="vol")

    # Final selection and ordering
    keep_cols = [
        "sku", "name", "l30d_sales", "cost", "price", "margin", "wtd_avg_margin", "barcode", "vol"
    ]
    for c in keep_cols:
        if c not in df.columns:
            df[c] = pd.NA
    df = df[keep_cols]

    return df


def main():
    engine = get_database_engine()

    df_natura_sku_summary = build_natura_sku_summary(engine)

    # Upsert to MySQL table
    upsert_df_to_mysql(
        df=df_natura_sku_summary,
        engine=engine,
        target_table="natura_sku_summary",
        key_col="sku",
    )

    try:
        print(df_natura_sku_summary.head().to_string(index=False))
        print(f"\nRows prepared: {len(df_natura_sku_summary)}")
    except Exception:
        pass


if __name__ == "__main__":
    main()



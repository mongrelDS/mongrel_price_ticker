# @title Calculate Days Since Date

import pandas as pd
from datetime import datetime


def calculate_days_since_date(df, date_column='date'):
    """
    Calculates the number of days between today and the date in the specified column.

    Args:
        df (pd.DataFrame): The pandas DataFrame.
        date_column (str): The name of the column containing the date.
                          Defaults to 'date'.

    Returns:
        pd.DataFrame: The DataFrame with a new 'days' column added.
    """
    # Get today's date
    today = datetime.now()

    # Convert date column to datetime
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')

    # Calculate days since date
    df['days'] = (today - df[date_column]).dt.days

    # Handle NaT and negative values
    df.loc[df['days'] < 0, 'days'] = 0
    df.loc[pd.isna(df[date_column]), 'days'] = 999

    return df

# Usage:
# df_ticker = calculate_days_since_date(df_ticker)
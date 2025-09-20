# @title cleanup the column names

import re

def clean_column_names(df):
  """
  Cleans column names to be compatible with BigQuery.

  Args:
    df: Pandas DataFrame.

  Returns:
    Pandas DataFrame with cleaned column names.
  """
  cleaned_names = []
  for name in df.columns:
    cleaned_name = re.sub(r'[^\w\s]', '_', name).strip().replace(' ', '_').replace('__', '_').lower().rstrip("_") # Replace special characters with underscores
    cleaned_names.append(cleaned_name)
  df.columns = cleaned_names
  return df

# shiphero_order_list = clean_column_names(shiphero_order_list)
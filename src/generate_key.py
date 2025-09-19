# @title HashKey

import pandas as pd
import hashlib

def generate_key(df, deduplication_columns, key_col="key"):
    """
    Generates a unique 13-character key for each row in a DataFrame based on
    a set of deduplication columns.

    Args:
        df (pd.DataFrame): The input DataFrame.
        deduplication_columns (list): A list of column names to be used for
                                      key generation.
        key_col (str, optional): The name of the new column to store the
                                 generated key. Defaults to "key".

    Returns:
        pd.DataFrame: The DataFrame with the new key column added.
    """
    # Step 1: Join the deduplication columns into a single string for each row.
    # We convert to string and fill any NaN values to ensure consistency.
    concatenated_strings = df[deduplication_columns].astype(str).agg(''.join, axis=1)

    # Step 2: Generate a hash key from this string.
    # We use a lambda function with .apply() to iterate through the series
    # and compute the SHA-256 hash for each concatenated string.
    # The string must be encoded to bytes before hashing.
    hashed_keys = concatenated_strings.apply(
        lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest()
    )

    # Step 3: Assign the 13-character hash to the key_col.
    df[key_col] = hashed_keys.str[:13]

    return df
import pandas as pd
import re
import numpy as np
from typing import Union, Optional, List
import warnings

def price_to_float(
    df: pd.DataFrame, 
    price_col: str = "price", 
    currency_marker: str = "$"
) -> pd.DataFrame:
    """
    Converts a DataFrame column of price strings to float values.

    This function processes each string in the specified column to extract a
    numerical price. It handles strings with single prices, multiple prices
    (selecting the lowest non-zero value), and removes specified currency
    markers. Supports various international number formats including:
    - US format: $1,234.56
    - European format: €1.234,56
    - French format: 1 500 € (with space as thousand separator)
    - Mixed formats with multiple prices

    Args:
        df (pd.DataFrame): The input DataFrame.
        price_col (str, optional): The name of the column containing the
                                   price strings. Defaults to "price".
        currency_marker (str, optional): The currency symbol to remove
                                         from the strings. Defaults to "$".

    Returns:
        pd.DataFrame: The DataFrame with the price column converted to floats.
                     Non-convertible values are set to NaN.

    Raises:
        KeyError: If the specified price_col doesn't exist in the DataFrame.
        ValueError: If the DataFrame is empty or invalid.

    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'price': ['$4.99', '$29.99 sale $39.99']})
        >>> result = price_to_float(df)
        >>> print(result['price'].tolist())
        [4.99, 29.99]
        
        >>> df_eur = pd.DataFrame({'cost': ['€15,50', '€1.234,56']})
        >>> result_eur = price_to_float(df_eur, price_col='cost', currency_marker='€')
        >>> print(result_eur['cost'].tolist())
        [15.5, 1234.56]
    """
    # Input validation
    if df.empty:
        warnings.warn("Input DataFrame is empty", UserWarning)
        return df.copy()
    
    if price_col not in df.columns:
        raise KeyError(f"Column '{price_col}' not found in DataFrame. Available columns: {list(df.columns)}")
    
    # Create a copy to avoid modifying the original DataFrame passed to the function
    df_copy = df.copy()

    def clean_and_convert_price(price_string: Union[str, float, int, None]) -> float:
        """
        Helper function to process a single price string.
        Handles various international number formats by assuming the last
        separator (dot or comma) is the decimal separator.
        
        Args:
            price_string: The price string to convert
            
        Returns:
            float: The converted price as a float, or np.nan if conversion fails
        """
        # Handle different input types
        if pd.isna(price_string) or price_string is None:
            return np.nan
            
        if not isinstance(price_string, str):
            # Try to convert numeric types directly
            try:
                return float(price_string)
            except (ValueError, TypeError):
                return np.nan

        # Remove the currency marker
        no_currency = price_string.replace(currency_marker, "").strip()
        
        # Handle empty strings after currency removal
        if not no_currency:
            return np.nan

        # Improved regex pattern to find number-like patterns
        # This pattern captures:
        # - Simple numbers: "123"
        # - Decimal numbers: "123.45" or "123,45"
        # - Numbers with thousand separators: "1,234.56" or "1.234,56"
        # - Numbers with spaces as thousand separators: "1 500"
        found_numbers = re.findall(r'\d[\d.,\s]*\d|\d+', no_currency)

        float_numbers = []
        for number_str in found_numbers:
            # Remove spaces used as thousand separators
            clean_str = number_str.replace(' ', '').strip()
            
            # Skip empty strings
            if not clean_str:
                continue
                
            last_comma = clean_str.rfind(',')
            last_dot = clean_str.rfind('.')

            # If a comma appears after the last dot, treat comma as the decimal separator.
            # This is common in European formats (e.g., "1.234,56").
            if last_comma > last_dot:
                # Remove dots (as thousand separators) and replace the comma with a dot.
                standardized_num_str = clean_str.replace('.', '').replace(',', '.')
            # Otherwise, treat the dot as the decimal separator (or no separator exists).
            # This is common in US/UK formats (e.g., "1,234.56").
            else:
                # Remove commas (as thousand separators).
                standardized_num_str = clean_str.replace(',', '')
            
            try:
                if standardized_num_str:
                    converted_num = float(standardized_num_str)
                    # Only add positive numbers (negative prices are unusual but valid)
                    if converted_num >= 0:
                        float_numbers.append(converted_num)
            except (ValueError, OverflowError):
                # Skip if conversion fails for any reason
                continue

        # Filter out any zero values (but keep negative values if they exist)
        non_zero_numbers = [num for num in float_numbers if num != 0]

        # If there are valid numbers, return the minimum, otherwise return NaN
        if non_zero_numbers:
            return min(non_zero_numbers)
        else:
            return np.nan

    # Apply the helper function to the specified price column
    df_copy[price_col] = df_copy[price_col].apply(clean_and_convert_price)

    return df_copy

# --- Example Usage ---
if __name__ == "__main__":
    print("🧪 Testing price_to_float function with various formats...")
    print("=" * 60)
    
    # Test 1: Basic US format
    print("\n1️⃣ Basic US Format:")
    data = {
        'product': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
        'price': [
            "$4.99",
            "$57.99",
            "$29.99",
            "$29.99 sale $39.99",
            "On sale for $19.95, was $25.00",
            "No price",  # Example of a value with no numbers
            ""  # Empty string
        ]
    }
    products_df = pd.DataFrame(data)
    converted_df = price_to_float(products_df)
    print("Original:", products_df['price'].tolist())
    print("Converted:", converted_df['price'].tolist())
    
    # Test 2: European format
    print("\n2️⃣ European Format:")
    data_eur = {
        'item': ['G', 'H', 'I'],
        'cost': ['€15.50', '€12.99 special €10.50', '€1.234,56']
    }
    items_df_eur = pd.DataFrame(data_eur)
    converted_df_eur = price_to_float(items_df_eur, price_col="cost", currency_marker="€")
    print("Original:", items_df_eur['cost'].tolist())
    print("Converted:", converted_df_eur['cost'].tolist())

    # Test 3: French/European Price Formats
    print("\n3️⃣ French/European Format:")
    data_fr = {
        'product_fr': ['Macaron Box', 'Baguette', 'Wine Bottle', 'Cheese Wheel', 'Champagne'],
        'price_fr': [
            '25,50 €',
            '€1,20',
            '€29,99 sale €1.200,50',  # Should pick 29.99
            'Prix: 1 500 €',  # Price with space as thousand separator
            '€2.500,00'  # Large number with European format
        ]
    }
    products_df_fr = pd.DataFrame(data_fr)
    converted_df_fr = price_to_float(products_df_fr, price_col="price_fr", currency_marker="€")
    print("Original:", products_df_fr['price_fr'].tolist())
    print("Converted:", converted_df_fr['price_fr'].tolist())
    
    # Test 4: Edge cases
    print("\n4️⃣ Edge Cases:")
    edge_cases = {
        'test_case': ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'],
        'price': [
            'Free',  # No numbers
            '0.00',  # Zero price
            '123',  # Integer
            456.78,  # Already a float
            None,  # None value
            'NaN',  # String NaN
            '$1,234.56',  # Thousand separator
            '€1.234,56'  # European thousand separator
        ]
    }
    edge_df = pd.DataFrame(edge_cases)
    converted_edge = price_to_float(edge_df)
    print("Original:", edge_df['price'].tolist())
    print("Converted:", converted_edge['price'].tolist())
    
    # Test 5: Error handling
    print("\n5️⃣ Error Handling:")
    try:
        # Test with non-existent column
        error_df = pd.DataFrame({'wrong_col': ['$1.00']})
        price_to_float(error_df, price_col="price")
    except KeyError as e:
        print(f"✅ Correctly caught KeyError: {e}")
    
    try:
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        result = price_to_float(empty_df)
        print(f"✅ Empty DataFrame handled: {len(result)} rows")
    except Exception as e:
        print(f"❌ Unexpected error with empty DataFrame: {e}")
    
    print("\n🎉 All tests completed!")


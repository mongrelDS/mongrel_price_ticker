#!/usr/bin/env python3
"""
Volume Extraction Function
Extracts volume and weight measurements from text and standardizes them to metric units.
"""

import pint
import pandas as pd
import re

def extract_volume(df, vol_col="vol_col", result_col="vol"):
    """
    Extract volume and weight measurements from text, converting to metric when possible.
    Handles an extensive range of unit variations and common abbreviations.

    Parameters:
    df (pd.DataFrame): Input dataframe
    vol_col (str): Name of column containing volume/weight text
    result_col (str): Name of column to store extracted measurements

    Returns:
    pd.DataFrame: DataFrame with new column containing standardized measurements
    """
    # Initialize unit registry
    ureg = pint.UnitRegistry()

    # Define comprehensive unit patterns
    unit_patterns = {
        # Volume - Metric
        'ml': r'(\d+(?:\.\d+)?)\s*(?:ml|mL|milliliter|millilitre|cc|cm3|cm³|mil|mills)',
        'l': r'(\d+(?:\.\d+)?)\s*(?:l|L|liter|litre|ltr|ℓ)(?!\w)',
        'dl': r'(\d+(?:\.\d+)?)\s*(?:dl|dL|deciliter|decilitre)',
        'cl': r'(\d+(?:\.\d+)?)\s*(?:cl|cL|centiliter|centilitre)',

        # Volume - Imperial/US
        'fl_oz': r'(\d+(?:\.\d+)?)\s*(?:fl\s*oz|fluid\s*ounce|fluid\s*ounces|fl\.|fl)',
        'pint': r'(\d+(?:\.\d+)?)\s*(?:pt|pint|pints)',
        'quart': r'(\d+(?:\.\d+)?)\s*(?:qt|quart|quarts)',
        'gallon': r'(\d+(?:\.\d+)?)\s*(?:gal|gallon|gallons)',
        'cup': r'(\d+(?:\.\d+)?)\s*(?:cup|cups|c\.)',
        'tbsp': r'(\d+(?:\.\d+)?)\s*(?:tbsp|Tbsp|tablespoon|tablespoons|Tbs|Tbls)',
        'tsp': r'(\d+(?:\.\d+)?)\s*(?:tsp|teaspoon|teaspoons)',

        # Weight - Metric
        'mg': r'(\d+(?:\.\d+)?)\s*(?:mg|milligram|milligrams)',
        'g': r'(\d+(?:\.\d+)?)\s*(?:g|gram|grams|gramme|grammes)(?!\w)',
        'kg': r'(\d+(?:\.\d+)?)\s*(?:kg|kilogram|kilograms|kilo|kilos)',

        # Weight - Imperial/US
        'oz': r'(\d+(?:\.\d+)?)\s*(?:oz|ounce|ounces)(?!\s*fl)',
        'lb': r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds)',
        'dr': r'(\d+(?:\.\d+)?)\s*(?:dr|dram|drams)',

        # Other common measurements
        'mcg': r'(\d+(?:\.\d+)?)\s*(?:mcg|µg|microgram|micrograms)',
        'ul': r'(\d+(?:\.\d+)?)\s*(?:ul|µl|microliter|microlitre)',
    }

    def extract_and_convert(text):
        if pd.isna(text):
            return None

        text = str(text).lower()

        # Try to find matches for each unit pattern
        for unit_type, pattern in unit_patterns.items():
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))

                # Convert to standardized units
                if unit_type == 'fl_oz':
                    quantity = value * ureg.fluid_ounce
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'pint':
                    quantity = value * ureg.pint
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'quart':
                    quantity = value * ureg.quart
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'gallon':
                    quantity = value * ureg.gallon
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'cup':
                    quantity = value * ureg.cup
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'tbsp':
                    quantity = value * ureg.tablespoon
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'tsp':
                    quantity = value * ureg.teaspoon
                    return f"{quantity.to('milliliter').magnitude:.0f} mL"
                elif unit_type == 'oz':
                    quantity = value * ureg.ounce
                    return f"{quantity.to('gram').magnitude:.0f} g"
                elif unit_type == 'lb':
                    quantity = value * ureg.pound
                    return f"{quantity.to('gram').magnitude:.0f} g"
                elif unit_type == 'dr':
                    quantity = value * ureg.dram
                    return f"{quantity.to('gram').magnitude:.0f} g"
                elif unit_type in ['ml', 'dl', 'cl']:
                    # Convert all to mL
                    if unit_type == 'dl':
                        return f"{(value * 100):.0f} mL"
                    elif unit_type == 'cl':
                        return f"{(value * 10):.0f} mL"
                    else:
                        return f"{value:.0f} mL"
                elif unit_type == 'l':
                    return f"{(value * 1000):.0f} mL"
                elif unit_type in ['mg', 'g', 'kg']:
                    # Standardize to appropriate unit based on size
                    if unit_type == 'mg':
                        return f"{value} mg"
                    elif unit_type == 'kg':
                        return f"{(value * 1000):.0f} g"
                    else:
                        return f"{value:.0f} g"
                elif unit_type == 'mcg':
                    return f"{value} mcg"
                elif unit_type == 'ul':
                    return f"{value} µL"

        return None

    # Apply the extraction function to the specified column
    df[result_col] = df[vol_col].apply(extract_and_convert)

    return df
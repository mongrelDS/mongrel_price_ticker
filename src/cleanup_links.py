# @title Generic URL Cleanup Function - Works with any domain

import pandas as pd


def cleanup_link(df, column_name="link", base_domain=None, add_html_suffix=True):
    """
    Cleans and standardizes URLs in a specified column by performing a multi-step process.

    Args:
        df (pd.DataFrame): The pandas DataFrame.
        column_name (str, optional): The name of the column containing the URLs to clean.
                                   Defaults to "link".
        base_domain (str, optional): The base domain to standardize URLs for. 
                                   If None, will auto-detect from the first URL in the column.
        add_html_suffix (bool, optional): Whether to add .html suffix to URLs that don't have it.
                                        Defaults to True.

    Returns:
        pd.DataFrame: The DataFrame with the cleaned URLs.
    """
    # --- Input validation ---
    if not isinstance(df, pd.DataFrame):
        print("Error: Input must be a pandas DataFrame.")
        return df

    if column_name not in df.columns:
        print(f"Error: Column '{column_name}' not found in DataFrame.")
        return df

    # --- Core Logic in a Helper Function ---
    try:
        def process_single_link(url):
            """Runs the full cleaning process on a single URL."""
            str_url = str(url).strip()
            
            # Skip empty or invalid URLs
            if not str_url or str_url.lower() in ['nan', 'none', '']:
                return str_url
            
            # Auto-detect base domain if not provided
            if base_domain is None:
                # Extract domain from URL
                if '://' in str_url:
                    domain_part = str_url.split('://')[1].split('/')[0]
                    detected_base = f"https://{domain_part}/"
                else:
                    detected_base = str_url
            else:
                detected_base = base_domain.rstrip('/') + '/'
                if not detected_base.startswith('http'):
                    detected_base = 'https://' + detected_base

            processed_url = str_url

            # Step 1: Standardize the path for the specified domain
            if str_url.startswith(detected_base):
                # Get everything after the base URL
                path_part = str_url[len(detected_base):]
                # The filename is the part after the last slash in the path
                filename = path_part.split('/')[-1]
                # Reconstruct the URL with just the base and the filename
                if filename:
                    processed_url = detected_base + filename

            # Step 2: Truncate any text after '.html' (handles query parameters)
            head, sep, tail = processed_url.partition('.html')
            if sep:
                truncated_url = head + sep
            else:
                truncated_url = processed_url

            # Step 3: Ensure the result has a '.html' suffix (if requested)
            if add_html_suffix and '.html' not in truncated_url and truncated_url != detected_base.rstrip('/'):
                final_url = truncated_url + '.html'
            else:
                final_url = truncated_url

            return final_url

        # Apply the cleaning function to the entire column
        df[column_name] = df[column_name].apply(process_single_link)
        return df

    except Exception as e:
        print(f"An error occurred: {e}")
        return df

# --- Usage Examples ---

# Example 1: Simplest usage - auto-detect domain, use default "link" column
# df_cleaned = cleanup_link(df_to_cleanup)

# Example 2: Specify a different column name
# df_cleaned = cleanup_link(df_to_cleanup, 'url')

# Example 3: Specify a specific domain
# df_cleaned = cleanup_link(df_to_cleanup, base_domain='https://www.healthyplanetcanada.com')

# Example 4: Don't add .html suffix
# df_cleaned = cleanup_link(df_to_cleanup, add_html_suffix=False)

# Example 5: For different domains
# df_cleaned = cleanup_link(df_to_cleanup, base_domain='https://www.example.com')
# df_cleaned = cleanup_link(df_to_cleanup, base_domain='www.another-site.com')  # Auto-adds https://
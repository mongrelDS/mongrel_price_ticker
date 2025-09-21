"""
Function to extract domain from URLs in a pandas DataFrame.

Example:
    When df['link'] contains 'https://www.healthyplanetcanada.com/products/1234567890'
    the domain should be 'healthyplanetcanada.com'
"""

from urllib.parse import urlparse


def get_domain(df, link_col='link'):
    """
    Extract domain from URLs in a pandas DataFrame column.
    
    Args:
        df (pandas.DataFrame): The DataFrame containing the URLs
        link_col (str): The name of the column containing URLs (default: 'link')
    
    Returns:
        pandas.DataFrame: The DataFrame with a new 'domain' column added
    
    Example:
        >>> df = pd.DataFrame({'link': ['https://www.example.com/page', 'https://test.org/path']})
        >>> result = get_domain(df)
        >>> print(result['domain'])
        0    www.example.com
        1    test.org
    """
    df['domain'] = df[link_col].apply(lambda x: urlparse(x).netloc)
    return df
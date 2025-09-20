import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import sys
sys.path.append('/home/mongreldatalab/mongrel_price_ticker/src')
from mySQL_Upsert_Function_with_Batch import upsert_df_to_mysql
from cleanup_column_names import clean_column_names

# Load environment variables from .env file
load_dotenv()

# --- 1. Database Connection Setup ---
# Get credentials from environment variables, with default values
db_host = os.getenv('DB_HOST', 'srv1978.hstgr.io')
db_user = os.getenv('DB_USER', 'u488367489_mongrel_data')
db_password = os.getenv('DB_PASSWORD', 'defaultpassword')
db_name = os.getenv('DB_NAME', 'u488367489_Price_Ticker')

# Create the database connection string for SQLAlchemy
connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"

# --- 2. Create DataFrame from SQL Query ---
try:
    # Create a database engine
    engine = create_engine(connection_string)

    # Define the SQL query to get the full details from each customer's first order.
    # We use a Common Table Expression (CTE) with a ROW_NUMBER() window function.
    # - PARTITION BY email: Groups the rows by customer email.
    # - ORDER BY order_date ASC: Sorts each customer's orders from oldest to newest.
    # - ROW_NUMBER() assigns a rank (1, 2, 3...) to each order. The first order gets rank 1.
    # Finally, we select only the rows where the rank (rn) is 1.
    query = """
    WITH RankedOrders AS (
        SELECT
            *,
            ROW_NUMBER() OVER(PARTITION BY email ORDER BY CAST(order_date AS DATE) ASC) as rn
        FROM
            natura_customer_orderlist
        WHERE
            order_date IS NOT NULL
    )
    SELECT
        email,
        customer_name,
        address_1,
        address_2,
        city,
        state,
        zip,
        country,
        phone,
        CAST(order_date AS DATE) AS first_order_date
    FROM
        RankedOrders
    WHERE
        rn = 1
    ORDER BY
        first_order_date;
    """

    # Execute the query and load the results directly into a pandas DataFrame
    df_customer_first_order = pd.read_sql_query(sql=text(query), con=engine)

    # Clean column names for consistency
    df_customer_first_order = clean_column_names(df_customer_first_order)

    upsert_df_to_mysql(df=df_customer_first_order,engine=engine,target_table='natura_customer_profile', key_col='email')

    # --- 3. Display Results ---
    print("✅ Successfully created the DataFrame 'df_customer_first_order'.")
    print("\nHere's a preview of the data, including address details from the first order:")
    print(df_customer_first_order.head()) # Display the first 5 rows

except Exception as e:
    print(f"❌ An error occurred: {e}")
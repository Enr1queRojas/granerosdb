import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError


# 1. Load variables from the .env file
load_dotenv()

_engine = None

def get_db_engine():
    """
    Creates and returns a SQLAlchemy engine for MSSQL
    using environment variables, optimized for remote connections.
    """
    global _engine
    if _engine is not None:
        return _engine

    # Load variables from environment
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "1433")
    db_name = os.getenv("DB_NAME")
    
    # Driver selection (Update to 'ODBC Driver 18' if version 17 is not installed)
    driver = "ODBC Driver 17 for SQL Server"

    # Connection URL formulation
    # Added Encrypt and TrustServerCertificate for stable remote IP connections
    connection_url = (
        f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db_name}"
        f"?driver={driver.replace(' ', '+')}"
        "&Encrypt=yes"
        "&TrustServerCertificate=yes"
    )

    try:
        engine = create_engine(
            connection_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            fast_executemany=True
        )

        # connection test
        with engine.connect() as conn:
            print(f"--- Connection to {host} established successfully ---")

        _engine = engine
        return engine

    except SQLAlchemyError as e:
        print(f"--- Critical Error: Could not connect to database: {e} ---")
        return None

    except SQLAlchemyError as e:
        print(f"--- Critical Error: Could not connect to database: {e} ---")
        return None

engine = get_db_engine()

def get_database_inventory():
    """
    Connects to the database and retrieves a complete inventory of 
    the schema, tables, and variables (columns).
    """
    # 1. Initialize the connection engine
    engine = get_db_engine()
    
    if not engine:
        print("--- Error: Could not establish engine connection. ---")
        return None

    # 2. Create the inspector object to read metadata
    inspector = inspect(engine)
    
    # 3. Retrieve schema information
    db_name = engine.url.database
    tables = inspector.get_table_names()
    
    inventory = {}

    print(f"--- Database Inventory: {db_name} ---")
    print(f"Total tables found: {len(tables)}\n")

    # 4. Loop through each table to extract variables
    for table_name in tables:
        columns_data = inspector.get_columns(table_name)
        
        # Store column names for the return dictionary
        column_names = [col['name'] for col in columns_data]
        inventory[table_name] = column_names
        
        # Detailed print for immediate inspection
        print(f"Table: {table_name}")
        for col in columns_data:
            # col['name'] = variable name, col['type'] = data type
            print(f"  - {col['name']} ({col['type']})")
        print("-" * 30)

    return inventory

def run_query(sql_query, description="Data"):
    """
    Executes a SQL query and returns a pandas DataFrame.
    :param sql_query: The SQL text or SQLAlchemy text() object.
    :param description: A label for printing status messages.
    :return: Pandas DataFrame or None if failed.
    """
    try:
        # 1. Ensure the query is wrapped in text() if it's a raw string
        if isinstance(sql_query, str):
            sql_query = text(sql_query)
            
        engine = get_db_engine()
        with engine.connect() as conn:
            df = pd.read_sql_query(sql_query, conn)
            
        # 2. Check and report status
        if df.empty:
            print(f"--- Warning: No records found for [{description}]. ---")
            return df
        else:
            print(f"--- Success: [{description}] retrieved with {len(df)} rows. ---")
            return df
            
    except Exception as e:
        print(f"--- Critical Error executing [{description}]: {e} ---")
        return None

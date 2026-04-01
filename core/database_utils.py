import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError


# 1. Load variables from the .env file
load_dotenv()

def get_db_engine():
    """
    Creates and returns a SQLAlchemy engine for MSSQL
    using environment variables, optimized for remote connections.
    """
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

        return engine

    except SQLAlchemyError as e:
        print(f"--- Critical Error: Could not connect to database: {e} ---")
        return None

    except SQLAlchemyError as e:
        print(f"--- Critical Error: Could not connect to database: {e} ---")
        return None

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

# --- Usage ---
# db_structure = get_database_inventory()
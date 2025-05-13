#!/usr/bin/env python3
"""
Creates and populates the ccr_reporting.db SQLite database with sample data.
"""

import sqlite3
import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define database path relative to this script's location
DB_DIR = Path(__file__).parent
DB_NAME = "ccr_reporting.db"
DB_PATH = DB_DIR / DB_NAME

# --- Sample Data ---

customer_data = [
    (1001, 'JPMorgan Chase & Co.', 'AA-', 'US', 'Interest-Rate Swap', 4500000000, '00021'),
    (1002, 'Bank of America Corp.', 'A+', 'US', 'FX Forward', 3800000000, '00106'),
    (1003, 'Citigroup Inc.', 'A', 'US', 'Equity Option', 3200000000, '00498'),
    (1004, 'Royal Bank of Canada', 'AA', 'CA', 'Interest-Rate Swap', 2100000000, '00003'),
    (1005, 'Toronto-Dominion Bank', 'AA-', 'CA', 'Commodity Swap', 1950000000, '00007'),
]

product_data = [
    ('P01', 'Interest-Rate Swap', 'Rates', 'High', 'USD', 'US', 20000000000),
    ('P02', 'FX Forward', 'FX', 'Medium', 'USD', 'US', 15000000000),
    ('P03', 'Equity Option', 'Equities', 'High', 'USD', 'US', 12000000000),
    ('P04', 'Credit Default Swap', 'Credit', 'Very High', 'USD', 'US', 10000000000),
    ('P05', 'Commodity Swap', 'Commodities', 'Medium', 'USD', 'US', 8000000000),
]

security_data = [
    ('AAPL', 'Apple Inc. Common', 'Equity', 180.25, 'USD', 'US', 'P03'),
    ('AMZN', 'Amazon.com Inc.', 'Equity', 145.60, 'USD', 'US', 'P03'),
    ('MSFT', 'Microsoft Corp.', 'Equity', 310.80, 'USD', 'US', 'P03'),
    ('TLT', 'iShares 20+ Yr UST', 'Rates ETF', 92.10, 'USD', 'US', 'P01'),
    ('XAUUSD', 'Gold Spot', 'Commodity', 2350.00, 'USD', None, 'P05'), # Assuming issuer_country is NULL for Spot
    ('EURUSD', 'Euro/US Dollar FX', 'FX', 1.08, 'USD', None, 'P02'), # Added for trade T0002
    ('USDJPY', 'US Dollar/Japanese Yen FX', 'FX', 150.0, 'USD', None, 'P02'), # Added for trade T0006
    ('GBPUSD', 'British Pound/US Dollar FX', 'FX', 1.25, 'USD', None, 'P02'), # Added for trade T0008
]

limits_data = [
    ('L001', 'Global IRS Limit', 'P01', 'NY_IRS', 18000000000, 90, 'USD'),
    ('L002', 'Global FX Limit', 'P02', 'NY_FX', 13000000000, 85, 'USD'),
    ('L003', 'Equity Deriv Limit', 'P03', 'TOR_EQD', 10000000000, 80, 'USD'),
    ('L004', 'CDS Desk Limit', 'P04', 'NY_CDS', 9000000000, 85, 'USD'),
    ('L005', 'Commodities Limit', 'P05', 'NY_COM', 7000000000, 90, 'USD'),
]

transit_mapping_data = [
    ('00021', 1001, 'NY_IRS', 'NYC Corporate', 'North America', 'CHASUS33XXX'),
    ('00106', 1002, 'NY_FX', 'Charlotte HQ', 'North America', 'BOFAUS3NXXX'),
    ('00498', 1003, 'NY_CDS', 'New York Citi', 'North America', 'CITIUS33XXX'),
    ('00003', 1004, 'TOR_EQD', 'Toronto HQ', 'North America', 'ROYCCAT2XXX'),
    ('00007', 1005, 'NY_COM', 'Bay Street Desk', 'North America', 'TDOMCATTTOR'),
]

trades_data = [
    ('T0001', 1001, 'P01', 'TLT', 2000000000, 25000000, 'NY_IRS', 2025000000, 'USD'),
    ('T0002', 1001, 'P02', 'EURUSD', 500000000, -1200000, 'NY_FX', 498800000, 'USD'),
    ('T0003', 1002, 'P03', 'AAPL', 1200000000, 45000000, 'TOR_EQD', 1245000000, 'USD'),
    ('T0004', 1003, 'P04', 'MSFT', 800000000, -12000000, 'NY_CDS', 788000000, 'USD'),
    ('T0005', 1004, 'P01', 'TLT', 900000000, 9500000, 'NY_IRS', 909500000, 'USD'),
    ('T0006', 1004, 'P02', 'USDJPY', 350000000, 2100000, 'NY_FX', 352100000, 'USD'),
    ('T0007', 1005, 'P05', 'XAUUSD', 600000000, 7200000, 'NY_COM', 607200000, 'USD'),
    ('T0008', 1002, 'P02', 'GBPUSD', 400000000, -900000, 'NY_FX', 399100000, 'USD'),
    ('T0009', 1003, 'P03', 'AMZN', 1000000000, 32000000, 'TOR_EQD', 1032000000, 'USD'),
    ('T0010', 1005, 'P01', 'TLT', 700000000, 6600000, 'NY_IRS', 706600000, 'USD'),
]

# --- Schema Definitions ---

# Using report_counterparties name as seen in previous logs
create_customer_table = """
CREATE TABLE IF NOT EXISTS report_counterparties (
    customer_id INTEGER PRIMARY KEY,
    customer_name TEXT,
    short_name TEXT, -- Added short_name as implied by failed query logs
    rating TEXT,
    country TEXT,
    primary_product TEXT,
    total_exposure_usd REAL,
    transit_no TEXT,
    FOREIGN KEY (transit_no) REFERENCES transit_mapping (transit_no)
);
"""
# Add short_name data generation later if needed

create_product_table = """
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    asset_class TEXT,
    risk_bucket TEXT,
    base_ccy TEXT,
    issuer_country TEXT,
    product_limit_usd REAL
);
"""

create_security_table = """
CREATE TABLE IF NOT EXISTS securities (
    ticker TEXT PRIMARY KEY,
    security_name TEXT,
    asset_class TEXT,
    current_price REAL,
    ccy TEXT,
    issuer_country TEXT,
    product_id TEXT,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);
"""

create_limits_table = """
CREATE TABLE IF NOT EXISTS limits (
    limit_id TEXT PRIMARY KEY,
    limit_name TEXT,
    product_id TEXT,
    desk_id TEXT,
    limit_amount_usd REAL,
    breach_threshold_pct INTEGER, -- Renamed for clarity
    ccy TEXT,
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);
"""

create_transit_mapping_table = """
CREATE TABLE IF NOT EXISTS transit_mapping (
    transit_no TEXT PRIMARY KEY,
    customer_id INTEGER,
    desk_id TEXT,
    branch_name TEXT,
    region TEXT,
    swift_code TEXT,
    FOREIGN KEY (customer_id) REFERENCES report_counterparties (customer_id)
);
"""

# Using report_daily_exposures name as seen in previous logs
create_trades_table = """
CREATE TABLE IF NOT EXISTS report_daily_exposures (
    trade_id TEXT PRIMARY KEY,
    report_date DATE, -- Added report_date as implied by failed query logs
    counterparty_id INTEGER, -- Changed from customer_id for consistency
    product_id TEXT,
    security_ticker TEXT,
    notional_usd REAL,
    mtm_usd REAL,
    desk_id TEXT,
    exposure_usd REAL,
    pfe_95_exposure REAL, -- Added pfe_95_exposure as implied by failed query logs
    currency TEXT, -- Changed from ccy for consistency
    FOREIGN KEY (counterparty_id) REFERENCES report_counterparties (customer_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id),
    FOREIGN KEY (security_ticker) REFERENCES securities (ticker)
);
"""
# Add report_date and pfe_95_exposure data generation later if needed

def create_and_populate_db():
    """Connects to the DB, creates tables, and inserts data."""
    conn = None
    try:
        logging.info(f"Connecting to database: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        logging.info("Dropping existing tables (if they exist)...")
        cursor.execute("DROP TABLE IF EXISTS report_daily_exposures;")
        cursor.execute("DROP TABLE IF EXISTS transit_mapping;")
        cursor.execute("DROP TABLE IF EXISTS limits;")
        cursor.execute("DROP TABLE IF EXISTS securities;")
        cursor.execute("DROP TABLE IF EXISTS products;")
        cursor.execute("DROP TABLE IF EXISTS report_counterparties;") # Changed table name

        logging.info("Creating tables...")
        cursor.execute(create_customer_table)
        cursor.execute(create_product_table)
        cursor.execute(create_security_table)
        cursor.execute(create_limits_table)
        cursor.execute(create_transit_mapping_table)
        cursor.execute(create_trades_table)

        logging.info("Inserting data...")

        # Customer data needs short_name added
        customer_data_with_short_name = []
        # Simple heuristic for short name (can be improved)
        for row in customer_data:
            parts = row[1].split()
            short_name = parts[0] if parts else 'Unknown'
            if len(parts) > 1 and parts[1].lower() not in ['of', '&', 'inc.', 'corp.']:
                 short_name = f"{parts[0]} {parts[1].replace('.', '').replace(',', '')}"
            customer_data_with_short_name.append(
                (row[0], row[1], short_name, row[2], row[3], row[4], row[5], row[6])
            )

        cursor.executemany("INSERT INTO report_counterparties (customer_id, customer_name, short_name, rating, country, primary_product, total_exposure_usd, transit_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", customer_data_with_short_name)
        cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?);", product_data)
        cursor.executemany("INSERT INTO securities VALUES (?, ?, ?, ?, ?, ?, ?);", security_data)
        cursor.executemany("INSERT INTO limits VALUES (?, ?, ?, ?, ?, ?, ?);", limits_data)
        cursor.executemany("INSERT INTO transit_mapping VALUES (?, ?, ?, ?, ?, ?);", transit_mapping_data)

        # Trades data needs report_date and pfe_95_exposure added
        from datetime import date
        today = date.today().isoformat()
        trades_data_full = []
        for row in trades_data:
            # Placeholder for PFE - needs actual calculation logic
            # Simple placeholder: 5% of exposure_usd or mtm_usd if positive, else 0
            pfe = max(0, row[7] * 0.05 if row[7] > 0 else 0)
            trades_data_full.append(
                 (row[0], today, row[1], row[2], row[3], row[4], row[5], row[6], row[7], pfe, row[8])
            )
        cursor.executemany("INSERT INTO report_daily_exposures (trade_id, report_date, counterparty_id, product_id, security_ticker, notional_usd, mtm_usd, desk_id, exposure_usd, pfe_95_exposure, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", trades_data_full)


        conn.commit()
        logging.info("Database created and populated successfully.")

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        if conn:
            conn.rollback() # Roll back changes on error
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    create_and_populate_db() 
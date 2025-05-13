import yfinance as yf
import sqlite3
import pandas as pd
import json
import logging
from datetime import datetime

# --- Configuration ---
DB_NAME = "financial_data.db"
TICKERS = ['AAPL', 'AMD', 'AMZN', 'ASML', 'CSCO', 'GOOGL', 'INTC', 'MSFT', 'MU', 'NVDA']
START_DATE = "2016-01-01"
END_DATE = "2020-08-31"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_connection(db_file):
    """ Create a database connection to the SQLite database specified by db_file """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        logging.info(f"SQLite DB connection successful to {db_file} (version {sqlite3.sqlite_version})")
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
    return conn

def create_tables(conn):
    """ Create tables in the SQLite database """
    cursor = conn.cursor()
    try:
        # Companies Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            ticker TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            summary TEXT,
            info_json TEXT
        );
        """)
        logging.info("Table 'companies' checked/created.")

        # Daily Stock Prices Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stock_prices (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            adj_close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES companies (ticker) ON DELETE CASCADE
        );
        """)
        logging.info("Table 'daily_stock_prices' checked/created.")

        # Dividends Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dividends (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            dividend_amount REAL,
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES companies (ticker) ON DELETE CASCADE
        );
        """)
        logging.info("Table 'dividends' checked/created.")

        # Stock Splits Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_splits (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            split_ratio TEXT,
            PRIMARY KEY (ticker, date),
            FOREIGN KEY (ticker) REFERENCES companies (ticker) ON DELETE CASCADE
        );
        """)
        logging.info("Table 'stock_splits' checked/created.")

        # Quarterly Income Statement Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_income_statement (
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL,  -- Using the index date from yfinance
            total_revenue REAL,
            cost_of_revenue REAL,
            gross_profit REAL,
            research_and_development REAL,
            selling_general_and_administrative REAL,
            operating_income REAL,
            net_interest_income REAL,
            other_income_expense REAL,
            pretax_income REAL,
            tax_provision REAL,
            net_income REAL,
            basic_eps REAL,
            diluted_eps REAL,
            -- Add other relevant fields as needed
            PRIMARY KEY (ticker, report_date),
            FOREIGN KEY (ticker) REFERENCES companies (ticker) ON DELETE CASCADE
        );
        """)
        logging.info("Table 'quarterly_income_statement' checked/created.")

        # Quarterly Balance Sheet Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quarterly_balance_sheet (
            ticker TEXT NOT NULL,
            report_date DATE NOT NULL, -- Using the index date from yfinance
            total_assets REAL,
            current_assets REAL,
            cash_and_cash_equivalents REAL,
            receivables REAL,
            inventory REAL,
            other_current_assets REAL,
            total_non_current_assets REAL,
            net_ppe REAL,
            goodwill_and_other_intangibles REAL,
            other_non_current_assets REAL,
            total_liabilities_net_minority_interest REAL,
            current_liabilities REAL,
            payables_and_accrued_expenses REAL,
            current_debt REAL,
            other_current_liabilities REAL,
            total_non_current_liabilities_net_minority_interest REAL,
            long_term_debt REAL,
            other_non_current_liabilities REAL,
            stockholders_equity REAL,
            -- Add other relevant fields as needed
            PRIMARY KEY (ticker, report_date),
            FOREIGN KEY (ticker) REFERENCES companies (ticker) ON DELETE CASCADE
        );
        """)
        logging.info("Table 'quarterly_balance_sheet' checked/created.")

        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Error creating tables: {e}")
    finally:
        if cursor:
            cursor.close()

# --- Main Population Logic (To be implemented) ---
def populate_data(conn, tickers, start_date, end_date):
    logging.info("Starting data population...")
    cursor = conn.cursor()

    for ticker_symbol in tickers:
        logging.info(f"Processing ticker: {ticker_symbol}...")
        try:
            ticker = yf.Ticker(ticker_symbol)

            # --- 1. Populate Companies Table ---
            try:
                info = ticker.info
                # Use .get() for safety
                cursor.execute("""
                INSERT OR REPLACE INTO companies (ticker, company_name, sector, industry, summary, info_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ticker_symbol,
                    info.get('longName'),
                    info.get('sector'),
                    info.get('industry'),
                    info.get('longBusinessSummary'), # Use longBusinessSummary if available
                    json.dumps(info) # Store full info as JSON
                ))
                logging.info(f"  Populated/Updated companies table for {ticker_symbol}.")
            except Exception as e:
                logging.warning(f"  Could not fetch or insert company info for {ticker_symbol}: {e}")
                # Insert just the ticker so foreign keys don't break
                cursor.execute("INSERT OR IGNORE INTO companies (ticker) VALUES (?)", (ticker_symbol,))


            # --- 2. Populate Daily Stock Prices ---
            try:
                # Adjust history call parameters if needed, e.g., auto_adjust=False might change columns
                hist_df = ticker.history(start=start_date, end=end_date, auto_adjust=True) # Ensure auto_adjust is True for simplicity
                
                if not hist_df.empty:
                    logging.debug(f"  Raw history columns for {ticker_symbol}: {hist_df.columns.tolist()}")
                    hist_df = hist_df.reset_index()
                    hist_df['ticker'] = ticker_symbol
                    # Ensure date format is YYYY-MM-DD
                    hist_df['Date'] = pd.to_datetime(hist_df['Date']).dt.strftime('%Y-%m-%d')
                    
                    # Define the mapping, check if columns exist before renaming/selecting
                    column_mapping = {
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        # 'Adj Close': 'adj_close', # yfinance standard with auto_adjust=True often uses just 'Close'
                        'Volume': 'volume'
                    }
                    
                    columns_to_insert = ['ticker']
                    columns_to_select = ['ticker']
                    
                    for source_col, db_col in column_mapping.items():
                        if source_col in hist_df.columns:
                            hist_df.rename(columns={source_col: db_col}, inplace=True)
                            columns_to_insert.append(db_col)
                            columns_to_select.append(db_col)
                        elif db_col == 'adj_close': # Handle adj_close specifically if needed (though usually covered by 'Close' w/ auto_adjust=True)
                             pass # Or attempt to calculate/find it differently if auto_adjust=False
                        else:
                             logging.warning(f"  Expected history column '{source_col}' not found for {ticker_symbol}.")
                             
                    # Add adj_close separately if Close exists (assuming auto_adjust=True means Close IS adj_close)
                    if 'close' in columns_to_insert:
                         hist_df['adj_close'] = hist_df['close']
                         columns_to_insert.append('adj_close')
                         columns_to_select.append('adj_close')
                    else:
                         # If even Close doesn't exist, add None
                         hist_df['adj_close'] = None
                         columns_to_insert.append('adj_close')
                         columns_to_select.append('adj_close')
                         

                    # Select only the columns needed for the DB
                    hist_df_selected = hist_df[columns_to_select]
                    
                    hist_data = hist_df_selected.values.tolist()
                    
                    placeholders = ", ".join(["?"] * len(columns_to_insert))
                    sql = f"INSERT OR IGNORE INTO daily_stock_prices ({', '.join(columns_to_insert)}) VALUES ({placeholders})"

                    cursor.executemany(sql, hist_data)
                    logging.info(f"  Populated daily_stock_prices for {ticker_symbol} ({len(hist_data)} rows).")
                else:
                    logging.warning(f"  No historical price data found for {ticker_symbol} in date range.")
            except Exception as e:
                 logging.warning(f"  Could not fetch or insert price data for {ticker_symbol}: {e}")
            
            # --- 3. Populate Dividends ---
            try:
                div_df = ticker.dividends
                if not div_df.empty:
                    div_df = div_df.reset_index()
                    div_df['ticker'] = ticker_symbol
                    div_df.rename(columns={'Date': 'date', 'Dividends': 'dividend_amount'}, inplace=True)
                     # Ensure date format is YYYY-MM-DD and filter
                    div_df['date'] = pd.to_datetime(div_df['date']).dt.strftime('%Y-%m-%d')
                    div_df_filtered = div_df[(div_df['date'] >= start_date) & (div_df['date'] <= end_date)]
                    
                    if not div_df_filtered.empty:
                        div_data = div_df_filtered[['ticker', 'date', 'dividend_amount']].values.tolist()
                        cursor.executemany("""
                        INSERT OR IGNORE INTO dividends (ticker, date, dividend_amount)
                        VALUES (?, ?, ?)
                        """, div_data)
                        logging.info(f"  Populated dividends for {ticker_symbol} ({len(div_data)} rows).")
                    else:
                        logging.info(f"  No dividends found for {ticker_symbol} in date range.")
                else:
                     logging.info(f"  No dividend data available for {ticker_symbol}.")
            except Exception as e:
                 logging.warning(f"  Could not fetch or insert dividend data for {ticker_symbol}: {e}")

            # --- 4. Populate Stock Splits ---
            try:
                split_df = ticker.splits
                if not split_df.empty:
                    split_df = split_df.reset_index()
                    split_df['ticker'] = ticker_symbol
                    split_df.rename(columns={'Date': 'date', 'Stock Splits': 'split_ratio'}, inplace=True)
                     # Ensure date format is YYYY-MM-DD and filter
                    split_df['date'] = pd.to_datetime(split_df['date']).dt.strftime('%Y-%m-%d')
                    split_df_filtered = split_df[(split_df['date'] >= start_date) & (split_df['date'] <= end_date)]
                    
                    if not split_df_filtered.empty:
                        # Convert ratio to string for storage
                        split_df_filtered['split_ratio'] = split_df_filtered['split_ratio'].astype(str) 
                        split_data = split_df_filtered[['ticker', 'date', 'split_ratio']].values.tolist()
                        cursor.executemany("""
                        INSERT OR IGNORE INTO stock_splits (ticker, date, split_ratio)
                        VALUES (?, ?, ?)
                        """, split_data)
                        logging.info(f"  Populated stock_splits for {ticker_symbol} ({len(split_data)} rows).")
                    else:
                        logging.info(f"  No stock splits found for {ticker_symbol} in date range.")
                else:
                     logging.info(f"  No stock split data available for {ticker_symbol}.")
            except Exception as e:
                 logging.warning(f"  Could not fetch or insert stock split data for {ticker_symbol}: {e}")

            # --- 5. Populate Quarterly Income Statement ---
            try:
                q_income_df = ticker.quarterly_financials
                if not q_income_df.empty:
                    q_income_df = q_income_df.T # Transpose
                    q_income_df = q_income_df.reset_index()
                    q_income_df['ticker'] = ticker_symbol
                    q_income_df.rename(columns={'index': 'report_date'}, inplace=True)
                    q_income_df['report_date'] = pd.to_datetime(q_income_df['report_date']).dt.strftime('%Y-%m-%d')
                    
                    # Select and rename columns, handle missing ones gracefully
                    db_columns = {
                        'Total Revenue': 'total_revenue',
                        'Cost Of Revenue': 'cost_of_revenue',
                        'Gross Profit': 'gross_profit',
                        'Research And Development': 'research_and_development',
                        'Selling General And Administration': 'selling_general_and_administrative',
                        'Operating Income': 'operating_income',
                        'Net Interest Income': 'net_interest_income',
                        'Other Income Expense': 'other_income_expense',
                        'Pretax Income': 'pretax_income',
                        'Tax Provision': 'tax_provision',
                        'Net Income': 'net_income',
                        'Basic EPS': 'basic_eps',
                        'Diluted EPS': 'diluted_eps'
                    }
                    
                    columns_to_insert = ['ticker', 'report_date']
                    final_data = []
                    df_renamed = q_income_df.rename(columns=db_columns)
                    
                    for db_col in db_columns.values():
                        if db_col in df_renamed.columns:
                            columns_to_insert.append(db_col)
                        else:
                            df_renamed[db_col] = None # Add missing column with None
                            columns_to_insert.append(db_col)
                    
                    # Convert to list of tuples
                    income_data = df_renamed[columns_to_insert].astype(object).where(pd.notnull(df_renamed), None).values.tolist()

                    placeholders = ", ".join(["?"] * len(columns_to_insert))
                    sql = f"INSERT OR IGNORE INTO quarterly_income_statement ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
                    
                    cursor.executemany(sql, income_data)
                    logging.info(f"  Populated quarterly_income_statement for {ticker_symbol} ({len(income_data)} rows).")
                else:
                     logging.info(f"  No quarterly income data available for {ticker_symbol}.")
            except Exception as e:
                 logging.warning(f"  Could not fetch or insert quarterly income data for {ticker_symbol}: {e}")
            
            # --- 6. Populate Quarterly Balance Sheet ---
            try:
                q_balance_df = ticker.quarterly_balance_sheet
                if not q_balance_df.empty:
                    q_balance_df = q_balance_df.T # Transpose
                    q_balance_df = q_balance_df.reset_index()
                    q_balance_df['ticker'] = ticker_symbol
                    q_balance_df.rename(columns={'index': 'report_date'}, inplace=True)
                    q_balance_df['report_date'] = pd.to_datetime(q_balance_df['report_date']).dt.strftime('%Y-%m-%d')
                    
                    # Select and rename columns
                    db_columns = {
                        'Total Assets': 'total_assets',
                        'Current Assets': 'current_assets',
                        'Cash And Cash Equivalents': 'cash_and_cash_equivalents',
                        'Receivables': 'receivables',
                        'Inventory': 'inventory',
                        'Other Current Assets': 'other_current_assets',
                        'Total Non Current Assets': 'total_non_current_assets',
                        'Net PPE': 'net_ppe',
                        'Goodwill And Other Intangible Assets': 'goodwill_and_other_intangibles',
                        'Other Non Current Assets': 'other_non_current_assets',
                        'Total Liabilities Net Minority Interest': 'total_liabilities_net_minority_interest',
                        'Current Liabilities': 'current_liabilities',
                        'Payables And Accrued Expenses': 'payables_and_accrued_expenses',
                        'Current Debt': 'current_debt',
                        'Other Current Liabilities': 'other_current_liabilities',
                        'Total Non Current Liabilities Net Minority Interest': 'total_non_current_liabilities_net_minority_interest',
                        'Long Term Debt': 'long_term_debt',
                        'Other Non Current Liabilities': 'other_non_current_liabilities',
                        'Stockholders Equity': 'stockholders_equity'
                    }
                    
                    columns_to_insert = ['ticker', 'report_date']
                    final_data = []
                    df_renamed = q_balance_df.rename(columns=db_columns)
                    
                    for db_col in db_columns.values():
                        if db_col in df_renamed.columns:
                            columns_to_insert.append(db_col)
                        else:
                            df_renamed[db_col] = None
                            columns_to_insert.append(db_col)
                            
                    balance_data = df_renamed[columns_to_insert].astype(object).where(pd.notnull(df_renamed), None).values.tolist()

                    placeholders = ", ".join(["?"] * len(columns_to_insert))
                    sql = f"INSERT OR IGNORE INTO quarterly_balance_sheet ({', '.join(columns_to_insert)}) VALUES ({placeholders})"
                    
                    cursor.executemany(sql, balance_data)
                    logging.info(f"  Populated quarterly_balance_sheet for {ticker_symbol} ({len(balance_data)} rows).")
                else:
                     logging.info(f"  No quarterly balance sheet data available for {ticker_symbol}.")
            except Exception as e:
                 logging.warning(f"  Could not fetch or insert quarterly balance sheet data for {ticker_symbol}: {e}")

            # Commit after processing each ticker
            conn.commit()
            logging.info(f"Committed data for {ticker_symbol}.")

        except Exception as e:
            logging.error(f"Failed processing ticker {ticker_symbol}: {e}")
            conn.rollback() # Rollback if major error for a ticker
        finally:
            if cursor:
                # No, keep cursor open for the loop
                pass

    logging.info("Data population finished.")
    if cursor:
        cursor.close() # Close cursor at the very end


# --- Verification (Optional) ---
def verify_data(conn):
    logging.info("Verifying data...")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT count(*) FROM companies")
        logging.info(f"  Total companies: {cursor.fetchone()[0]}")
        cursor.execute("SELECT ticker, count(*) FROM daily_stock_prices GROUP BY ticker")
        logging.info(f"  Stock price rows per ticker: {cursor.fetchall()}")
        cursor.execute("SELECT count(*) FROM quarterly_income_statement")
        logging.info(f"  Total quarterly income rows: {cursor.fetchone()[0]}")
        cursor.execute("SELECT count(*) FROM quarterly_balance_sheet")
        logging.info(f"  Total quarterly balance sheet rows: {cursor.fetchone()[0]}")
    except sqlite3.Error as e:
        logging.error(f"Error verifying data: {e}")
    finally:
        if cursor:
            cursor.close()

# --- Main Execution ---
if __name__ == "__main__":
    conn = create_connection(DB_NAME)
    if conn is not None:
        create_tables(conn)
        populate_data(conn, TICKERS, START_DATE, END_DATE)
        verify_data(conn)
        conn.close()
        logging.info("Database connection closed.")
    else:
        logging.error("Database connection failed. Exiting.") 
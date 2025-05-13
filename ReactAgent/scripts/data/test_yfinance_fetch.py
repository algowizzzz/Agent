import yfinance as yf
import pandas as pd

# --- Configuration ---
tickers_to_test = ['AAPL', 'NVDA']
start_date = "2020-01-01"
# Use a slightly later end date to ensure the last day is included if needed
end_date = "2020-09-01" 

# Display options for pandas
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print(f"--- Testing yfinance data fetch for {tickers_to_test} from {start_date} to {end_date} ---")

for ticker_symbol in tickers_to_test:
    print(f"\n{'='*20} Fetching data for: {ticker_symbol} {'='*20}")
    try:
        ticker = yf.Ticker(ticker_symbol)

        # 1. Company Info (Dictionary)
        print("\n1. Company Info (.info):")
        info = ticker.info
        # Print selected keys for brevity
        selected_info = {
            k: info.get(k, 'N/A') for k in 
            ['symbol', 'longName', 'sector', 'industry', 'marketCap', 'previousClose', 'businessSummary']
        }
        print(selected_info)
        print("-"*50)

        # 2. Historical Prices (DataFrame)
        print(f"\n2. Historical Prices (.history from {start_date} to {end_date}):")
        hist = ticker.history(start=start_date, end=end_date)
        print(hist)
        print("-"*50)

        # 3. Dividends (Series/DataFrame)
        print(f"\n3. Dividends (.dividends from {start_date} to {end_date}):")
        dividends = ticker.dividends
        if not dividends.empty:
            # Filter dividends within the date range
            dividends_filtered = dividends[(dividends.index >= start_date) & (dividends.index < end_date)]
            print(dividends_filtered)
        else:
            print(f"No dividend data available for {ticker_symbol}.")
        print("-"*50)

        # 4. Stock Splits (Series/DataFrame)
        print(f"\n4. Stock Splits (.splits from {start_date} to {end_date}):")
        splits = ticker.splits
        if not splits.empty:
            # Filter splits within the date range
            splits_filtered = splits[(splits.index >= start_date) & (splits.index < end_date)]
            print(splits_filtered)
        else:
            print(f"No split data available for {ticker_symbol}.")
        print("-"*50)

        # 5. Quarterly Financials (Income Statement - DataFrame)
        print("\n5. Quarterly Financials (.quarterly_financials):")
        q_financials = ticker.quarterly_financials
        if not q_financials.empty:
            print(q_financials.T) # Transpose for better readability
        else:
             print(f"No quarterly financials data available for {ticker_symbol}.")
        print("-"*50)
        
        # 6. Quarterly Balance Sheet (DataFrame)
        print("\n6. Quarterly Balance Sheet (.quarterly_balance_sheet):")
        q_balance_sheet = ticker.quarterly_balance_sheet
        if not q_balance_sheet.empty:
            print(q_balance_sheet.T) # Transpose for better readability
        else:
            print(f"No quarterly balance sheet data available for {ticker_symbol}.")
        print("-"*50)

    except Exception as e:
        print(f"\n*** ERROR fetching data for {ticker_symbol}: {e} ***")

print("\n--- Test Finished ---") 
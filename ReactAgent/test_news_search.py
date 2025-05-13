#!/usr/bin/env python3

import os
import sys
import logging
from langchain_tools.tool_factory import create_financial_news_search_tool

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test the financial_news_search tool directly"""
    
    # Check if SERPAPI_API_KEY is set
    if not os.getenv("SERPAPI_API_KEY"):
        logger.error("SERPAPI_API_KEY environment variable is not set!")
        print("Please set the SERPAPI_API_KEY environment variable before running this script.")
        return
    
    # Create the financial news search tool
    logger.info("Creating financial_news_search tool...")
    financial_news_tool = create_financial_news_search_tool()
    
    # Get query from command line or use default
    query = "Microsoft MSFT Q2 2023 earnings site:finance.yahoo.com" if len(sys.argv) < 2 else sys.argv[1]
    
    # Run the query
    logger.info(f"Running query: {query}")
    try:
        result = financial_news_tool.func(query)
        logger.info("Query executed successfully!")
        print("\n--- Search Results ---")
        print(result)
    except Exception as e:
        logger.error(f"Error executing query: {e}", exc_info=True)
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 
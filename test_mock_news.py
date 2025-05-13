#!/usr/bin/env python3
"""
Test script for the enhanced financial news tool with mock news provider.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

# Import the financial news tool
from tools.financial_news_tool import run_financial_news_search

def test_news_search():
    """Test the financial news search with various queries."""
    
    # Test queries that target specific mock data
    test_queries = [
        "Tell me about Apple's latest watch strategy",
        "Microsoft's recent cloud performance",
        "Federal Reserve interest rate changes",
        "General market outlook for tech stocks"
    ]
    
    print("\n===== TESTING MOCK NEWS PROVIDER =====\n")
    
    # Ensure we don't have a SERPAPI key for this test
    if "SERPAPI_API_KEY" in os.environ:
        original_key = os.environ["SERPAPI_API_KEY"]
        del os.environ["SERPAPI_API_KEY"]
        print("Temporarily removed SERPAPI_API_KEY from environment for testing")
    else:
        original_key = None
        print("No SERPAPI_API_KEY found in environment, mock provider will be used")
    
    # Run tests for each query
    for i, query in enumerate(test_queries, 1):
        print(f"\n----- Test Query {i}: '{query}' -----\n")
        
        try:
            result = run_financial_news_search(query)
            print(result)
        except Exception as e:
            print(f"ERROR: {type(e).__name__}: {e}")
    
    # Restore the original API key if it existed
    if original_key:
        os.environ["SERPAPI_API_KEY"] = original_key
        print("\nRestored original SERPAPI_API_KEY to environment")
    
    print("\n===== TESTING COMPLETE =====\n")

if __name__ == "__main__":
    test_news_search() 
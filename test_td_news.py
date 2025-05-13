#!/usr/bin/env python3
"""
Test script for the JSON-only Financial News Tool with TD Bank queries
"""

from tools.financial_news_tool import run_financial_news_search

def test_td_news_search():
    print("\n=============== TESTING JSON-ONLY NEWS TOOL WITH TD BANK QUERIES ===============")
    
    # Test with simple TD Bank query
    query = "TD Bank"
    print(f"\nQuery: '{query}'")
    print("Results:")
    results = run_financial_news_search(query)
    print(results)
    
    # Test with TD Bank downgrade query
    query = "TD Bank downgrade"
    print(f"\nQuery: '{query}'")
    print("Results:")
    results = run_financial_news_search(query)
    print(results)
    
    # Test with TD Bank governance query
    query = "TD Bank governance AML"
    print(f"\nQuery: '{query}'")
    print("Results:")
    results = run_financial_news_search(query)
    print(results)
    
    print("\n============== JSON-ONLY NEWS TOOL TEST COMPLETE ==============")

if __name__ == "__main__":
    test_td_news_search() 
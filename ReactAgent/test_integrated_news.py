#!/usr/bin/env python3
"""
Test script for integrated financial news tool with JSON file support
"""

import logging
import os
import sys
from tools.financial_news_tool import run_financial_news_search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def color_print(text, color):
    """Print colored text to terminal."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def main():
    """
    Test the integrated financial news tool.
    """
    color_print("===== INTEGRATED FINANCIAL NEWS TOOL TEST =====", "blue")
    
    # Test queries
    test_queries = [
        "bank downgrade news",
        "China rating"
    ]
    
    # Test with JSON mode enabled
    color_print("\n1. Testing with JSON mode enabled:", "cyan")
    for query in test_queries:
        color_print(f"\nQuery: '{query}'", "yellow")
        results = run_financial_news_search(query, json_mode=True)
        print(results[:500] + "..." if len(results) > 500 else results)
    
    # Test with fallback to JSON mode
    color_print("\n2. Testing with fallback to JSON mode:", "cyan")
    for query in test_queries:
        color_print(f"\nQuery: '{query}'", "yellow")
        results = run_financial_news_search(query)  # json_mode=False is default
        print(results[:500] + "..." if len(results) > 500 else results)
    
    # Test with custom JSON file path (which doesn't exist)
    color_print("\n3. Testing with non-existent JSON file (should fall back to mock):", "cyan")
    query = "bank news"
    color_print(f"\nQuery: '{query}'", "yellow")
    results = run_financial_news_search(query, json_mode=True, json_file_path="nonexistent.json")
    print(results[:500] + "..." if len(results) > 500 else results)
    
    color_print("\n===== TEST COMPLETE =====", "blue")

if __name__ == "__main__":
    main() 
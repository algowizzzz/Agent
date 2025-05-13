#!/usr/bin/env python3
"""
Test script for JSON-based financial news tool
"""

import logging
import os
import sys
from tools.json_news_tool import run_json_news_search, JsonFileNewsProvider

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
    Run tests for the JSON news tool.
    """
    color_print("===== JSON NEWS TOOL TEST =====", "blue")
    
    # Test with different queries
    test_queries = [
        "bank downgrade news",
        "Moody's",
        "China credit rating",
        "TD Bank governance",
        "commercial real estate risk"
    ]
    
    color_print("\n1. Testing JsonFileNewsProvider initialization and loading:", "cyan")
    provider = JsonFileNewsProvider()
    color_print(f"  Loaded {len(provider.news_data)} articles from JSON file", "green")
    
    color_print("\n2. Testing news search functionality with different queries:", "cyan")
    for query in test_queries:
        color_print(f"\nQuery: '{query}'", "yellow")
        results = provider.search(query)
        color_print(f"  Found {len(results)} matching articles", "green")
        
        # Print result titles for reference
        if results:
            for i, result in enumerate(results, 1):
                color_print(f"  {i}. {result.get('title', 'Untitled')}", "green")
        else:
            color_print("  No matches found", "red")
    
    color_print("\n3. Testing the full workflow with run_json_news_search:", "cyan")
    query = "bank ratings downgrades"
    color_print(f"Query: '{query}'", "yellow")
    formatted_results = run_json_news_search(query)
    print(formatted_results)
    
    color_print("\n===== TEST COMPLETE =====", "blue")

if __name__ == "__main__":
    main() 
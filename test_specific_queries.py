#!/usr/bin/env python3
"""
Test script for specific queries, showing top 3 results with scores
"""

import logging
from document_level_search import semantic_document_search

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test queries from user
TEST_QUERIES = [
    "q1 2017 aapl",
    "q3 2018 msft",
    "q4 2017 amzn",
    "amzn and nvidia 2017 growth comparison"
]

def run_test_queries():
    """Run test queries and display top 3 results with scores"""
    for query in TEST_QUERIES:
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}")
        
        # Run search limiting to top 3 results
        results = semantic_document_search(query, max_results=3)
        
        if results:
            print(f"Found {len(results)} results (showing top 3):")
            
            for i, result in enumerate(results):
                print(f"\n{i+1}. {result['document_name']}")
                print(f"   Company: {result['ticker']}")
                print(f"   Similarity: {result['similarity']}")
                if 'excerpt' in result and result['excerpt']:
                    excerpt = result['excerpt']
                    if len(excerpt) > 150:
                        excerpt = excerpt[:150] + "..."
                    print(f"   Excerpt: {excerpt}")
        else:
            print("No results found.")
        
        print(f"\n{'-'*80}")

if __name__ == "__main__":
    run_test_queries() 
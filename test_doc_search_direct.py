#!/usr/bin/env python3
"""
Simplified test script that directly tests the document search functionality
without needing an API key
"""

import logging
from tools.earnings_call_tool import create_doc_level_search_wrapper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test query
test_query = "What were Apple's iPhone revenues in Q1 2020?"

def run_test():
    """Run the test with just the document search wrapper"""
    logger.info(f"Testing document search with query: {test_query}")
    
    # Call the document search wrapper directly
    result = create_doc_level_search_wrapper(test_query)
    
    # Print the result
    print("\n" + "="*80)
    print(f"QUERY: {test_query}")
    print("="*80)
    if "result" in result:
        print(result["result"])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_test() 
#!/usr/bin/env python3
"""
Direct search for Microsoft Q1 2017 earnings documents
"""

import logging
import json
import re
from final_document_level_search import semantic_document_search

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_direct_search():
    """Run a direct search for Microsoft Q1 2017 earnings documents"""
    
    # Define specific queries targeting Q1 2017
    search_queries = [
        "Microsoft Q1 2017 earnings call transcript",
        "MSFT Q1 2017 financial results",
        "Microsoft first quarter 2017 earnings call",
        "Microsoft earnings October 2016",  # Q1 of fiscal 2017 would be reported in Oct 2016
        "Microsoft Q1 fiscal 2017 revenue"
    ]
    
    # Run each search query
    for query in search_queries:
        print(f"\n{'=' * 80}")
        print(f"SEARCH QUERY: {query}")
        print(f"{'=' * 80}")
        
        # Call the search directly with correct parameter name
        results = semantic_document_search(query, max_results=10)
        
        # Process and display results
        if not results or len(results) == 0:
            print("No documents found for this query.")
            continue
            
        # Print found documents
        print(f"Found {len(results)} documents:")
        for i, doc in enumerate(results, 1):
            print(f"\n{i}. {doc.get('document_name', 'Unnamed document')} ({doc.get('ticker', 'Unknown')})")
            print(f"   Document ID: {doc.get('document_id', 'No ID')}")
            print(f"   Similarity: {doc.get('similarity', 'Unknown')}")
            
            # If we have a date, print it
            date_match = re.search(r'\((\d{4}-\d{2}-\d{2})\)', doc.get('document_name', ''))
            if date_match:
                print(f"   Date: {date_match.group(1)}")
            
            # Print excerpt if available
            if "excerpt" in doc and len(doc["excerpt"]) > 0:
                excerpt = doc["excerpt"]
                # Truncate if too long
                if len(excerpt) > 200:
                    excerpt = excerpt[:200] + "..."
                print(f"   Excerpt: {excerpt}")

if __name__ == "__main__":
    run_direct_search() 
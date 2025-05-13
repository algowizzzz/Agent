#!/usr/bin/env python3
"""
Script to test the Document Tool directly.
"""

import os
import sys
import argparse
import json
import logging
from langchain_tools.tool3_document import get_tool # Import from tool3
from bson import json_util # Import for handling potential BSON types in output if needed

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test(query: str, doc_ids: list):
    """Runs the document tool with the given inputs."""
    logger.info(f"Testing Document Tool with Query: '{query}' and Document IDs: {doc_ids}")
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)
        
    try:
        # Get the document tool function
        document_tool_fn = get_tool(api_key)
        
        # Call the tool function directly
        # Ensure doc_ids are passed as a list of strings
        result = document_tool_fn(query=query, doc_ids=[str(d) for d in doc_ids])
        
        print("\n--- Document Tool Result ---")
        # Use json.dumps with json_util.default for pretty printing potentially complex dicts
        print(json.dumps(result, indent=2, default=json_util.default))
        print("--------------------------")
        
    except Exception as e:
        logger.error(f"An error occurred during tool execution: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Document Tool Directly")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    parser.add_argument("-d", "--doc_ids", required=True, nargs='+', help="One or more document_id strings.")
    
    args = parser.parse_args()
    
    run_test(args.query, args.doc_ids) 
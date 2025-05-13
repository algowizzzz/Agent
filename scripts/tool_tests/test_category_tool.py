#!/usr/bin/env python3
"""
Script to test the Category Summary Tool directly.
"""

import os
import sys
import argparse
import json
import logging
from langchain_tools.tool2_category import category_summary_tool # Import the specific tool function

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_category_test(query: str, category_id: str):
    """Runs the category summary tool with the given query and category ID."""
    logger.info(f"Testing Category Summary Tool with Query: '{query}' and Category ID: '{category_id}'")

    # Check for API key (needed by the LLM inside the tool)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    try:
        # Call the category tool function directly
        # Note: The tool function itself handles DB connection and LLM initialization
        result = category_summary_tool(query=query, category_id=category_id)

        print("\n--- Category Summary Tool Result ---")
        # Use standard json.dumps as output doesn't contain datetime objects
        print(json.dumps(result, indent=2))
        print("------------------------------------")

    except Exception as e:
        logger.error(f"An error occurred during category tool execution: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Category Summary Tool Directly")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    parser.add_argument("-c", "--category", required=True, help="The category ID (e.g., company ticker) to query.")

    args = parser.parse_args()

    run_category_test(args.query, args.category) 
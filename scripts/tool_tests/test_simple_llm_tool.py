#!/usr/bin/env python3
"""
Script to test the Simple LLM Tool directly.
"""

import os
import sys
import argparse
import json
import logging
from langchain_tools.tool5_simple_llm import get_tool # Import from tool5

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test(query: str):
    """Runs the simple LLM tool with the given query."""
    logger.info(f"Testing Simple LLM Tool with Query: '{query}'")
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)
        
    try:
        # Get the simple LLM tool function
        simple_llm_tool_fn = get_tool(api_key)
        
        # Call the tool function directly
        result = simple_llm_tool_fn(query=query)
        
        print("\n--- Simple LLM Tool Result ---")
        print(json.dumps(result, indent=2))
        print("-----------------------------")
        
    except Exception as e:
        logger.error(f"An error occurred during tool execution: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Simple LLM Tool Directly")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    
    args = parser.parse_args()
    
    run_test(args.query) 
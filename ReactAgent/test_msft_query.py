#!/usr/bin/env python3
"""
Test script for specific Microsoft Q1 2017 revenue query
"""

import os
import logging
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from tools.earnings_call_tool import run_transcript_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test query for Microsoft Q1 2017 revenue
TEST_QUERY = "What was Microsoft's Q1 2017 revenue and key insights in few lines?"

def run_test():
    """Run the test with a specific Microsoft query"""
    logger.info(f"Testing earnings call tool with query: {TEST_QUERY}")
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable is not set")
        return
    
    try:
        # Create LLM
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0,
            anthropic_api_key=api_key
        )
        
        # Call the earnings call tool
        logger.info("Calling earnings call transcript analysis tool...")
        response = run_transcript_agent(TEST_QUERY, llm, api_key)
        
        # Print the response
        logger.info("Response received:")
        print("\n" + "=" * 80)
        print(f"QUERY: {TEST_QUERY}")
        print("=" * 80)
        print(response)
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Error running test: {e}", exc_info=True)

if __name__ == "__main__":
    run_test() 
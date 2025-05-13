#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Tool Import ---
# Import the factory function for the tool
try:
    from langchain_tools.tool_factory import create_financial_news_search_tool
except ImportError as e:
    logger.error(f"Failed to import tool factory: {e}. Ensure langchain_tools is in Python path.")
    sys.exit(1)

def run_test(query: str):
    """Runs the financial news search tool with the given query."""
    logger.info(f"Testing financial_news_search tool with query: '{query}'")

    # Load environment variables (especially SERPAPI_API_KEY)
    load_dotenv() 
    
    # Check if the key is loaded (optional but good practice)
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        logger.error("SERPAPI_API_KEY not found in environment variables.")
        logger.error("Please ensure it's set in your .env file or system environment.")
        # Optionally provide the key you received here for immediate use, but warn again
        # logger.warning("Using API key provided in conversation - remember to set it securely.")
        # api_key = "757846c69f7c8e278cc33deca4522bc0b2cdcdcf89290d65e066a0dd8e054c00" 
        # os.environ["SERPAPI_API_KEY"] = api_key # Temporarily set for this run
        # if not api_key: # Check again if fallback failed
        #      sys.exit(1) # Exit if key is still missing

    try:
        # Create the tool instance
        news_tool = create_financial_news_search_tool()
        logger.info(f"Tool created: {news_tool.name} - {news_tool.description[:100]}...")
        
        # Run the tool
        logger.info("Running tool...")
        result = news_tool.run(query)
        
        # Print the results
        logger.info("--- Tool Result ---")
        print(result)
        logger.info("--- End of Result ---")

    except ImportError as e:
         # Specific check for google-search-results dependency
         if "google-search-results" in str(e):
              logger.error("Missing dependency: Please install 'google-search-results' package.")
              logger.error("Run: pip install google-search-results")
         else:
              logger.error(f"An import error occurred: {e}")
         sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred while running the tool: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Financial News Search Tool")
    parser.add_argument("-q", "--query", required=True, help="The search query for the news tool.")
    args = parser.parse_args()
    
    run_test(args.query) 
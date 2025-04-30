# Wrapper for financial news search
import logging
import os
import json
from typing import Union, List, Dict

# Assuming SerpAPIWrapper is the intended tool
# Handle potential ImportError
try:
    from langchain_community.utilities import SerpAPIWrapper
except ImportError:
    SerpAPIWrapper = None # Set to None if import fails

logger = logging.getLogger(__name__)

def run_financial_news_search(query: str) -> str:
    """
    Performs a web search using the provided query and returns formatted results.
    Handles potential API key errors and missing dependencies.
    Returns results as a string or an error message string.
    """
    logger.info(f"[Financial News Tool] Executing web search for query: {query}")

    if SerpAPIWrapper is None:
        error_msg = "Error: SerpAPIWrapper dependency not installed. Run `pip install google-search-results`."
        logger.error(error_msg)
        return error_msg
    
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_api_key:
        error_msg = "Error: SERPAPI_API_KEY environment variable not set."
        logger.error(error_msg)
        return error_msg

    try:
        search = SerpAPIWrapper(serpapi_api_key=serpapi_api_key)
        results: Union[str, List, Dict] = search.run(query)

        # Format results consistently as a string
        if isinstance(results, list):
            # Format list of strings or dicts
            formatted_results = []
            for item in results:
                if isinstance(item, dict):
                    # Basic formatting for dict items
                    item_str = f"Title: {item.get('title', 'N/A')}, Snippet: {item.get('snippet', 'N/A')}, Link: {item.get('link', 'N/A')}"
                    formatted_results.append(item_str)
                else:
                    formatted_results.append(str(item))
            return "\n".join(formatted_results)
        elif isinstance(results, dict):
            # Try to extract common fields or just dump JSON
            if 'answer_box' in results:
                 return json.dumps(results['answer_box'], indent=2)
            elif 'organic_results' in results and results['organic_results']:
                 return json.dumps(results['organic_results'][0], indent=2) # Example: first result
            else:
                 return json.dumps(results, indent=2)
        else:
            # Assume it's already a string or can be converted
            return str(results)

    except Exception as e:
        logger.error(f"[Financial News Tool] Error during web search: {e}", exc_info=True)
        # Check for specific API key error text (might vary)
        if "Authorization Error" in str(e):
             return "Error: Invalid or unauthorized SerpAPI key."
        return f"Error: Web search failed. Details: {type(e).__name__}: {e}" 
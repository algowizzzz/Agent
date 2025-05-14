# Financial news tool wrapper
import logging
from tools.json_news_tool import run_json_news_search

logger = logging.getLogger(__name__)

def run_financial_news_search(query: str) -> str:
    """
    Wrapper for the JSON-based news search. This function exists for compatibility
    with the BasicAgent which expects a function with this name.
    
    Args:
        query: The search query string
        
    Returns:
        Formatted string with search results
    """
    logger.info(f"[Financial News Tool] Executing search for query: {query}")
    return run_json_news_search(query) 
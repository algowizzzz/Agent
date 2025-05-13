# Simplified financial news tool - JSON file provider only
import logging
import os
from typing import List, Dict

# Import the JSON file provider
from tools.json_news_tool import JsonFileNewsProvider, format_news_results

logger = logging.getLogger(__name__)

def run_financial_news_search(query: str, json_file_path: str = None) -> str:
    """
    Performs a news search using the provided query and returns formatted results.
    Only uses the JSON file provider.
    
    Args:
        query: The search query string
        json_file_path: Optional path to a specific JSON news file
        
    Returns:
        Formatted results as a string
    """
    logger.info(f"[Financial News Tool] Executing search for query: {query}")
    
    try:
        # Initialize the JSON provider
        json_provider = JsonFileNewsProvider(json_file_path)
        
        # Search for relevant news
        results = json_provider.search(query)
        
        if results:
            logger.info(f"[Financial News Tool] Found {len(results)} relevant news articles")
            return format_news_results(results)
        else:
            logger.warning(f"[Financial News Tool] No news articles found for query: {query}")
            return "No financial news results found matching your query."
            
    except Exception as e:
        error_msg = f"[Financial News Tool] Error during news search: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error searching news: {str(e)}" 
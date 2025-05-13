# JSON-based financial news tool
import logging
import os
import json
from typing import List, Dict
import datetime
import re

logger = logging.getLogger(__name__)

class JsonFileNewsProvider:
    """News provider that reads from JSON files containing financial news articles."""
    
    def __init__(self, json_file_path=None):
        """
        Initialize with path to JSON news file.
        If no path is provided, it will look for a default location.
        """
        self.json_file_path = json_file_path
        if not self.json_file_path:
            # Default to looking in the data/news directory
            self.json_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                              "data", "news", "financial_news.json")
        
        self.news_data = self._load_news_data()
        
    def _load_news_data(self) -> List[Dict]:
        """Load news data from the JSON file."""
        try:
            if not os.path.exists(self.json_file_path):
                logger.warning(f"News JSON file not found: {self.json_file_path}")
                return []
                
            with open(self.json_file_path, 'r') as f:
                news_data = json.load(f)
                
            logger.info(f"Successfully loaded {len(news_data)} news articles from {self.json_file_path}")
            return news_data
        except Exception as e:
            logger.error(f"Error loading news data: {e}", exc_info=True)
            return []
    
    def search(self, query: str) -> List[Dict]:
        """
        Search news articles based on the provided query.
        Performs basic keyword matching on title and content.
        """
        if not self.news_data:
            logger.warning("No news data available")
            return []
            
        # Convert query to lowercase for case-insensitive matching
        query = query.lower()
        
        # Extract keywords from query
        keywords = re.findall(r'\b\w+\b', query)
        significant_keywords = [kw for kw in keywords if len(kw) > 2 and kw not in 
                                ('the', 'and', 'for', 'with', 'news', 'about', 'latest')]
        
        results = []
        
        # Search through news articles
        for article in self.news_data:
            title = article.get('title', '').lower()
            content = article.get('content', '').lower()
            source = article.get('source', '').lower()
            
            # Calculate a simple relevance score
            score = 0
            for keyword in significant_keywords:
                if keyword in title:
                    score += 3  # Higher weight for title matches
                if keyword in content:
                    score += 1
                if keyword in source:
                    score += 0.5
            
            # Include articles that match at least one significant keyword
            if score > 0:
                # Add score to article for sorting
                article_with_score = article.copy()
                article_with_score['relevance_score'] = score
                results.append(article_with_score)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Remove the temporary score field
        for article in results:
            if 'relevance_score' in article:
                del article['relevance_score']
                
        return results

def format_news_results(results: List[Dict]) -> str:
    """Format news results into a readable string with proper structure."""
    if not results:
        return "No news articles found matching your query."
        
    formatted = "# Financial News Results\n\n"
    
    for i, item in enumerate(results, 1):
        formatted += f"## {i}. {item.get('title', 'Untitled Article')}\n"
        formatted += f"**Source**: {item.get('source', 'Unknown')}\n"
        
        # Add content
        content = item.get('content', 'No content available')
        formatted += f"\n{content}\n\n"
        
        # Add link if available
        if 'link' in item and item['link']:
            formatted += f"**Link**: {item['link']}\n\n"
        
        formatted += "---\n\n"
    
    return formatted

def run_json_news_search(query: str, json_file_path=None) -> str:
    """
    Performs a search using the provided query against JSON news files.
    Returns results as a formatted string.
    
    Args:
        query: The search query string
        json_file_path: Optional path to a specific JSON news file
        
    Returns:
        Formatted string with search results
    """
    logger.info(f"[JSON News Tool] Executing search for query: {query}")
    
    try:
        news_provider = JsonFileNewsProvider(json_file_path)
        results = news_provider.search(query)
        
        logger.info(f"[JSON News Tool] Found {len(results)} matching articles")
        return format_news_results(results)
    
    except Exception as e:
        error_msg = f"[JSON News Tool] Error during news search: {e}"
        logger.error(error_msg, exc_info=True)
        return f"Error searching news: {str(e)}" 
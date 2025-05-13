"""
Tool2_Category: Second tool in the hierarchical retrieval system.

This tool analyzes category-level summaries to:
1. Attempt to directly answer the query based on category information
2. Identify which specific document would be most relevant to explore further
3. Provide reasoning about its decision process
"""

import json
import re
import logging
import os
from typing import Dict, Any, Union, Optional, List, Type, Callable
from pymongo import MongoClient
from langchain_core.language_models import BaseChatModel
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from .config import format_category_prompt, sanitize_json_response

# Import config module
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mongodb_client():
    """Get MongoDB client with proper error handling"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        # Test connection
        client.admin.command('ping')
        return client
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection and collections"""
    client = get_mongodb_client()
    if client is None:
        return None
    
    return client['earnings_transcripts']

def load_tool_config():
    """Load tool configuration from config file"""
    config_path = os.path.join(os.path.dirname(__file__), 'tool_prompts_config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('category_tool', {})
    except Exception as e:
        logger.error(f"Failed to load tool config: {e}")
        return {}

def get_category_summary(category_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve the category summary from MongoDB.
    
    Args:
        category_id (str): The category ID to retrieve. 
                                    
    Returns:
        Optional[Dict[str, Any]]: The category summary or None if not found
    """
    if category_id is None:
        logger.error("No category ID provided")
        return None
        
    logger.info(f"Fetching category summary for ID: {category_id}")
    
    try:
        db = init_db()
        if db is None:
            logger.error("Failed to initialize database connection")
            return None
        
        # Clean up the category ID
        clean_category_id = category_id.strip().upper()
        
        # Try to find the category summary with more flexible matching
        category_summary = db.category_summaries.find_one({
            "$or": [
                {"category_id": clean_category_id},
                {"category": clean_category_id},
                {"ticker": clean_category_id},
                {"aliases": clean_category_id}
            ]
        })
        
        if category_summary is None:
            logger.warning(f"No category summary found for ID: {clean_category_id}")
            return None
    
        # Get document IDs from the metadata
        document_ids = category_summary.get("document_ids", [])
        if not document_ids and "metadata" in category_summary:
            document_ids = category_summary["metadata"].get("document_ids", [])
    
        # Handle the actual document structure
        return {
            "overview": category_summary.get("summary_text", ""),
            "key_points": category_summary.get("key_points", []),
            "themes": category_summary.get("themes", []),
            "details": {
                "last_updated": category_summary.get("last_updated"),
                "model": category_summary.get("model"),
                "document_ids": document_ids
            }
        }
        
    except Exception as e:
        logger.error(f"Error accessing MongoDB: {e}")
        return None

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def extract_category_from_query(query: str) -> Optional[str]:
    """Extract category ID from query string.
    
    Args:
        query (str): Input query string
        
    Returns:
        Optional[str]: Extracted category ID or None
    """
    # First try to extract from category=X format
    category_match = re.search(r'category=(\w+)', query, re.IGNORECASE)
    if category_match:
        return category_match.group(1).upper()
    
    # Fallback to looking for standalone tickers
    companies = re.findall(r'\b[A-Z]{3,5}\b', query.upper())
    if companies:
        return companies[0]
    
    return None

def category_summary_tool(query: str, category_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Analyze category summaries and answer queries using LLM.
    Handles plain text Thought/Answer output from LLM.
    Does NOT return document IDs - these must be found by another tool.
    
    Args:
        query (str): The query to answer
        category_id (Optional[str]): Optional category ID to filter by
    
    Returns:
        Dict[str, Any]: Response containing thought, answer.
                       'relevant_doc_ids' will always be empty.
                       'confidence' is defaulted to 0.
                       Includes 'error' key on failure.
    """
    # First try to use provided category_id
    if not category_id:
        # If not provided, try to extract from query
        category_id = extract_category_from_query(query)
    
    # If still no category_id, use default
    if not category_id:
        logger.warning("No category ID found in query or provided directly")
        return {
            "thought": "No category identified",
            "answer": "Unable to determine which company/category to analyze...",
            "relevant_doc_ids": [],
            "confidence": 0,
            "error": "No category ID found"
        }
        
    # Clean up category ID
    category_id = category_id.strip().upper()
    logger.info(f"Using category ID: {category_id}")
        
    summary_data = get_category_summary(category_id)
    
    if summary_data is None:
        return {
            "thought": "No category summary found",
            "answer": f"Unable to find relevant information for {category_id}...",
            "relevant_doc_ids": [],
            "confidence": 0,
            "error": "No category summary found"
        }
    
    llm_thought = "Analysis thought not generated."
    llm_answer = "LLM analysis failed or produced no answer."
    error_msg = None

    try:
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620", 
            temperature=0,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        summary_for_llm = { 
             "overview": summary_data.get("overview", ""),
             "key_points": summary_data.get("key_points", []),
             "themes": summary_data.get("themes", []),
        }

        # Use the plain text prompt 
        prompt = format_category_prompt(
            json.dumps(summary_for_llm, indent=2, cls=DateTimeEncoder),
            query,
            category_id
        )
                
        response = llm.invoke(prompt)
        llm_output_text = response.content
        
        # Extract Thought/Answer using Regex from plain text
        thought = "Could not parse thought."
        answer = "Could not parse answer."
        
        thought_match = re.search(r"Thought:(.*?)(?:Answer:|$)", llm_output_text, re.DOTALL | re.IGNORECASE)
        if thought_match:
            thought = thought_match.group(1).strip()
            
        answer_match = re.search(r"Answer:(.*)", llm_output_text, re.DOTALL | re.IGNORECASE)
        if answer_match:
            answer = answer_match.group(1).strip()
        elif not thought_match: 
            answer = llm_output_text.strip()
        
        llm_thought = thought
        llm_answer = answer
            
        logger.info(f"LLM selected document IDs: [] (tool does not select IDs)")
        
    except Exception as e:
        logger.error(f"Error during category tool LLM call: {str(e)}")
        error_msg = f"LLM Call Error: {str(e)}"
        llm_answer = f"Error during LLM call: {str(e)}"

    # Return standard structure
    return {
        "thought": llm_thought,
        "answer": llm_answer,
        "relevant_doc_ids": [], 
        "confidence": 0, 
        "error": error_msg 
    }

def get_tool(api_key: str) -> Callable:
    """Factory function to create and return the category tool with API key bound."""
    def category_tool_with_api_key(query: str, category_id: str = None) -> Dict[str, Any]:
        return category_summary_tool(query, category_id)
    
    # Copy attributes for better display in LangChain
    category_tool_with_api_key.__name__ = "category_summary_tool"
    category_tool_with_api_key.__doc__ = category_summary_tool.__doc__
    
    return category_tool_with_api_key

# Example usage
if __name__ == "__main__":
    import os
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run category tool analysis")
    parser.add_argument("query", help="The query to analyze")
    parser.add_argument("--category", help="Category ID to analyze", default=None)
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        exit(1)
    
    # Create the tool
    category_tool = get_tool(api_key)
    
    # Run the tool with provided arguments
    result = category_tool(args.query, args.category)
    
    # Print the result
    print(json.dumps(result, indent=2)) 
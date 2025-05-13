"""
Tool1_Department: First tool in the hierarchical retrieval system.

This tool analyzes department-level summaries to:
1. Attempt to directly answer the query based on high-level information
2. Identify which category (company) would be most relevant to explore further
3. Provide reasoning about its decision process
"""

import json
import re
import logging
from typing import Dict, Any, Union, Optional, List, Type, Callable
from pymongo import MongoClient
from langchain_core.language_models import BaseChatModel
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from datetime import datetime

# Import config module
from . import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['earnings_transcripts']

# Default department ID
DEFAULT_DEPARTMENT_ID = "TECH"

def get_department_summary(department_id: str = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve the department summary from MongoDB.
    
    Args:
        department_id (str, optional): The department ID to retrieve. 
                                    Defaults to DEFAULT_DEPARTMENT_ID.
                                    
    Returns:
        Optional[Dict[str, Any]]: The department summary or None if not found
    """
    # Use the default department ID if none is provided
    if department_id is None:
        department_id = DEFAULT_DEPARTMENT_ID
        
    # Log the department ID being used
    logger.info(f"Fetching department summary for ID: {department_id}")
    
    # Query the database
    dept_summary = db.department_summaries.find_one({"department_id": department_id})
    if not dept_summary:
        logger.warning(f"No department summary found for ID: {department_id}")
        return None
    
    summary = dept_summary.get("summary", {})
    
    # Handle different summary formats
    if isinstance(summary, dict):
        # Case 1: Summary has raw_text field with JSON string
        if "raw_text" in summary:
            raw_text = summary["raw_text"]
            logger.info("Found raw_text field in summary")
            
            try:
                # Clean the raw text of control characters and normalize newlines
                clean_text = ''.join(char for char in raw_text if ord(char) >= 32 or char in '\n\r\t')
                clean_text = clean_text.replace('\r\n', '\n').replace('\r', '\n')
                
                # Try to extract just the JSON object part using regex
                json_match = re.search(r'(\{[^{}]*\})', clean_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    logger.info("Extracted JSON object from raw_text")
                    
                    # Parse the extracted JSON
                    parsed_json = json.loads(json_str)
                    
                    # Check if we have a valid structure
                    if isinstance(parsed_json, dict) and "strategic_summary" in parsed_json:
                        logger.info("Successfully parsed JSON with strategic_summary")
                        return parsed_json
                    else:
                        logger.warning("Parsed JSON doesn't have expected structure")
                else:
                    logger.warning("No JSON object found in raw_text")
            except Exception as e:
                logger.error(f"JSON parse error details: {e}")
            
            # If we get here, parsing failed, create a structured summary
            structured_summary = {
                "strategic_summary": clean_text.strip(),
                "companies_covered": [],
                "extracted_from_raw_text": True
            }
            
            # Extract companies
            company_patterns = {
                "AAPL": r"(?:Apple|AAPL)",
                "MSFT": r"(?:Microsoft|MSFT)",
                "GOOGL": r"(?:Google|GOOGL)",
                "AMZN": r"(?:Amazon|AMZN)",
                "INTC": r"(?:Intel|INTC)",
                "NVDA": r"(?:NVIDIA|NVDA)",
                "AMD": r"AMD",
                "MU": r"(?:Micron|MU)",
                "CSCO": r"(?:Cisco|CSCO)",
                "ASML": r"ASML"
            }
            
            for ticker, pattern in company_patterns.items():
                if re.search(pattern, clean_text, re.IGNORECASE):
                    structured_summary["companies_covered"].append(ticker)
            
            logger.info(f"Created structured summary with {len(structured_summary['companies_covered'])} companies")
            return structured_summary
        
        # Case 2: Summary already has strategic_summary field
        elif "strategic_summary" in summary:
            logger.info("Found strategic_summary field in summary")
            return summary
        
        # Case 3: Summary is empty or has unexpected structure
        else:
            logger.warning(f"Summary has unexpected structure: {summary}")
            return summary
    
    # Case 4: Summary is not a dict (e.g., string)
    else:
        logger.warning(f"Summary is not a dictionary: {type(summary)}")
        return {"strategic_summary": str(summary)}

def fetch_and_format_summary(summary_id: str = None) -> tuple:
    """
    Fetch a summary by ID and format it for the LLM prompt.
    
    Args:
        summary_id (str, optional): The summary ID to retrieve.
                                   Defaults to DEFAULT_DEPARTMENT_ID.
                                   
    Returns:
        tuple: (formatted_summary, raw_summary, success)
               formatted_summary: JSON string of the summary
               raw_summary: The original summary dict
               success: Boolean indicating if retrieval was successful
    """
    # Get the summary from the database
    summary = get_department_summary(summary_id)
    
    # If no summary was found, return failure
    if not summary:
        return (
            "No department summary available.", 
            None, 
            False
        )
    
    # Format the summary for the prompt
    try:
        # Ensure the summary is properly structured
        if isinstance(summary, dict):
            if "strategic_summary" not in summary:
                summary["strategic_summary"] = str(summary)
            if "companies_covered" not in summary:
                summary["companies_covered"] = []
        else:
            summary = {
                "strategic_summary": str(summary),
                "companies_covered": []
            }
        
        formatted_summary = json.dumps(summary, indent=2, ensure_ascii=False)
        return (formatted_summary, summary, True)
    except Exception as e:
        logger.error(f"Error formatting department summary: {e}")
        # Fall back to string representation with minimal structure
        formatted_summary = json.dumps({
            "strategic_summary": str(summary),
            "companies_covered": []
        }, ensure_ascii=False)
        return (formatted_summary, summary, True)

def get_category_summary(category_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a category summary from MongoDB.
    
    Args:
        category_id (str): The category ID to retrieve.
                                    
    Returns:
        Optional[Dict[str, Any]]: The category summary or None if not found
    """
    # Log the category ID being used
    logger.info(f"Fetching category summary for ID: {category_id}")
    
    # Query the database
    category_summary = db.category_summaries.find_one({"category_id": category_id})
    if not category_summary:
        logger.warning(f"No category summary found for ID: {category_id}")
        return None
    
    return category_summary.get("summary", {})

def fetch_category_summaries() -> str:
    """
    Fetch summaries for all available categories.
    
    Returns:
        str: Formatted string with category summaries
    """
    # Get available categories from config
    dept_config = config.get_department_tool_config()
    categories = dept_config.get("default_companies", [])
    
    # Initialize result string
    result = ""
    
    # Fetch summary for each category
    for category in categories[:4]:  # Limiting to 4 categories as per requirements
        summary = get_category_summary(category)
        if summary:
            # Extract a brief version of the summary
            brief_summary = ""
            if isinstance(summary, dict) and "strategic_summary" in summary:
                brief_summary = summary["strategic_summary"][:200] + "..."  # First 200 chars
            elif isinstance(summary, str):
                brief_summary = summary[:200] + "..."
            else:
                brief_summary = str(summary)[:200] + "..."
                
            # Add to result
            result += f"--- {category} ---\n{brief_summary}\n\n"
    
    if not result:
        result = "No category summaries available."
        
    return result

def department_summary_tool(query: str, api_key: str, department_id: str = None) -> Dict[str, Any]:
    """
    Analyze department-level summaries and identify relevant categories.
    
    Args:
        query (str): The query to analyze
        api_key (str): API key for LLM
        department_id (str, optional): Department to analyze
        
    Returns:
        Dict[str, Any]: Analysis results with standardized fields
    """
    try:
        # Get and format the department summary
        formatted_summary, raw_summary, success = fetch_and_format_summary(department_id)
        if not success:
            return {
                "thought": "Failed to retrieve department summary",
                "answer": "Unable to access department information",
                "category": None,
                "confidence": 0,
                "requires_category_analysis": False
            }

        # Initialize the LLM
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0,
            anthropic_api_key=api_key
        )
        
        # Format the prompt
        prompt = config.format_department_prompt(
            query=query,
            formatted_summary=formatted_summary,
            category_summaries=fetch_category_summaries()
        )
        
        # Get LLM response
        response = llm.invoke(prompt)
        raw_llm_content = response.content # Store raw content
        
        # Parse and validate response
        try:
            # Try parsing after basic sanitization
            sanitized_content = sanitize_json_response(raw_llm_content)
            parsed_response = json.loads(sanitized_content)
            logger.debug("Department tool LLM response parsed successfully.")
        except json.JSONDecodeError as e:
            logger.error(f"Department tool JSON parsing error: {e}")
            logger.debug(f"Problematic raw content: {repr(raw_llm_content)}")
            # Return structured error
            return {
                "thought": "LLM response parsing failed.",
                "answer": "Error: Could not parse the analysis response.",
                "category": None,
                "confidence": 0,
                "requires_category_analysis": False,
                "metadata": {
                    "error": f"JSONDecodeError: {e}",
                    "raw_output_snippet": raw_llm_content[:500] + "..." if isinstance(raw_llm_content, str) else "[Output not string]",
                    "department_id": department_id or DEFAULT_DEPARTMENT_ID,
                    "timestamp": datetime.now().isoformat()
                 }
            }
        
        # Enhance response with additional fields
        enhanced_response = {
            "thought": parsed_response.get("thought", "No reasoning provided"),
            "answer": parsed_response.get("answer", "No answer provided"),
            "category": parsed_response.get("category"),
            "confidence": float(parsed_response.get("confidence", 0)),
            "requires_category_analysis": True if parsed_response.get("category") else False,
            "metadata": {
                "department_id": department_id or DEFAULT_DEPARTMENT_ID,
                "timestamp": datetime.now().isoformat(),
                "query_type": "department_analysis"
            }
        }
        
        return enhanced_response
        
    except Exception as e:
        logger.error(f"Error in department analysis: {e}")
        return {
            "thought": f"Error during analysis: {str(e)}",
            "answer": "An error occurred while analyzing the department information",
            "category": None,
            "confidence": 0,
            "requires_category_analysis": False,
            "metadata": {
                "error": str(e),
                "department_id": department_id or DEFAULT_DEPARTMENT_ID,
                "timestamp": datetime.now().isoformat()
            }
        }

def get_tool(api_key: str, debug: bool = False) -> Callable:
    """Factory function to create and return the department tool with API key bound."""
    # Set logger level based on debug flag
    if debug:
        logger.setLevel(logging.DEBUG)
        
    def department_tool_with_api_key(query: str, department_id: str = None) -> Dict[str, Any]:
        return department_summary_tool(query, api_key, department_id)
    
    # Copy attributes for better display in LangChain
    department_tool_with_api_key.__name__ = "department_summary_tool"
    department_tool_with_api_key.__doc__ = department_summary_tool.__doc__
    
    return department_tool_with_api_key

def sanitize_json_response(response: str) -> str:
    """
    Clean up the LLM response to ensure it's valid JSON.
    
    Args:
        response (str): Raw LLM response
        
    Returns:
        str: Cleaned JSON string
    """
    try:
        # Find the first { and last }
        start = response.find('{')
        end = response.rfind('}')
        
        if start == -1 or end == -1:
            logger.error("No JSON object found in response")
            return json.dumps({
                "thought": "Error processing response",
                "answer": "I don't have enough information to answer this query. Confidence: 0/10.",
                "category": "TECHNOLOGY"
            })
            
        # Extract just the JSON part
        json_str = response[start:end+1]
        
        # Remove any markdown code block markers
        json_str = json_str.replace('```json', '').replace('```', '')
        
        # Clean up newlines and extra spaces while preserving structure
        json_str = re.sub(r'\s+(?=(?:[^"]*"[^"]*")*[^"]*$)', ' ', json_str)
        
        # First try to parse as is
        try:
            parsed = json.loads(json_str)
            return json.dumps(parsed, indent=2)
        except json.JSONDecodeError:
            # If that fails, try to fix common issues
            
            # Fix unescaped quotes in values
            json_str = re.sub(r'(?<!\\)"(?=[^"]*"[^"]*$)', r'\"', json_str)
            
            # Fix trailing commas
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Try parsing again after fixes
            try:
                parsed = json.loads(json_str)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON after cleaning: {e}")
                # Return a minimal valid JSON as fallback
                return json.dumps({
                    "thought": "Error processing response",
                    "answer": "I don't have enough information to answer this query. Confidence: 0/10.",
                    "category": "TECHNOLOGY"
                })
                
    except Exception as e:
        logger.error(f"Unexpected error in sanitize_json_response: {e}")
        return json.dumps({
            "thought": "Error processing response",
            "answer": "I don't have enough information to answer this query. Confidence: 0/10.",
            "category": "TECHNOLOGY"
        })

# Example usage
if __name__ == "__main__":
    import os
    
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        exit(1)
    
    # Create the tool
    department_tool = get_tool(api_key)
    
    # Example query
    query = "How are tech companies investing in AI?"
    
    # Run the tool
    result = department_tool(query)
    
    # Print the result
    print(json.dumps(result, indent=2)) 
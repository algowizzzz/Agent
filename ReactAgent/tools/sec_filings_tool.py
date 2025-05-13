#!/usr/bin/env python3
"""
SEC Filings Analysis Tool - Extracts and analyzes information from SEC filings stored locally

This tool reads local SEC filing MHTML/HTML files and provides relevant information based on user queries.
"""

import os
import re
import logging
import json
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Configuration mapping company queries to filing files
SEC_FILINGS_CONFIG = {
    "microsoft": {
        "file": "10-K.mhtml",
        "description": "Microsoft 10-K Annual Report"
    },
    "microstrategy": {
        "file": "10-K-Mircostrategy.mhtml",
        "description": "MicroStrategy 10-K Annual Report"
    },
    "bmo": {
        "file": "bmoMD&A.mhtml",
        "description": "Bank of Montreal MD&A Report"
    },
    "xbrl": {
        "file": "XBRL Viewer.xml",
        "description": "XBRL Viewer Sample"
    }
}

def run_sec_filings_analysis(
    query: str,
    llm: Optional[BaseChatModel] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Main function to analyze SEC filings based on user query.
    
    Args:
        query: The user query about SEC filings
        llm: Optional LangChain language model (if not provided, will create one)
        api_key: Optional API key for creating LLM (if not provided, uses env var)
        
    Returns:
        String with the SEC filing analysis results
    """
    logger.info(f"[SEC Filings Analysis] Processing query: {query}")
    
    # Create LLM if not provided
    if llm is None:
        try:
            from langchain_anthropic import ChatAnthropic
            
            if api_key is None:
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("No API key provided and ANTHROPIC_API_KEY not in environment")
            
            llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0, anthropic_api_key=api_key)
            logger.info("[SEC Filings Analysis] Created new LLM instance")
        except Exception as e:
            error_msg = f"[SEC Filings Analysis] Failed to create LLM: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    try:
        # Determine which company/filing to analyze
        company, filing_info = _identify_company_and_filing(query)
        
        if not company or not filing_info:
            return "Unable to identify which company filing to analyze. Please specify a company name like Microsoft, MicroStrategy, or BMO in your query."
        
        # Read the filing content
        filing_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fillings", filing_info['file'])
        filing_content = _read_filing(filing_path)
        
        if not filing_content:
            return f"Error: Could not read filing content from {filing_info['file']}"
        
        # Extract relevant information from the filing based on the query
        return _analyze_filing_content(query, filing_content, company, filing_info, llm)
        
    except Exception as e:
        error_msg = f"[SEC Filings Analysis] Error during analysis: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

def _identify_company_and_filing(query: str) -> tuple:
    """
    Identify which company filing to analyze based on the query.
    
    Args:
        query: The user query
    
    Returns:
        Tuple of (company_key, filing_info) or (None, None) if no match
    """
    query_lower = query.lower()
    
    # Check for direct company mentions
    for company, info in SEC_FILINGS_CONFIG.items():
        if company.lower() in query_lower:
            return company, info
    
    # More flexible matching for variations of company names
    if "microsoft" in query_lower or "msft" in query_lower:
        return "microsoft", SEC_FILINGS_CONFIG["microsoft"]
    elif "microstrategy" in query_lower or "mstr" in query_lower:
        return "microstrategy", SEC_FILINGS_CONFIG["microstrategy"]
    elif "bmo" in query_lower or "bank of montreal" in query_lower:
        return "bmo", SEC_FILINGS_CONFIG["bmo"]
    elif "xbrl" in query_lower:
        return "xbrl", SEC_FILINGS_CONFIG["xbrl"]
        
    # If no company is explicitly mentioned, look for filing types
    if "10-k" in query_lower or "annual report" in query_lower:
        # Default to Microsoft if no specific company but 10-K is mentioned
        return "microsoft", SEC_FILINGS_CONFIG["microsoft"]
    elif "md&a" in query_lower or "management discussion" in query_lower:
        return "bmo", SEC_FILINGS_CONFIG["bmo"]
        
    # No clear match
    return None, None

def _read_filing(file_path: str) -> str:
    """
    Read the content of a filing file.
    
    Args:
        file_path: Path to the filing file
    
    Returns:
        The filing content as a string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # For MHTML/HTML files, extract the text using BeautifulSoup
        if file_path.endswith('.mhtml') or file_path.endswith('.html'):
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.extract()
            # Get text
            text = soup.get_text()
            # Break into lines and remove leading and trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text
        elif file_path.endswith('.xml'):
            # For XML files, just return the content as is
            return content
        else:
            # For other file types, just return the content
            return content
    except Exception as e:
        logger.error(f"Error reading filing {file_path}: {str(e)}")
        return ""

def _analyze_filing_content(
    query: str, 
    content: str, 
    company: str, 
    filing_info: dict,
    llm: BaseChatModel
) -> str:
    """
    Analyze the filing content based on the user query.
    
    Args:
        query: The user query
        content: The filing content
        company: The company key
        filing_info: Information about the filing
        llm: LangChain language model
    
    Returns:
        Analysis results as a string
    """
    logger.info(f"[SEC Filings Analysis] Analyzing {filing_info['description']} for query: {query}")
    
    # Truncate content if it's too large to fit in the context window
    max_content_length = 60000  # Adjust based on model's context limit
    if len(content) > max_content_length:
        content = content[:max_content_length] + "\n[Content truncated due to length...]"
    
    system_prompt = f"""You are a financial analysis expert specializing in SEC filings analysis. You've been provided with the content of {filing_info['description']}.

Your task is to analyze this filing and extract relevant information to answer the user's query. Focus specifically on the query and provide concise, relevant information from the filing.

If the information requested is not available in the filing, state that clearly rather than making up information.

If the query is asking for numerical data or specific facts, include those precise details in your response.
"""

    human_prompt = f"""User Query: {query}

Filing Content:
{content}

Please provide a concise, accurate response based solely on the information contained in this filing."""
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"[SEC Filings Analysis] Error in filing analysis: {str(e)}")
        return f"Error analyzing filing: {str(e)}" 
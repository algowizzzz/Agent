#!/usr/bin/env python3
"""
SEC Filings Analysis Tool - Extracts and analyzes information from SEC filings stored locally

This tool reads local SEC filing MHTML/HTML files and provides relevant information based on user queries.
"""

import os
import re
import logging
import json
import glob
from typing import Dict, List, Any, Optional, Tuple
from bs4 import BeautifulSoup
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

# Configuration mapping company queries to filing files
SEC_FILINGS_CONFIG = {
    "microsoft": {
        "file": "10-K.mhtml",
        "description": "Microsoft 10-K Annual Report",
        "alt_files": ["MSFT_10K.mhtml", "MSFT-10K.mhtml", "Microsoft-10K.mhtml"]
    },
    "microstrategy": {
        "file": "10-K-Mircostrategy.mhtml",  # Note: This matches the actual filename with the typo
        "description": "MicroStrategy 10-K Annual Report",
        "alt_files": ["10-K-Microstrategy.mhtml", "MSTR_10K.mhtml", "MSTR-10K.mhtml", "Microstrategy-10K.mhtml"]
    },
    "bmo": {
        "file": "bmoMD&A.mhtml",
        "description": "Bank of Montreal MD&A Report",
        "alt_files": ["BMO_MDA.mhtml", "BMO-MDA.mhtml", "BankOfMontreal-MDA.mhtml"]
    },
    "xbrl": {
        "file": "XBRL Viewer.xml",
        "description": "XBRL Viewer Sample",
        "alt_files": ["XBRL-Viewer.xml"]
    }
}

# Multiple possible base directories for SEC filings
POSSIBLE_SEC_FILING_DIRS = [
    # Original path
    lambda: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fillings"),
    # Nested ReactAgent path
    lambda: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ReactAgent", "fillings"),
    # Alternative spelling
    lambda: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "filings"),
    # Nested ReactAgent with alternative spelling
    lambda: os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ReactAgent", "filings"),
]

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
            available_companies = ", ".join(SEC_FILINGS_CONFIG.keys())
            return f"Unable to identify which company filing to analyze. Please specify one of these companies: {available_companies}"
        
        # Find the filing file
        filing_path, file_source = _locate_filing_file(filing_info)
        
        if not filing_path:
            # Get list of available files
            available_files = _list_available_filings()
            if available_files:
                return (f"Error: Could not find {filing_info['file']} for {company}. "
                        f"Available filings: {', '.join(available_files)}")
            else:
                return (f"Error: Could not find {filing_info['file']} for {company} "
                        f"and no other filings are available.")
        
        # Read the filing content
        filing_content = _read_filing(filing_path)
        
        if not filing_content:
            return f"Error: Could not read filing content from {os.path.basename(filing_path)}"
        
        # Extract relevant information from the filing based on the query
        return _analyze_filing_content(query, filing_content, company, filing_info, llm, file_source)
        
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

def _locate_filing_file(filing_info: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Locate the filing file in various possible locations.
    
    Args:
        filing_info: Information about the filing including filename
    
    Returns:
        Tuple of (file_path, source_description) or (None, None) if not found
    """
    # Try primary filename in all possible directories
    filename = filing_info['file']
    alt_files = filing_info.get('alt_files', [])
    
    # First try with the primary filename
    for dir_getter in POSSIBLE_SEC_FILING_DIRS:
        try:
            base_dir = dir_getter()
            file_path = os.path.join(base_dir, filename)
            if os.path.exists(file_path):
                return file_path, f"Found in {base_dir}"
        except Exception as e:
            logger.warning(f"Error accessing directory: {str(e)}")
    
    # Try alternative filenames
    for alt_file in alt_files:
        for dir_getter in POSSIBLE_SEC_FILING_DIRS:
            try:
                base_dir = dir_getter()
                file_path = os.path.join(base_dir, alt_file)
                if os.path.exists(file_path):
                    return file_path, f"Found as alternative filename in {base_dir}"
            except Exception as e:
                logger.warning(f"Error accessing directory: {str(e)}")
    
    # Try case-insensitive search
    for dir_getter in POSSIBLE_SEC_FILING_DIRS:
        try:
            base_dir = dir_getter()
            if os.path.exists(base_dir):
                for file in os.listdir(base_dir):
                    if file.lower() == filename.lower():
                        return os.path.join(base_dir, file), f"Found with case-insensitive match in {base_dir}"
                
                # Check alt files with case-insensitive matching
                for alt_file in alt_files:
                    for file in os.listdir(base_dir):
                        if file.lower() == alt_file.lower():
                            return os.path.join(base_dir, file), f"Found with case-insensitive match in {base_dir}"
        except Exception as e:
            logger.warning(f"Error accessing directory: {str(e)}")
    
    # No file found
    return None, None

def _list_available_filings() -> List[str]:
    """
    List all available filing files across all possible directories.
    
    Returns:
        List of available filing filenames
    """
    available_files = []
    
    for dir_getter in POSSIBLE_SEC_FILING_DIRS:
        try:
            base_dir = dir_getter()
            if os.path.exists(base_dir):
                for file in os.listdir(base_dir):
                    if file.endswith('.mhtml') or file.endswith('.html') or file.endswith('.xml'):
                        if file not in available_files:
                            available_files.append(file)
        except Exception as e:
            logger.warning(f"Error accessing directory: {str(e)}")
    
    return available_files

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
    llm: BaseChatModel,
    file_source: str = ""
) -> str:
    """
    Analyze the filing content based on the user query.
    
    Args:
        query: The user query
        content: The filing content
        company: The company key
        filing_info: Information about the filing
        llm: LangChain language model
        file_source: Source information about where the file was found
    
    Returns:
        Analysis results as a string
    """
    file_info = f"{filing_info['description']} ({file_source})" if file_source else filing_info['description']
    logger.info(f"[SEC Filings Analysis] Analyzing {file_info} for query: {query}")
    
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
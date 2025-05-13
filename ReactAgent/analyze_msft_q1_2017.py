#!/usr/bin/env python3
"""
Directly analyze Microsoft Q1 2017 earnings call document 
"""

import os
import logging
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_tools.tool5_transcript_analysis import analyze_document_content

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_analysis():
    """Analyze Microsoft Q1 2017 earnings call directly"""
    
    # Document ID for Microsoft Q1 2017 earnings call (October 20, 2016)
    DOCUMENT_ID = "cabb3bf8-234b-4bef-bc67-c213d5e3c703"
    
    # Define specific analysis queries
    analysis_queries = [
        "What was Microsoft's total revenue in Q1 2017?",
        "What were the key financial metrics for Microsoft in Q1 2017?",
        "What were the main business highlights and insights for Microsoft in Q1 2017?",
        "What was the revenue breakdown by segment for Microsoft in Q1 2017?",
        "What was the guidance or outlook provided for the next quarter?"
    ]
    
    # Run each analysis query
    for query in analysis_queries:
        print(f"\n{'=' * 80}")
        print(f"ANALYSIS QUERY: {query}")
        print(f"{'=' * 80}")
        
        # Call the document analysis function directly
        result = analyze_document_content(query, DOCUMENT_ID)
        
        # Check for errors
        if result.get("error"):
            print(f"ERROR: {result['error']}")
            continue
        
        # Print the answer
        print(result.get("answer", "No answer provided"))

if __name__ == "__main__":
    run_analysis() 
#!/usr/bin/env python3
"""
Test script for the SEC Filings Analysis Tool
"""

import os
import sys
from dotenv import load_dotenv

# Add the ReactAgent directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ReactAgent"))

# Import the tool
from tools.sec_filings_tool import run_sec_filings_analysis

def main():
    """Run a test of the SEC Filings Analysis Tool"""
    print("\n=== TESTING SEC FILINGS ANALYSIS TOOL ===\n")
    
    # Load environment variables to get API key
    load_dotenv()
    
    # Sample queries to test
    queries = [
        "What are Microsoft's key risk factors mentioned in their 10-K?",
        "What is MicroStrategy's bitcoin strategy?",
        "What are BMO's financial highlights from their MD&A report?"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        print("Analyzing...\n")
        
        # Run the analysis
        result = run_sec_filings_analysis(query=query)
        
        print("=== ANALYSIS RESULTS ===\n")
        print(result)
        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    main() 
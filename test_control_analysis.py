#!/usr/bin/env python3
"""
Test script for the Control Analysis Tool
"""

import os
import sys
from dotenv import load_dotenv

# Add the ReactAgent directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ReactAgent"))

# Import the tool
from tools.control_analysis_tool import run_control_analyzer_agent

def main():
    """Run a test of the Control Analysis Tool"""
    print("\n=== TESTING CONTROL ANALYSIS TOOL ===\n")
    
    # Load environment variables to get API key
    load_dotenv()
    
    # Sample control to analyze
    control = "The Finance Manager performs monthly reconciliation of cash accounts by the 5th business day of the following month."
    
    print(f"Control to analyze: '{control}'")
    print("\nAnalyzing...\n")
    
    # Run the analysis
    result = run_control_analyzer_agent(query=control)
    
    print("=== ANALYSIS RESULTS ===\n")
    print(result)

if __name__ == "__main__":
    main() 
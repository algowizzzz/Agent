#!/usr/bin/env python3
"""
Simple test for SEC Filings Tool (without API calls)
"""

import os
from tools.sec_filings_tool import (
    _list_available_filings,
    _locate_filing_file,
    SEC_FILINGS_CONFIG
)

def main():
    """Test the SEC filings tool without making API calls"""
    print("=== SEC FILINGS TOOL BASIC TEST ===\n")
    
    # Test 1: Check if the tool imports correctly
    print("✅ Successfully imported sec_filings_tool modules")
    
    # Test 2: Check the SEC_FILINGS_CONFIG
    print(f"Number of companies in SEC_FILINGS_CONFIG: {len(SEC_FILINGS_CONFIG)}")
    print("Companies configured:")
    for company in SEC_FILINGS_CONFIG.keys():
        print(f"  - {company}")
    
    # Test 3: List available filings
    print("\nSearching for available filings...")
    filings = _list_available_filings()
    if filings:
        print("Found the following SEC filings:")
        for filing in filings:
            print(f"  - {filing}")
    else:
        print("No SEC filings found")
    
    # Test 4: Check each company's filing
    print("\nAttempting to locate filings for each company:")
    for company, info in SEC_FILINGS_CONFIG.items():
        file_path, source = _locate_filing_file(info)
        if file_path:
            print(f"  ✅ {company}: {os.path.basename(file_path)} ({source})")
        else:
            print(f"  ❌ {company}: Filing not found")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    main() 
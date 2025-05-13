#!/usr/bin/env python3
"""
BMO SEC Filing Local Demo

This script creates a sample BMO SEC filing locally and extracts the MD&A section.

Usage:
    python bmo_local_demo.py
"""

import os
import re
import json
import logging
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("bmo_local_demo.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_sample_filing(output_path, form_type="10-K", year="2023"):
    """
    Create a sample SEC filing HTML file.
    
    Args:
        output_path: Path to save the sample filing to
        form_type: Form type (10-K or 10-Q)
        year: Year of the filing
        
    Returns:
        The path to the created file
    """
    logger.info(f"Creating sample {form_type} filing for year {year}")
    
    # Create sample HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bank of Montreal - {form_type} ({year})</title>
    </head>
    <body>
        <h1>BANK OF MONTREAL</h1>
        <h2>{form_type} REPORT</h2>
        <p>For the fiscal year ended October 31, {year}</p>
        
        <h2>ITEM 1. BUSINESS</h2>
        <p>Bank of Montreal is a diversified financial services provider based in North America.</p>
        <p>BMO Financial Group is a highly diversified financial services provider with total assets of $1.1 trillion.</p>
        
        <h2>ITEM 2. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS</h2>
        <p>This Management's Discussion and Analysis (MD&A) comments on Bank of Montreal's operations and financial condition for the years ended October 31, {year} and {int(year)-1}.</p>
        
        <h3>Executive Summary</h3>
        <p>Bank of Montreal reported strong financial results with net income of $4.2 billion for the fiscal year {year}, up 15% from the previous year.</p>
        <p>Return on equity was 16.2%, compared with 15.1% in {int(year)-1}.</p>
        
        <h3>Financial Performance</h3>
        <p>Revenue increased by 8% driven by growth in net interest income and higher non-interest revenue.</p>
        <p>Net interest margin was 2.68%, up from 2.54% in the prior year due to higher interest rates and favorable mix shift.</p>
        <p>Non-interest expenses increased by 4.2%, reflecting investments in technology and talent.</p>
        
        <h3>Business Segment Performance</h3>
        <p>Canadian P&C delivered net income of $1.8 billion, up 12% from the prior year.</p>
        <p>U.S. P&C reported net income of $1.4 billion, an increase of 18% year-over-year.</p>
        <p>Wealth Management generated net income of $1.2 billion, up 8% from the prior year.</p>
        <p>Capital Markets reported net income of $1.1 billion, an increase of 7% from the prior year.</p>
        
        <h3>Balance Sheet</h3>
        <p>Total assets increased by 9% to $1.1 trillion as at October 31, {year}.</p>
        <p>Loans increased by 7% to $520 billion, reflecting growth in both commercial and consumer lending.</p>
        <p>Deposits grew by 8% to $650 billion, with increases in both personal and commercial deposits.</p>
        
        <h3>Capital Management</h3>
        <p>Common Equity Tier 1 ratio was 13.2% as at October 31, {year}, well above regulatory requirements.</p>
        <p>The Bank repurchased 10 million common shares for $1.1 billion under its normal course issuer bid.</p>
        <p>The quarterly dividend was increased twice during {year}, resulting in a 5% increase from the prior year.</p>
        
        <h2>ITEM 3. QUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK</h2>
        <p>Market risk is the potential for adverse changes in the value of the Bank's assets and liabilities.</p>
        
        <h2>ITEM 4. CONTROLS AND PROCEDURES</h2>
        <p>As of October 31, {year}, the Bank's management evaluated the effectiveness of the design and operation of its disclosure controls and procedures.</p>
        
        <h2>ITEM 5. FINANCIAL STATEMENTS</h2>
        <p>The consolidated financial statements have been prepared in accordance with International Financial Reporting Standards (IFRS).</p>
    </body>
    </html>
    """
    
    # Write the HTML content to the file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    logger.info(f"Created sample filing at {output_path}")
    return output_path

def extract_mda_section(html_path):
    """
    Extract the Management's Discussion and Analysis section from an HTML filing.
    
    Args:
        html_path: Path to the HTML filing
        
    Returns:
        Text content of the MD&A section, or None if not found
    """
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Different ways MD&A might be indicated in the document
        mda_indicators = [
            r"management'?s\s+discussion\s+and\s+analysis",
            r"management\s+discussion\s+and\s+analysis",
            r"md&a",
            r"item\s+2"  # Item 2 is often MD&A
        ]
        
        # Find the MD&A section header
        mda_section = None
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            text = heading.get_text().lower()
            if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_indicators):
                mda_section = heading
                break
                
        if not mda_section:
            logger.warning(f"Could not find MD&A section in {html_path}")
            return None
            
        # Extract the MD&A section text
        mda_text = mda_section.get_text() + "\n\n"
        
        # Get all content until the next major section (h2)
        next_element = mda_section.next_sibling
        
        while next_element:
            if next_element.name == 'h2' and next_element.get_text().lower().startswith('item'):
                break
                
            if next_element.name and next_element.get_text().strip():
                mda_text += next_element.get_text().strip() + "\n\n"
                
            next_element = next_element.next_sibling
            
        logger.info(f"Extracted MD&A section from {html_path} ({len(mda_text)} characters)")
        return mda_text
        
    except Exception as e:
        logger.error(f"Error extracting MD&A section: {e}")
        return None

def main():
    """Main function for the BMO SEC filing local demo."""
    logger.info("Starting BMO SEC filing local demo")
    
    filings = []
    sample_filings = [
        {"form_type": "10-K", "year": "2023", "description": "Annual Report for 2023 Fiscal Year"},
        {"form_type": "10-Q", "year": "2023", "description": "Quarterly Report for Q3 2023"}
    ]
    
    for filing_info in sample_filings:
        form_type = filing_info["form_type"]
        year = filing_info["year"]
        description = filing_info["description"]
        
        # Create a filename for the HTML file
        html_filename = f"BMO_{form_type}_{year}.html"
        html_path = os.path.join(OUTPUT_DIR, html_filename)
        
        # Create the sample filing
        html_path = create_sample_filing(html_path, form_type, year)
        
        # Extract the MD&A section
        mda_content = extract_mda_section(html_path)
        mda_path = None
        
        if mda_content:
            # Create a filename for the MD&A text file
            mda_filename = f"BMO_{form_type}_{year}_MDA.txt"
            mda_path = os.path.join(OUTPUT_DIR, mda_filename)
            
            # Save the MD&A content to a text file
            try:
                with open(mda_path, 'w', encoding='utf-8') as f:
                    f.write(mda_content)
                    
                logger.info(f"Saved MD&A section to {mda_path}")
                
            except Exception as e:
                logger.error(f"Error saving MD&A content: {e}")
                mda_path = None
        
        # Add filing information to the list
        filings.append({
            "company": "Bank of Montreal",
            "form_type": form_type,
            "year": year,
            "description": description,
            "html_path": html_path,
            "mda_path": mda_path
        })
    
    # Save the filing information to a JSON file
    json_path = os.path.join(OUTPUT_DIR, "bmo_filings.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(filings, f, indent=2)
            
        logger.info(f"Saved filing information to {json_path}")
        
    except Exception as e:
        logger.error(f"Error saving filing information: {e}")
    
    # Print a summary
    annual_reports = sum(1 for filing in filings if filing['form_type'] == '10-K')
    quarterly_reports = sum(1 for filing in filings if filing['form_type'] == '10-Q')
    mda_sections = sum(1 for filing in filings if filing.get('mda_path'))
    
    logger.info("=" * 50)
    logger.info(f"BMO SEC Filing Local Demo Summary:")
    logger.info(f"  - Total filings processed: {len(filings)}")
    logger.info(f"  - Annual reports (10-K): {annual_reports}")
    logger.info(f"  - Quarterly reports (10-Q): {quarterly_reports}")
    logger.info(f"  - MD&A sections extracted: {mda_sections}")
    logger.info("=" * 50)
    
    logger.info("BMO SEC filing local demo completed")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
BMO SEC Filing Sample Downloader

This script downloads a sample of SEC filings for Bank of Montreal (BMO)
from direct URLs and extracts the Management's Discussion and Analysis (MD&A) section.

Usage:
    python bmo_sec_sample.py
"""

import os
import re
import time
import json
import logging
import datetime
from bs4 import BeautifulSoup
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[
        logging.FileHandler("bmo_sec_sample.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sample URLs for BMO SEC filings
SAMPLE_FILINGS = [
    {
        "form_type": "10-K",
        "filing_date": "2023-12-07",
        "url": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000023/bmo-20231031.htm",
        "description": "Annual Report for 2023 Fiscal Year"
    },
    {
        "form_type": "10-Q",
        "filing_date": "2023-08-29",
        "url": "https://www.sec.gov/Archives/edgar/data/927971/000092797123000018/bmo-20230731.htm",
        "description": "Quarterly Report for Q3 2023"
    }
]

# Request headers to avoid 403 errors
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

def download_filing(url, output_path):
    """
    Download a filing document and save it to disk.
    
    Args:
        url: URL to the filing document
        output_path: Path to save the document to
        
    Returns:
        The local path if successful, None otherwise
    """
    try:
        logger.info(f"Downloading filing from {url}")
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
            
        logger.info(f"Downloaded filing to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading filing: {e}")
        return None

def extract_mda_section(html_path):
    """
    Extract the Management's Discussion and Analysis section from an HTML filing.
    
    Args:
        html_path: Path to the HTML filing
        
    Returns:
        Text content of the MD&A section, or None if not found
    """
    try:
        with open(html_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Different ways MD&A might be indicated in the document
        mda_indicators = [
            r"management'?s\s+discussion\s+and\s+analysis",
            r"management\s+discussion\s+and\s+analysis",
            r"md&a",
            r"item\s+7"  # Item 7 is typically MD&A in 10-K
        ]
        
        # Common section headers for MD&A sections
        section_tags = ['h1', 'h2', 'h3', 'h4', 'div', 'p', 'span']
        
        # Try to find the MD&A section
        mda_section = None
        for tag in section_tags:
            for element in soup.find_all(tag):
                text = element.get_text().lower()
                if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_indicators):
                    mda_section = element
                    break
            if mda_section:
                break
                
        if not mda_section:
            logger.warning(f"Could not find MD&A section in {html_path}")
            return None
            
        # Extract the MD&A section text
        mda_text = ""
        current = mda_section
        
        # Try to find the end of the MD&A section
        mda_end_indicators = [
            r"financial\s+statements",
            r"item\s+8",
            r"item\s+4",
            r"quantitative\s+and\s+qualitative\s+disclosures",
        ]
        
        # Collect text until we find an end indicator or have collected a reasonable amount
        mda_paragraphs = []
        max_paragraphs = 30  # Limit to avoid collecting the entire document
        
        while current and len(mda_paragraphs) < max_paragraphs:
            if current.name in ['h1', 'h2', 'h3', 'h4']:
                text = current.get_text().lower()
                if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_end_indicators):
                    break
                    
            if current.name == 'p' and current.get_text().strip():
                mda_paragraphs.append(current.get_text().strip())
                
            current = current.next_element
            
        mda_text = "\n\n".join(mda_paragraphs)
            
        logger.info(f"Extracted MD&A section from {html_path} ({len(mda_text)} characters)")
        return mda_text
        
    except Exception as e:
        logger.error(f"Error extracting MD&A section: {e}")
        return None

def main():
    """Main function to download sample BMO filings."""
    logger.info("Starting BMO SEC filing sample download")
    
    filings = []
    
    for filing_info in SAMPLE_FILINGS:
        form_type = filing_info["form_type"]
        filing_date = filing_info["filing_date"]
        url = filing_info["url"]
        description = filing_info["description"]
        
        # Create a filename for the HTML file
        html_filename = f"BMO_{form_type}_{filing_date.replace('-', '')}.html"
        html_path = os.path.join(OUTPUT_DIR, html_filename)
        
        # Download the HTML filing
        html_path = download_filing(url, html_path)
        if not html_path:
            logger.warning(f"Failed to download HTML filing for {description}, skipping")
            continue
            
        # Extract the MD&A section
        mda_content = extract_mda_section(html_path)
        mda_path = None
        
        if mda_content:
            # Create a filename for the MD&A text file
            mda_filename = f"BMO_{form_type}_{filing_date.replace('-', '')}_MDA.txt"
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
            "filing_date": filing_date,
            "description": description,
            "html_path": html_path,
            "mda_path": mda_path,
        })
        
        # Add a delay to avoid overloading the SEC server
        time.sleep(2)
    
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
    logger.info(f"BMO SEC Filing Sample Download Summary:")
    logger.info(f"  - Total filings processed: {len(filings)}")
    logger.info(f"  - Annual reports (10-K): {annual_reports}")
    logger.info(f"  - Quarterly reports (10-Q): {quarterly_reports}")
    logger.info(f"  - MD&A sections extracted: {mda_sections}")
    logger.info("=" * 50)
    
    logger.info("BMO SEC filing sample download completed")

if __name__ == "__main__":
    main() 
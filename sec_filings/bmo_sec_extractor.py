#!/usr/bin/env python3
"""
BMO SEC Filing Extractor

This script extracts SEC filings (annual and quarterly reports) for Bank of Montreal (BMO)
from the SEC EDGAR RSS feed. It downloads the filings from the past year and extracts
the Management's Discussion and Analysis (MD&A) section from each report.

Usage:
    python bmo_sec_extractor.py
"""

import os
import re
import sys
import time
import json
import logging
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("bmo_sec_extractor.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Constants
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
SEC_EDGAR_RSS_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
SEC_EDGAR_BASE_URL = "https://www.sec.gov"
# BMO's CIK (Central Index Key) - used to identify the company in SEC filings
BMO_CIK = "0000927971"  # Bank of Montreal CIK
# Form types we're interested in
FORM_TYPES = ["10-K", "10-Q"]  # Annual and quarterly reports
# Time period: 1 year back from today
ONE_YEAR_AGO = datetime.datetime.now() - datetime.timedelta(days=365)

# Request headers to avoid 403 errors (SEC requires a user-agent)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def get_sec_rss_feed(cik):
    """
    Fetch the SEC EDGAR RSS feed for a given CIK.
    
    Args:
        cik: The Central Index Key for the company
        
    Returns:
        A list of feed entries
    """
    logger.info(f"Fetching SEC EDGAR RSS feed for CIK: {cik}")
    
    params = {
        "action": "getcompany",
        "CIK": cik,
        "type": ",".join(FORM_TYPES),
        "output": "atom",
        "count": 100  # Get more than we need to ensure we have a full year
    }
    
    try:
        response = requests.get(SEC_EDGAR_RSS_URL, params=params, headers=HEADERS)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        if not feed.entries:
            logger.warning(f"No entries found in the RSS feed for CIK: {cik}")
            return []
            
        logger.info(f"Successfully fetched {len(feed.entries)} SEC filings")
        return feed.entries
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching SEC EDGAR RSS feed: {e}")
        return []

def filter_entries_by_date(entries):
    """
    Filter entries to include only those from the past year.
    
    Args:
        entries: List of RSS feed entries
        
    Returns:
        Filtered list of entries
    """
    filtered_entries = []
    
    for entry in entries:
        try:
            # Parse the entry date
            entry_date = datetime.datetime.strptime(entry.updated, "%Y-%m-%dT%H:%M:%S%z")
            entry_date = entry_date.replace(tzinfo=None)  # Remove timezone for comparison
            
            # Check if the entry is from the past year
            if entry_date >= ONE_YEAR_AGO:
                filtered_entries.append(entry)
                
        except (ValueError, AttributeError) as e:
            logger.warning(f"Error parsing date for entry: {e}")
            continue
    
    logger.info(f"Filtered to {len(filtered_entries)} filings from the past year")
    return filtered_entries

def get_filing_documents_url(filing_url):
    """
    Extract the URL for the filing documents page.
    
    Args:
        filing_url: URL to the filing summary page
        
    Returns:
        URL to the filing documents page
    """
    try:
        response = requests.get(filing_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the Documents button/link which leads to the filing documents
        for link in soup.find_all('a'):
            if link.text and 'Documents' in link.text:
                return urljoin(SEC_EDGAR_BASE_URL, link['href'])
        
        logger.warning(f"Could not find documents link for filing: {filing_url}")
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching filing page: {e}")
        return None

def get_filing_document_urls(documents_url):
    """
    Extract URLs for the actual filing documents (HTML, XML, etc.).
    
    Args:
        documents_url: URL to the filing documents page
        
    Returns:
        Dictionary mapping document types to their URLs
    """
    try:
        response = requests.get(documents_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        document_urls = {}
        
        # Find the table with document information
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    # Document type (e.g., 10-K, EX-101.INS)
                    doc_type = cells[0].text.strip()
                    # Description is often "Complete submission text file" for the main document
                    description = cells[1].text.strip()
                    # Document URL
                    if cells[2].find('a'):
                        doc_url = urljoin(SEC_EDGAR_BASE_URL, cells[2].find('a')['href'])
                        document_urls[doc_type] = {
                            'description': description,
                            'url': doc_url
                        }
        
        logger.info(f"Found {len(document_urls)} document URLs")
        return document_urls
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching document URLs: {e}")
        return {}

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
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        soup = BeautifulSoup(content, 'html.parser')
        
        # Different ways MD&A might be indicated in the document
        mda_indicators = [
            r"management'?s\s+discussion\s+and\s+analysis",
            r"management\s+discussion\s+and\s+analysis",
            r"md&a",
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
        # This is a simple approach that might need refinement
        mda_text = ""
        current = mda_section
        
        # Try to find the end of the MD&A section
        # This is a heuristic approach and might need adjustment
        mda_end_indicators = [
            r"financial\s+statements",
            r"item\s+8",
            r"item\s+4",
            r"quantitative\s+and\s+qualitative\s+disclosures",
        ]
        
        while current:
            if current.name in ['h1', 'h2', 'h3', 'h4']:
                text = current.get_text().lower()
                if any(re.search(indicator, text, re.IGNORECASE) for indicator in mda_end_indicators):
                    break
                    
            mda_text += current.get_text() + "\n"
            current = current.next_sibling
            
        logger.info(f"Extracted MD&A section from {html_path} ({len(mda_text)} characters)")
        return mda_text
        
    except Exception as e:
        logger.error(f"Error extracting MD&A section: {e}")
        return None

def process_filing(entry):
    """
    Process a single filing: download it and extract the MD&A section.
    
    Args:
        entry: RSS feed entry for the filing
        
    Returns:
        Dictionary with filing information and MD&A content
    """
    # Extract filing information
    filing_type = None
    filing_date = None
    
    # Parse the title to extract the form type (10-K or 10-Q)
    title = entry.title
    for form_type in FORM_TYPES:
        if form_type in title:
            filing_type = form_type
            break
            
    if not filing_type:
        logger.warning(f"Could not determine filing type from title: {title}")
        return None
        
    # Parse the entry date
    try:
        filing_date = datetime.datetime.strptime(entry.updated, "%Y-%m-%dT%H:%M:%S%z")
        filing_date = filing_date.replace(tzinfo=None)  # Remove timezone
    except (ValueError, AttributeError) as e:
        logger.warning(f"Error parsing date for entry: {e}")
        filing_date = datetime.datetime.now()  # Default to current date
        
    # Format the date for use in filenames
    date_str = filing_date.strftime("%Y%m%d")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Filing information dictionary
    filing_info = {
        "company": "Bank of Montreal",
        "cik": BMO_CIK,
        "form_type": filing_type,
        "filing_date": filing_date.strftime("%Y-%m-%d"),
        "title": title,
        "link": entry.link,
        "html_path": None,
        "mda_path": None,
        "mda_content": None
    }
    
    logger.info(f"Processing {filing_type} filing from {filing_info['filing_date']}")
    
    # Get the documents page URL
    documents_url = get_filing_documents_url(entry.link)
    if not documents_url:
        logger.warning("Could not get documents URL, skipping filing")
        return filing_info
        
    # Get document URLs
    document_urls = get_filing_document_urls(documents_url)
    if not document_urls:
        logger.warning("Could not get document URLs, skipping filing")
        return filing_info
    
    # Look for the main filing document
    main_doc_url = None
    for doc_type, doc_info in document_urls.items():
        if doc_type in FORM_TYPES or "Complete submission" in doc_info['description']:
            main_doc_url = doc_info['url']
            break
            
    if not main_doc_url:
        # Try to find an HTML document as a fallback
        for doc_type, doc_info in document_urls.items():
            if doc_info['url'].endswith('.htm') or doc_info['url'].endswith('.html'):
                main_doc_url = doc_info['url']
                break
                
    if not main_doc_url:
        logger.warning("Could not find main document URL, skipping filing")
        return filing_info
        
    # Create a filename for the HTML file
    html_filename = f"BMO_{filing_type}_{date_str}.html"
    html_path = os.path.join(OUTPUT_DIR, html_filename)
    
    # Download the HTML filing
    html_path = download_filing(main_doc_url, html_path)
    if not html_path:
        logger.warning("Failed to download HTML filing, skipping")
        return filing_info
        
    filing_info['html_path'] = html_path
    
    # Extract the MD&A section
    mda_content = extract_mda_section(html_path)
    if mda_content:
        # Create a filename for the MD&A text file
        mda_filename = f"BMO_{filing_type}_{date_str}_MDA.txt"
        mda_path = os.path.join(OUTPUT_DIR, mda_filename)
        
        # Save the MD&A content to a text file
        try:
            with open(mda_path, 'w', encoding='utf-8') as f:
                f.write(mda_content)
                
            filing_info['mda_path'] = mda_path
            filing_info['mda_content'] = mda_content
            logger.info(f"Saved MD&A section to {mda_path}")
            
        except Exception as e:
            logger.error(f"Error saving MD&A content: {e}")
    
    return filing_info

def main():
    """Main function to extract BMO filings from SEC EDGAR."""
    logger.info("Starting BMO SEC filing extraction")
    
    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get the SEC EDGAR RSS feed for BMO
    entries = get_sec_rss_feed(BMO_CIK)
    if not entries:
        logger.error("No entries found in the SEC EDGAR RSS feed, exiting")
        sys.exit(1)
        
    # Filter entries to include only those from the past year
    entries = filter_entries_by_date(entries)
    if not entries:
        logger.error("No filings found from the past year, exiting")
        sys.exit(1)
        
    # Process each filing
    filings = []
    for i, entry in enumerate(entries):
        logger.info(f"Processing filing {i+1}/{len(entries)}")
        filing_info = process_filing(entry)
        if filing_info:
            filings.append(filing_info)
            
        # Add a delay to avoid overloading the SEC server
        time.sleep(1)
        
    # Save the filing information to a JSON file
    json_path = os.path.join(OUTPUT_DIR, "bmo_filings.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            # Remove the MD&A content from the JSON file to keep it smaller
            json_filings = []
            for filing in filings:
                filing_copy = filing.copy()
                filing_copy.pop('mda_content', None)
                json_filings.append(filing_copy)
                
            json.dump(json_filings, f, indent=2)
            
        logger.info(f"Saved filing information to {json_path}")
        
    except Exception as e:
        logger.error(f"Error saving filing information: {e}")
    
    # Print a summary
    annual_reports = sum(1 for filing in filings if filing['form_type'] == '10-K')
    quarterly_reports = sum(1 for filing in filings if filing['form_type'] == '10-Q')
    mda_sections = sum(1 for filing in filings if filing.get('mda_path'))
    
    logger.info("=" * 50)
    logger.info(f"BMO SEC Filing Extraction Summary:")
    logger.info(f"  - Total filings processed: {len(filings)}")
    logger.info(f"  - Annual reports (10-K): {annual_reports}")
    logger.info(f"  - Quarterly reports (10-Q): {quarterly_reports}")
    logger.info(f"  - MD&A sections extracted: {mda_sections}")
    logger.info("=" * 50)
    
    logger.info("BMO SEC filing extraction completed")

if __name__ == "__main__":
    main() 
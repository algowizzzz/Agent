# BMO SEC Filing Extractor

This tool extracts SEC filings (annual and quarterly reports) for Bank of Montreal (BMO) from the SEC EDGAR database using their RSS feed. It specifically focuses on identifying and extracting the Management's Discussion and Analysis (MD&A) sections from these reports.

## Features

- Downloads the past year of SEC filings for BMO (10-K annual reports and 10-Q quarterly reports)
- Extracts MD&A sections from each filing
- Saves both the original HTML filings and the extracted MD&A sections as text files
- Creates a JSON index of all processed filings
- Provides detailed logging for troubleshooting

## Requirements

The script requires the following Python packages:
- requests
- beautifulsoup4
- feedparser

You can install these requirements using pip:

```bash
pip install requests beautifulsoup4 feedparser
```

## Usage

1. Navigate to the `sec_filings` directory:
   ```bash
   cd sec_filings
   ```

2. Run the script:
   ```bash
   python bmo_sec_extractor.py
   ```

3. The script will:
   - Download filings to the `reports` directory
   - Extract MD&A sections
   - Create a summary JSON file (`bmo_filings.json`)
   - Log operations to `bmo_sec_extractor.log`

## Output

The script produces the following outputs in the `reports` directory:

- HTML files: Original SEC filings (e.g., `BMO_10-K_20230228.html`)
- Text files: Extracted MD&A sections (e.g., `BMO_10-K_20230228_MDA.txt`)
- JSON file: Index of all processed filings with metadata (`bmo_filings.json`)

## Customization

You can modify the script to extract filings for different companies by changing the `BMO_CIK` constant to the appropriate Central Index Key (CIK) for the company you're interested in.

## Notes

- The SEC imposes rate limits on their API, so the script includes a delay between requests
- The extraction of MD&A sections is based on heuristics and may not work perfectly for all filings
- The script requires an internet connection to access the SEC EDGAR database

## Troubleshooting

If you encounter issues:

1. Check the log file (`bmo_sec_extractor.log`) for detailed error messages
2. Ensure you have a stable internet connection
3. The SEC may occasionally change their website structure, which might require updates to the script 
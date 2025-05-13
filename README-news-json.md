# JSON News Feed Implementation

This document describes the implementation of the JSON-based news feed system for the financial analysis agent.

## Overview

The system has been enhanced to use JSON files as a source for financial news data instead of relying solely on external APIs like SerpAPI. This implementation offers several benefits:

1. **Offline capability**: The system can operate without internet access
2. **Customizable data**: News articles can be manually curated or sourced from any system
3. **Predictable behavior**: Testing is more reliable with consistent news data
4. **Fallback mechanism**: The system gracefully falls back from API -> JSON -> Mock data

## Components

### New Files

1. `tools/json_news_tool.py` - Core implementation of the JSON news provider
2. `utils/news_file_manager.py` - Utility to manage JSON news files
3. `data/news/financial_news.json` - Sample news data
4. `test_json_news.py` - Test script for the JSON news tool
5. `test_integrated_news.py` - Test script for the integrated news functionality

### Modified Files

1. `tools/financial_news_tool.py` - Enhanced to use JSON files as a source or fallback

## Usage

### Searching News

The news search function now accepts additional parameters:

```python
from tools.financial_news_tool import run_financial_news_search

# Use JSON file as the primary source
results = run_financial_news_search("bank downgrades", json_mode=True)

# Use API with JSON as fallback (default behavior)
results = run_financial_news_search("bank downgrades")

# Use a specific JSON file
results = run_financial_news_search(
    "bank downgrades", 
    json_mode=True,
    json_file_path="data/news/custom_news.json"
)
```

### Managing News Files

The `utils/news_file_manager.py` module provides a command-line interface for managing news files:

```bash
# List all news files
python -m utils.news_file_manager list

# Read a specific news file
python -m utils.news_file_manager read --file financial_news.json

# Create a new news file
python -m utils.news_file_manager create --file custom_news.json --json data.json

# Update an existing news file
python -m utils.news_file_manager update --file financial_news.json --json new_data.json --append
```

## JSON Format

The news data follows this JSON format:

```json
[
  {
    "title": "News Article Title",
    "source": "Source Name",
    "link": "https://example.com/article-url",
    "content": "Full text content of the news article..."
  },
  ...
]
```

## Search Algorithm

The search functionality uses a simple but effective algorithm:

1. Extracts significant keywords from the search query
2. Assigns relevance scores to articles based on keyword matches
   - Title matches: 3 points
   - Content matches: 1 point
   - Source matches: 0.5 points
3. Returns articles sorted by relevance score

## Testing

You can test the implementation using:

```bash
python test_json_news.py
python test_integrated_news.py
```

## Future Enhancements

Potential improvements for the JSON news system:

1. Add more sophisticated text search capabilities
2. Implement automated news scraping to JSON
3. Add category metadata to articles for better filtering
4. Support for multiple news JSON files with different topics 
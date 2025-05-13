#!/usr/bin/env python3
"""
Utility to manage JSON news files for the financial news tool.
"""

import os
import json
import logging
import argparse
import datetime
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_NEWS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "news")

def ensure_news_dir(directory: str = DEFAULT_NEWS_DIR) -> str:
    """Ensure the news directory exists."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created news directory: {directory}")
    return directory

def list_news_files(directory: str = DEFAULT_NEWS_DIR) -> List[str]:
    """List all JSON news files in the directory."""
    ensure_news_dir(directory)
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    return json_files

def create_news_file(news_data: List[Dict[str, Any]], filename: str = None, 
                    directory: str = DEFAULT_NEWS_DIR) -> str:
    """
    Create a new JSON news file with the provided data.
    
    Args:
        news_data: List of news article dictionaries
        filename: Optional filename to use
        directory: Directory to save the file in
        
    Returns:
        Path to the created file
    """
    ensure_news_dir(directory)
    
    if not filename:
        # Generate a timestamped filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_{timestamp}.json"
    
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename += '.json'
    
    file_path = os.path.join(directory, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(news_data, f, indent=2)
    
    logger.info(f"Created news file with {len(news_data)} articles: {file_path}")
    return file_path

def update_news_file(news_data: List[Dict[str, Any]], filename: str, 
                    directory: str = DEFAULT_NEWS_DIR, append: bool = False) -> str:
    """
    Update an existing JSON news file or create a new one if it doesn't exist.
    
    Args:
        news_data: List of news article dictionaries
        filename: Filename to update
        directory: Directory where the file is located
        append: If True, append to existing data; if False, replace existing data
        
    Returns:
        Path to the updated file
    """
    ensure_news_dir(directory)
    
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename += '.json'
    
    file_path = os.path.join(directory, filename)
    
    existing_data = []
    if os.path.exists(file_path) and append:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            logger.info(f"Loaded {len(existing_data)} existing articles from {file_path}")
        except Exception as e:
            logger.warning(f"Error loading existing file {file_path}: {e}")
            existing_data = []
    
    # Combine data if appending
    if append:
        combined_data = existing_data + news_data
        # Deduplicate based on title
        title_set = set()
        unique_data = []
        for article in combined_data:
            title = article.get('title', '')
            if title and title not in title_set:
                title_set.add(title)
                unique_data.append(article)
        final_data = unique_data
        logger.info(f"Combined {len(existing_data)} existing + {len(news_data)} new articles = {len(final_data)} unique articles")
    else:
        final_data = news_data
        logger.info(f"Replacing existing data with {len(news_data)} articles")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, indent=2)
    
    logger.info(f"Updated news file: {file_path}")
    return file_path

def read_news_file(filename: str, directory: str = DEFAULT_NEWS_DIR) -> List[Dict[str, Any]]:
    """
    Read a JSON news file.
    
    Args:
        filename: Filename to read
        directory: Directory where the file is located
        
    Returns:
        List of news article dictionaries
    """
    # Ensure .json extension
    if not filename.endswith('.json'):
        filename += '.json'
    
    file_path = os.path.join(directory, filename)
    
    if not os.path.exists(file_path):
        logger.warning(f"News file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            news_data = json.load(f)
        
        logger.info(f"Read {len(news_data)} articles from {file_path}")
        return news_data
    except Exception as e:
        logger.error(f"Error reading news file {file_path}: {e}")
        return []

def main():
    """Command-line interface for the news file manager."""
    parser = argparse.ArgumentParser(description="Manage JSON news files for the financial news tool")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List files command
    list_parser = subparsers.add_parser("list", help="List all news files")
    list_parser.add_argument("--dir", help="Directory to list files from", default=DEFAULT_NEWS_DIR)
    
    # Create file command
    create_parser = subparsers.add_parser("create", help="Create a new news file")
    create_parser.add_argument("--file", help="Filename to create", default=None)
    create_parser.add_argument("--dir", help="Directory to create file in", default=DEFAULT_NEWS_DIR)
    create_parser.add_argument("--json", help="JSON string or file path with news data", required=True)
    
    # Update file command
    update_parser = subparsers.add_parser("update", help="Update an existing news file")
    update_parser.add_argument("--file", help="Filename to update", required=True)
    update_parser.add_argument("--dir", help="Directory where the file is located", default=DEFAULT_NEWS_DIR)
    update_parser.add_argument("--json", help="JSON string or file path with news data", required=True)
    update_parser.add_argument("--append", help="Append instead of replace", action="store_true")
    
    # Read file command
    read_parser = subparsers.add_parser("read", help="Read a news file")
    read_parser.add_argument("--file", help="Filename to read", required=True)
    read_parser.add_argument("--dir", help="Directory where the file is located", default=DEFAULT_NEWS_DIR)
    
    args = parser.parse_args()
    
    if args.command == "list":
        files = list_news_files(args.dir)
        print(f"Found {len(files)} news files:")
        for i, file in enumerate(files, 1):
            print(f"{i}. {file}")
    
    elif args.command == "create" or args.command == "update":
        # Parse JSON data
        json_input = args.json
        if os.path.exists(json_input):
            # Input is a file path
            with open(json_input, 'r', encoding='utf-8') as f:
                try:
                    news_data = json.load(f)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in file: {json_input}")
                    return
        else:
            # Input is a JSON string
            try:
                news_data = json.loads(json_input)
            except json.JSONDecodeError:
                logger.error("Invalid JSON string")
                return
        
        if not isinstance(news_data, list):
            logger.error("JSON data must be a list of news article objects")
            return
        
        if args.command == "create":
            file_path = create_news_file(news_data, args.file, args.dir)
        else:  # update
            file_path = update_news_file(news_data, args.file, args.dir, args.append)
        
        print(f"{'Created' if args.command == 'create' else 'Updated'} news file: {file_path}")
    
    elif args.command == "read":
        news_data = read_news_file(args.file, args.dir)
        for i, article in enumerate(news_data, 1):
            print(f"\n--- Article {i} ---")
            print(f"Title: {article.get('title', 'N/A')}")
            print(f"Source: {article.get('source', 'N/A')}")
            if 'content' in article:
                print(f"Content: {article['content'][:100]}...")
            print(f"Link: {article.get('link', 'N/A')}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import sys
import argparse
import pymongo

# MongoDB connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]
category_summaries_collection = db["category_summaries"]

def get_category_summary(category_id):
    """Retrieve the summary for a given category"""
    summary = category_summaries_collection.find_one({"category_id": category_id.upper()})
    return summary

def save_summary_to_file(summary, output_file):
    """Save the summary to a text file"""
    if not summary:
        print(f"No summary found")
        return False
    
    try:
        with open(output_file, 'w') as f:
            f.write(f"CATEGORY SUMMARY: {summary.get('category_id', 'Unknown')}\n")
            f.write(f"Last Updated: {summary.get('last_updated', 'Unknown')}\n")
            f.write(f"Word Count: {summary.get('wordcount', 0)}\n")
            f.write(f"Transcript Count: {summary.get('transcript_count', 0)}\n")
            
            # Add token information if available
            if 'input_tokens' in summary and 'output_tokens' in summary:
                f.write(f"Tokens: {summary.get('input_tokens', 0)} input, {summary.get('output_tokens', 0)} output\n")
            
            f.write("\n" + "="*80 + "\n\n")
            f.write(summary.get('summary_text', 'No summary text available'))
        
        print(f"Summary saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving summary to file: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Extract a category summary from the database and save it as a text file")
    parser.add_argument("--category", required=True, help="Category ID (e.g., AAPL)")
    parser.add_argument("--output", default=None, help="Output file path (default: {category_id}_summary.txt)")
    
    args = parser.parse_args()
    
    # Get the summary
    category_id = args.category.upper()
    summary = get_category_summary(category_id)
    
    if not summary:
        print(f"No summary found for category {category_id}")
        sys.exit(1)
    
    # Set default output file name if not provided
    output_file = args.output if args.output else f"{category_id.lower()}_summary.txt"
    
    # Save to file
    success = save_summary_to_file(summary, output_file)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 
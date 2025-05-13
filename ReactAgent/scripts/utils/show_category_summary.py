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

def display_summary(summary):
    """Format and display the summary"""
    if not summary:
        return "No summary found for this category"
    
    output = f"Category: {summary.get('category_id', 'Unknown')}\n"
    output += f"Last Updated: {summary.get('last_updated', 'Unknown')}\n"
    output += f"Word Count: {summary.get('wordcount', 0)}\n"
    output += f"Transcript Count: {summary.get('transcript_count', 0)}\n"
    
    # Add token information if available
    if 'input_tokens' in summary and 'output_tokens' in summary:
        output += f"Tokens: {summary.get('input_tokens', 0)} input, {summary.get('output_tokens', 0)} output\n"
    
    # --- ADDED: Print the actual document_ids field ---
    output += f"\nStored Document IDs Field:\n{summary.get('document_ids', 'No document IDs')}"
    # --- END ADDED ---
    
    output += "\n" + "-" * 80 + "\n\n"
    output += summary.get('summary_text', 'No summary text available')
    
    return output

def main():
    parser = argparse.ArgumentParser(description="Display a category summary from the database")
    parser.add_argument("--category", required=True, help="Category ID (e.g., AAPL)")
    
    args = parser.parse_args()
    
    # Get and display summary
    category_id = args.category.upper()
    summary = get_category_summary(category_id)
    
    if not summary:
        print(f"No summary found for category {category_id}")
        sys.exit(1)
    
    print(display_summary(summary))

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
import sys
import argparse
import pymongo
import datetime

# MongoDB connection
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["earnings_transcripts"]
category_summaries_collection = db["category_summaries"]

def count_words(text):
    """Count the number of words in a text"""
    return len(text.split())

def import_summary_file(category_id, file_path):
    """Import a summary file into the database"""
    try:
        with open(file_path, 'r') as f:
            summary_text = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return False
    
    # Check for existing summary
    existing_summary = category_summaries_collection.find_one({"category_id": category_id})
    
    # Prepare summary document
    summary_doc = {
        "category_id": category_id,
        "summary_text": summary_text,
        "wordcount": count_words(summary_text),
        "transcript_count": 0,  # We don't know how many transcripts were used
        "last_updated": datetime.datetime.now(),
        "import_source": file_path,
        "document_ids": []
    }
    
    if existing_summary:
        # Update existing summary
        category_summaries_collection.update_one(
            {"category_id": category_id},
            {"$set": summary_doc}
        )
        print(f"Updated existing summary for {category_id}")
    else:
        # Insert new summary
        category_summaries_collection.insert_one(summary_doc)
        print(f"Inserted new summary for {category_id}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Import a summary file into the database")
    parser.add_argument("--category", required=True, help="Category ID (e.g., AAPL)")
    parser.add_argument("--file", required=True, help="Path to the summary file")
    
    args = parser.parse_args()
    
    # Import the summary
    category_id = args.category.upper()
    success = import_summary_file(category_id, args.file)
    
    if success:
        print(f"Successfully imported summary for {category_id}")
    else:
        print(f"Failed to import summary for {category_id}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
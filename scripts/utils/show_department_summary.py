#!/usr/bin/env python3
import sys
import argparse
from datetime import datetime
from pymongo import MongoClient

def get_department_summary(department_id):
    """Retrieve department summary from the database"""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        db = client.earnings_transcripts
        
        summary = db.department_summaries.find_one({"department_id": department_id})
        return summary
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

def display_summary(summary):
    """Display the summary with metadata"""
    if not summary:
        print("No summary found")
        return
        
    print(f"\nDepartment: {summary['department_id']}")
    print(f"Last Updated: {summary['last_updated']}")
    print(f"Model: {summary['model']}")
    print(f"Categories: {', '.join(summary['category_ids'])}")
    print("\nSummary:")
    print("=" * 80)
    print(summary['summary_text'])
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Display a department summary from the database")
    parser.add_argument("--department", required=True, help="Department ID to display summary for")
    args = parser.parse_args()
    
    summary = get_department_summary(args.department)
    display_summary(summary)

if __name__ == "__main__":
    main() 
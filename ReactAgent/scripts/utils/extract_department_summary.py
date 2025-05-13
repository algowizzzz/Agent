#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime
from pymongo import MongoClient

def get_mongodb_client():
    """Get MongoDB client with error handling"""
    try:
        return MongoClient('mongodb://localhost:27017/')
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        sys.exit(1)

def get_department_summary(client, department_id):
    """Retrieve department summary from MongoDB"""
    db = client.bussgpt
    summary = db.department_summaries.find_one({"department_id": department_id})
    if not summary:
        print(f"No summary found for department: {department_id}")
        sys.exit(1)
    return summary

def format_summary_for_file(summary):
    """Format the department summary for text file output"""
    output = []
    
    # Add metadata
    output.append("=== Department Summary Metadata ===")
    output.append(f"Department ID: {summary.get('department_id')}")
    output.append(f"Last Updated: {summary.get('last_updated')}")
    output.append(f"Model Used: {summary.get('model')}")
    output.append(f"Categories Analyzed: {', '.join(summary.get('category_ids', []))}")
    output.append("\n=== Summary Content ===\n")
    
    # Add the summary content
    summary_data = summary.get('summary', {})
    if isinstance(summary_data, dict):
        for section, content in summary_data.items():
            # Convert section name from snake_case to Title Case
            section_title = section.replace('_', ' ').title()
            output.append(f"--- {section_title} ---\n")
            
            if isinstance(content, list):
                for item in content:
                    output.append(f"• {item}")
            else:
                output.append(str(content))
            output.append("")  # Empty line between sections
    else:
        output.append(str(summary_data))
    
    return "\n".join(output)

def save_summary_to_file(formatted_summary, output_file):
    """Save the formatted summary to a text file"""
    try:
        with open(output_file, 'w') as f:
            f.write(formatted_summary)
        print(f"Summary saved to: {output_file}")
    except Exception as e:
        print(f"Error saving summary to file: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Extract department summary to text file")
    parser.add_argument("--department", required=True, help="Department ID to extract")
    parser.add_argument("--output", required=True, help="Output file path")
    args = parser.parse_args()
    
    # Get MongoDB client
    client = get_mongodb_client()
    
    # Get department summary
    summary = get_department_summary(client, args.department)
    
    # Format summary for file output
    formatted_summary = format_summary_for_file(summary)
    
    # Save to file
    save_summary_to_file(formatted_summary, args.output)

if __name__ == "__main__":
    main() 
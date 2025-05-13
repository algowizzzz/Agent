#!/usr/bin/env python3
"""
Simple script to check MongoDB transcript metadata
"""

import json
from langchain_tools.tool4_metadata_lookup import get_mongodb_client

# Connect to MongoDB
client = get_mongodb_client()
db = client['earnings_transcripts']

# Get collections
transcripts_coll = db.transcripts
summaries_coll = db.document_summaries
category_summaries_coll = db.category_summaries

# Get basic counts
transcript_count = transcripts_coll.count_documents({})
summary_count = summaries_coll.count_documents({})
category_summary_count = category_summaries_coll.count_documents({})

# Get list of unique categories
categories = transcripts_coll.distinct('category_id')

# Get sample transcript info for each category
category_info = {}
for cat in categories:
    docs = list(transcripts_coll.find(
        {'category_id': cat}, 
        {'document_id': 1, 'date': 1, 'quarter': 1, 'fiscal_year': 1, '_id': 0}
    ).sort('date', -1).limit(3))
    
    # Convert dates to strings for JSON serialization
    for doc in docs:
        if 'date' in doc and doc['date']:
            doc['date'] = doc['date'].strftime('%Y-%m-%d')
    
    category_info[cat] = docs

# Print overall statistics
print("=== Earnings Transcripts Database Statistics ===")
print(f"Total transcripts: {transcript_count}")
print(f"Transcripts with summaries: {summary_count}")
print(f"Categories with synthesized summaries: {category_summary_count}")
print(f"Unique companies/categories: {len(categories)}")
print("\n=== Category List ===")
print(", ".join(categories))

# Print sample data
print("\n=== Sample Transcript Data (3 most recent per category) ===")
for cat, docs in category_info.items():
    print(f"\n{cat}:")
    for doc in docs:
        print(f"  - Q{doc.get('quarter')} {doc.get('fiscal_year')} ({doc.get('date')}) - ID: {doc.get('document_id')}")

print("\nDone!") 
from pymongo import MongoClient
import pprint

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')

# List all databases
print("Available databases:")
for db_name in client.list_database_names():
    print(f"- {db_name}")

# Check earnings_transcripts database
db_name = 'earnings_transcripts'
print(f"\nExploring database: {db_name}")
db = client[db_name]

# List all collections
print("\nCollections:")
for collection in db.list_collection_names():
    count = db[collection].count_documents({})
    print(f"- {collection}: {count} documents")

# For each collection, show one sample document's structure
for collection in db.list_collection_names():
    print(f"\nSample document structure for '{collection}':")
    sample = db[collection].find_one()
    if sample:
        # Get just the keys and their types, not the values
        keys_types = {k: type(v).__name__ for k, v in sample.items()}
        pprint.pprint(keys_types)
    else:
        print("No documents found")

# Get document info for category AAPL
print("\nAAPL documents (by collection):")
for collection in db.list_collection_names():
    count = db[collection].count_documents({'category_id': 'AAPL'})
    if count > 0:
        print(f"- {collection}: {count} documents with category_id='AAPL'")
    
    # Also try category field
    count = db[collection].count_documents({'category': 'AAPL'})
    if count > 0:
        print(f"- {collection}: {count} documents with category='AAPL'") 
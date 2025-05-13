from pymongo import MongoClient
import pprint
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['earnings_transcripts']

def print_db_status(message="Current database status:"):
    """Print current database status with collection counts"""
    print(f"\n{message}")
    for collection in sorted(db.list_collection_names()):
        count = db[collection].count_documents({})
        print(f"- {collection}: {count} documents")

def rename_collection(old_name, new_name):
    """Rename a collection if it exists"""
    if old_name in db.list_collection_names():
        if new_name not in db.list_collection_names():
            db[old_name].rename(new_name)
            print(f"Renamed collection '{old_name}' to '{new_name}'")
        else:
            print(f"Cannot rename: '{new_name}' already exists")
    else:
        print(f"Collection '{old_name}' does not exist")

def standardize_document_fields(collection_name, field_mapping, query=None):
    """Standardize field names in documents based on mapping"""
    if query is None:
        query = {}
    
    count = 0
    for doc in db[collection_name].find(query):
        updates = {}
        for old_field, new_field in field_mapping.items():
            if old_field in doc and old_field != new_field:
                # Only update if the field exists and needs to be renamed
                updates[new_field] = doc[old_field]
                updates[old_field] = ""  # Will be unset later
        
        if updates:
            # Apply updates
            db[collection_name].update_one(
                {"_id": doc["_id"]},
                {"$set": {k: v for k, v in updates.items() if v != ""},
                 "$unset": {k: 1 for k, v in updates.items() if v == ""}}
            )
            count += 1
    
    print(f"Standardized fields in {count} documents in '{collection_name}'")

def add_metadata_field(collection_name, field_name, value, query=None):
    """Add a metadata field to documents"""
    if query is None:
        query = {}
    
    result = db[collection_name].update_many(
        query,
        {"$set": {field_name: value}}
    )
    
    print(f"Added '{field_name}' to {result.modified_count} documents in '{collection_name}'")

def merge_collections(source_name, target_name, id_field="document_id"):
    """Merge documents from source to target based on id_field"""
    if source_name not in db.list_collection_names() or target_name not in db.list_collection_names():
        print(f"One of the collections does not exist")
        return
    
    # Count before
    target_count_before = db[target_name].count_documents({})
    
    # Get all documents from source
    for doc in db[source_name].find():
        if id_field in doc:
            # Check if document exists in target
            existing = db[target_name].find_one({id_field: doc[id_field]})
            if existing:
                # Update existing document
                db[target_name].update_one(
                    {id_field: doc[id_field]},
                    {"$set": {k: v for k, v in doc.items() if k != "_id"}}
                )
            else:
                # Insert new document
                new_doc = {k: v for k, v in doc.items() if k != "_id"}
                db[target_name].insert_one(new_doc)
    
    # Count after
    target_count_after = db[target_name].count_documents({})
    print(f"Merged {target_count_after - target_count_before} documents from '{source_name}' to '{target_name}'")

def remove_duplicate_documents(collection_name, id_field="document_id"):
    """Remove duplicate documents based on id_field"""
    # Get all unique IDs
    distinct_ids = db[collection_name].distinct(id_field)
    
    duplicates_removed = 0
    for id_value in distinct_ids:
        # Find all documents with this ID
        docs = list(db[collection_name].find({id_field: id_value}))
        if len(docs) > 1:
            # Keep the most recent document (or the one with most fields if no date)
            if all('last_updated' in doc for doc in docs):
                # Sort by last_updated
                docs.sort(key=lambda x: x.get('last_updated', datetime.min), reverse=True)
            else:
                # Sort by number of fields as a heuristic for completeness
                docs.sort(key=lambda x: len(x.keys()), reverse=True)
            
            # Keep the first document, remove others
            for doc in docs[1:]:
                db[collection_name].delete_one({"_id": doc["_id"]})
                duplicates_removed += 1
    
    print(f"Removed {duplicates_removed} duplicate documents from '{collection_name}'")

def delete_empty_collections():
    """Delete collections with zero documents"""
    for collection in db.list_collection_names():
        if db[collection].count_documents({}) == 0:
            db[collection].drop()
            print(f"Deleted empty collection '{collection}'")

def main():
    print_db_status("Initial database status:")
    
    # Step 1: Rename collections for consistency
    print("\nRenaming collections for consistency...")
    rename_collection("department_summary", "department_summaries_old")
    rename_collection("transcripts_backup", "transcripts_archive")
    
    # Step 2: Standardize field names
    print("\nStandardizing field names...")
    field_mapping = {
        "category": "category_id",  # Make category_id the standard identifier
        "ticker": "category_id",    # Rename ticker to category_id
        "content": "transcript_text" # Standardize transcript field name
    }
    
    standardize_document_fields("transcripts", field_mapping)
    standardize_document_fields("transcripts_archive", field_mapping)
    
    # Step 3: Add metadata where missing
    print("\nAdding metadata fields where missing...")
    add_metadata_field("transcripts", "data_type", "earnings_transcript", 
                      {"data_type": {"$exists": False}})
    
    add_metadata_field("document_summaries", "summary_type", "document_summary", 
                      {"summary_type": {"$exists": False}})
    
    add_metadata_field("category_summaries", "summary_type", "category_summary", 
                      {"summary_type": {"$exists": False}})
    
    # Step 4: Remove duplicates
    print("\nRemoving duplicate documents...")
    remove_duplicate_documents("transcripts")
    remove_duplicate_documents("document_summaries")
    remove_duplicate_documents("category_summaries")
    
    # Step 5: Merge relevant collections if needed
    print("\nMerging collections if needed...")
    # This is cautious - only uncomment if you're sure you want to merge
    # merge_collections("transcripts_archive", "transcripts", "document_id")
    
    # Step 6: Delete empty collections
    print("\nDeleting empty collections...")
    delete_empty_collections()
    
    # Final status
    print_db_status("Final database status:")
    
    print("\nDatabase cleanup complete.")

if __name__ == "__main__":
    # Ask for confirmation
    print("This script will clean up the database, standardize fields, and remove duplicates.")
    print("It's recommended to back up your database before proceeding.")
    response = input("Do you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        main()
    else:
        print("Operation cancelled.") 
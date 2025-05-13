from pymongo import MongoClient
import json
import os
import datetime
import pprint

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['earnings_transcripts']

def backup_database(output_dir="database_backup"):
    """Backup all collections in the database to JSON files"""
    # Create backup directory if it doesn't exist
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"{output_dir}_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)
    
    print(f"Backing up database 'earnings_transcripts' to directory: {backup_dir}")
    
    # Get all collections
    collections = db.list_collection_names()
    
    # Backup each collection
    for collection_name in collections:
        # Create a JSON-serializable list of all documents
        docs = list(db[collection_name].find())
        
        # Convert ObjectId to string for JSON serialization
        for doc in docs:
            doc['_id'] = str(doc['_id'])
            
            # Handle datetime objects
            for key, value in doc.items():
                if isinstance(value, datetime.datetime):
                    doc[key] = value.isoformat()
        
        # Save to file
        output_file = os.path.join(backup_dir, f"{collection_name}.json")
        with open(output_file, 'w') as f:
            json.dump(docs, f, indent=2)
        
        print(f"Backed up {len(docs)} documents from '{collection_name}' to {output_file}")
    
    # Create a metadata file with collection statistics
    metadata = {
        "backup_date": timestamp,
        "database": "earnings_transcripts",
        "collections": {}
    }
    
    for collection_name in collections:
        count = db[collection_name].count_documents({})
        metadata["collections"][collection_name] = {
            "document_count": count
        }
    
    metadata_file = os.path.join(backup_dir, "backup_metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nBackup complete! Metadata saved to {metadata_file}")
    return backup_dir

def restore_from_backup(backup_dir):
    """Restore database from backup files"""
    if not os.path.exists(backup_dir):
        print(f"Backup directory {backup_dir} does not exist")
        return False
    
    # Get metadata
    metadata_file = os.path.join(backup_dir, "backup_metadata.json")
    if not os.path.exists(metadata_file):
        print(f"Metadata file not found: {metadata_file}")
        return False
    
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
    
    print(f"Restoring database from backup: {backup_dir}")
    print(f"Backup date: {metadata.get('backup_date', 'unknown')}")
    
    # Get all collection files
    for collection_name, stats in metadata["collections"].items():
        json_file = os.path.join(backup_dir, f"{collection_name}.json")
        if not os.path.exists(json_file):
            print(f"Warning: Collection file not found: {json_file}")
            continue
        
        # Load documents
        with open(json_file, 'r') as f:
            docs = json.load(f)
        
        print(f"Restoring {len(docs)} documents to collection '{collection_name}'...")
        
        # Create temporary collection
        temp_collection = f"{collection_name}_temp"
        db[temp_collection].drop()  # Ensure it's empty
        
        # Insert documents
        if docs:
            db[temp_collection].insert_many(docs)
        
        # Replace original collection with temp
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
        
        db[temp_collection].rename(collection_name)
    
    print("\nRestore complete!")
    return True

if __name__ == "__main__":
    print("MongoDB Database Backup Utility")
    print("==============================")
    print("1. Create backup")
    print("2. Restore from backup")
    choice = input("Choose an option (1/2): ")
    
    if choice == "1":
        backup_dir = backup_database()
        print(f"\nBackup created at: {backup_dir}")
        print("You can use this location if you need to restore.")
    
    elif choice == "2":
        backup_dir = input("Enter backup directory path: ")
        if os.path.exists(backup_dir):
            confirm = input(f"This will overwrite existing collections. Continue? (yes/no): ")
            if confirm.lower() in ['yes', 'y']:
                restore_from_backup(backup_dir)
            else:
                print("Restore cancelled")
        else:
            print(f"Directory not found: {backup_dir}")
    
    else:
        print("Invalid option") 
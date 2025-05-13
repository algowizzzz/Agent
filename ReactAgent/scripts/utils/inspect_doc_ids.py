import pymongo
import json
from bson import json_util # For proper JSON serialization of MongoDB types
import argparse # Added argparse

def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping') # Test connection
        print("MongoDB connection successful.")
        return client
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        return None

def inspect_specific_documents(doc_ids_to_inspect: list):
    client = get_mongodb_client()
    if client is None:
        return

    try:
        db = client['earnings_transcripts']
        target_collection_name = "transcripts" 
        documents_collection = db[target_collection_name]
        
        print(f"\nInspecting specific documents from '{db.name}.{documents_collection.name}' collection...")
        print(f"Document IDs: {doc_ids_to_inspect}")
        
        # Fetch specific documents by document_id (UUID string)
        # Ensure IDs are strings if they come from argparse
        doc_ids_str = [str(doc_id) for doc_id in doc_ids_to_inspect]
        found_docs = list(documents_collection.find({"document_id": {"$in": doc_ids_str}}))
        
        if found_docs:
            print(f"\nFound {len(found_docs)} matching documents.")
            for i, doc in enumerate(found_docs):
                print(f"\n--- Document {i+1} (ID: {doc.get('document_id', 'N/A')}) --- ")
                # Print select fields, including a snippet of transcript_text
                print(f"  _id: {doc.get('_id')}")
                print(f"  document_id: {doc.get('document_id')}")
                print(f"  category_id: {doc.get('category_id')}")
                print(f"  date: {doc.get('date')}")
                print(f"  filename: {doc.get('filename')}")
                transcript_text = doc.get('transcript_text', '')
                print(f"  transcript_text (first 500 chars):\n    {transcript_text[:500]}...")
                print("------------------------------------")
        else:
            print("No documents found matching the specified IDs in the collection.")
            
    except Exception as e:
        print(f"An error occurred while inspecting documents: {e}")
    finally:
        if client:
            client.close()
            print("\nMongoDB connection closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect specific documents by document_id.")
    parser.add_argument("doc_ids", nargs='+', help="One or more document_id strings to inspect.")
    args = parser.parse_args()
    
    inspect_specific_documents(args.doc_ids) 
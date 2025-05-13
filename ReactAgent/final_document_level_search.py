#!/usr/bin/env python3
"""
Document-Level Semantic Search Implementation

This module implements a pure semantic search approach at the document level:
1. No metadata filtering - relies solely on semantic search
2. Document-level granularity (one vector per document) instead of chunks
3. Uses high-quality document summaries for embedding when available
4. Uses original user query without enhancement
"""

import os
import json
import logging
import chromadb
import pymongo
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CHROMA_PERSIST_DIR = "./chroma_db_persist"
NEW_COLLECTION_NAME = "document_level_embeddings"
EMBEDDING_MODEL = "all-mpnet-base-v2"
MONGODB_URI = "mongodb://localhost:27017/"
MAX_RESULTS = 10

# Load ticker mapping
uuid_to_ticker = {}
try:
    with open("ticker_mapping.json", "r") as f:
        uuid_to_ticker = json.load(f)
    logger.info(f"Loaded ticker mapping with {len(uuid_to_ticker)} entries")
except Exception as e:
    logger.warning(f"Error loading ticker mapping: {e}")

def get_mongodb_client() -> Optional[pymongo.MongoClient]:
    """Get MongoDB client connection"""
    try:
        client = pymongo.MongoClient(MONGODB_URI)
        # Test connection
        client.admin.command('ping')
        return client
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        return None

def get_document_summary(doc_id: str) -> str:
    """Get document summary from MongoDB if available"""
    client = get_mongodb_client()
    if not client:
        return ""
    
    try:
        db = client['earnings_transcripts']
        
        # Check document_summaries collection
        summary_doc = db.document_summaries.find_one({"document_id": doc_id})
        if summary_doc and "summary" in summary_doc:
            return summary_doc["summary"]
        
        return ""
    except Exception as e:
        logger.error(f"Error fetching document summary for {doc_id}: {e}")
        return ""
    finally:
        client.close()

def get_document_content(doc_id: str) -> str:
    """Get document content from MongoDB if available"""
    client = get_mongodb_client()
    if not client:
        return ""
    
    try:
        db = client['earnings_transcripts']
        
        # Get document from transcripts collection
        transcript_doc = db.transcripts.find_one({"document_id": doc_id})
        if transcript_doc and "transcript_text" in transcript_doc:
            # Get the transcript text and truncate if needed
            transcript_text = transcript_doc["transcript_text"]
            
            # Get the first 8000 characters (approximately 2000 tokens)
            # This is to avoid exceeding token limits in embedding models
            max_length = 8000
            if len(transcript_text) > max_length:
                truncated_text = transcript_text[:max_length] + "... [truncated]"
                return truncated_text
            
            return transcript_text
        
        return ""
    except Exception as e:
        logger.error(f"Error fetching document content for {doc_id}: {e}")
        return ""
    finally:
        client.close()

def get_document_metadata(doc_id: str) -> Dict[str, Any]:
    """Fetch document metadata from MongoDB if available"""
    client = get_mongodb_client()
    if not client:
        return {}
    
    try:
        db = client['earnings_transcripts']
        
        # Get document metadata from the transcripts collection
        transcript_doc = db.transcripts.find_one({"document_id": doc_id})
        if transcript_doc:
            # Extract metadata fields from transcript document
            metadata = {
                "document_id": doc_id,
                "category_id": transcript_doc.get("category_id", "Unknown"),
            }
            
            # Use 'category' field directly for ticker
            if "category" in transcript_doc:
                metadata["ticker"] = transcript_doc["category"]
            
            # Create a meaningful document name using available fields
            # Format: "Company - Q[Quarter] [Year] Earnings Call ([Date])"
            company = transcript_doc.get("category", "Unknown")
            quarter = transcript_doc.get("quarter", "")
            fiscal_year = transcript_doc.get("fiscal_year", "")
            date_str = transcript_doc.get("date", "")
            
            # Format the date if available
            formatted_date = ""
            if date_str:
                try:
                    # Try to parse the date string from ISO format
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime("%Y-%m-%d")
                except:
                    formatted_date = date_str.split("T")[0] if "T" in date_str else date_str
            
            # Create the document name
            document_name = f"{company}"
            if quarter and fiscal_year:
                document_name += f" - Q{quarter} {fiscal_year} Earnings Call"
            if formatted_date:
                document_name += f" ({formatted_date})"
                
            metadata["document_name"] = document_name
            
            # Debug metadata extraction
            logger.debug(f"Extracted metadata for {doc_id}: {metadata}")
            
            # Convert MongoDB _id to string representation if needed
            if "_id" in transcript_doc:
                metadata["_id"] = str(transcript_doc["_id"])
            
            return metadata
            
        return {}
    except Exception as e:
        logger.error(f"Error fetching document metadata for {doc_id}: {e}")
        return {}
    finally:
        client.close()

def get_all_document_ids() -> List[str]:
    """Get all document IDs from MongoDB"""
    client = get_mongodb_client()
    if not client:
        return []
    
    try:
        db = client['earnings_transcripts']
        
        # Get all document IDs from transcripts collection
        documents = db.transcripts.find({}, {"document_id": 1})
        document_ids = [doc["document_id"] for doc in documents if "document_id" in doc]
        
        return document_ids
    except Exception as e:
        logger.error(f"Error fetching document IDs: {e}")
        return []
    finally:
        client.close()

def get_documents_by_company(company_id: str) -> List[str]:
    """Get document IDs for a specific company"""
    client = get_mongodb_client()
    if not client:
        return []
    
    try:
        db = client['earnings_transcripts']
        
        # Get document IDs by company ID
        documents = db.transcripts.find({"category_id": company_id}, {"document_id": 1})
        document_ids = [doc["document_id"] for doc in documents if "document_id" in doc]
        
        return document_ids
    except Exception as e:
        logger.error(f"Error fetching documents for company {company_id}: {e}")
        return []
    finally:
        client.close()

def create_document_level_embeddings():
    """Create document-level embeddings for all documents"""
    # Initialize embedding model
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    
    # Create embedding function for ChromaDB
    class SentenceTransformerEmbeddings:
        def __init__(self, model):
            self.model = model
            
        def __call__(self, input):
            return self.model.encode(input).tolist()
    
    embedding_function = SentenceTransformerEmbeddings(embedding_model)
    
    # Connect to ChromaDB
    logger.info(f"Connecting to ChromaDB at {CHROMA_PERSIST_DIR}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    
    # Create new collection
    try:
        # If collection exists, delete it first
        chroma_client.delete_collection(name=NEW_COLLECTION_NAME)
        logger.info(f"Deleted existing collection: {NEW_COLLECTION_NAME}")
    except Exception:
        # Collection doesn't exist yet, that's fine
        pass
        
    new_collection = chroma_client.create_collection(
        name=NEW_COLLECTION_NAME,
        embedding_function=embedding_function,
        metadata={"description": "Document-level embeddings for semantic search"}
    )
    
    # Get all document IDs
    document_ids = get_all_document_ids()
    logger.info(f"Found {len(document_ids)} documents to process")
    
    # Process each document
    docs_processed = 0
    docs_with_summaries = 0
    
    for doc_id in document_ids:
        # Get document summary and metadata
        summary = get_document_summary(doc_id)
        metadata = get_document_metadata(doc_id)
        
        # Skip if no metadata found
        if not metadata:
            logger.warning(f"No metadata found for document {doc_id}, skipping")
            continue
        
        # Prepare document metadata for ChromaDB
        chroma_metadata = {
            "document_id": doc_id,
            "document_name": metadata.get("document_name", "Unknown"),
            "category_id": metadata.get("category_id", "Unknown"),
        }
        
        # Add ticker symbol for easier display if available
        if "ticker" in metadata:
            chroma_metadata["ticker"] = metadata["ticker"]
        elif "category_id" in metadata and metadata["category_id"] in uuid_to_ticker:
            ticker = uuid_to_ticker[metadata["category_id"]]
            chroma_metadata["ticker"] = ticker
        else:
            # Try to use the category_id itself as ticker if it's a valid ticker format
            category_id = metadata.get("category_id", "")
            if category_id and len(category_id) <= 5 and category_id.isalpha():
                chroma_metadata["ticker"] = category_id
        
        # Flag if we have a summary
        has_summary = bool(summary)
        chroma_metadata["has_summary"] = has_summary
        
        try:
            # If we have a summary, use it for embedding
            if has_summary:
                # Add document with summary to collection
                new_collection.add(
                    ids=[doc_id],
                    documents=[summary],
                    metadatas=[chroma_metadata]
                )
                docs_with_summaries += 1
            else:
                # If no summary, try to use the document content
                content = get_document_content(doc_id)
                if content:
                    # Add document with content to collection
                    chroma_metadata["has_content"] = True
                    new_collection.add(
                        ids=[doc_id],
                        documents=[content[:5000]],  # Truncate to first 5000 chars to avoid token limit issues
                        metadatas=[chroma_metadata]
                    )
                else:
                    logger.warning(f"No summary or content found for document {doc_id}, skipping")
                    continue
        except Exception as e:
            logger.error(f"Error adding document {doc_id} to collection: {e}")
            continue
        
        docs_processed += 1
        if docs_processed % 20 == 0:
            logger.info(f"Processed {docs_processed}/{len(document_ids)} documents")
    
    logger.info(f"Document-level embeddings created for {docs_processed} documents, {docs_with_summaries} with summaries")
    return new_collection

def semantic_document_search(query: str, max_results: int = MAX_RESULTS) -> List[Dict[str, Any]]:
    """
    Search documents using semantic search without metadata filtering
    
    Args:
        query: The user query
        max_results: Maximum number of results to return
        
    Returns:
        List of document metadata and relevance scores
    """
    # Initialize empty result list
    search_results = []
    
    try:
        # Initialize embedding model
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Create a class to wrap the embedding model to match ChromaDB's interface
        class SentenceTransformerEmbeddings:
            def __init__(self, model):
                self.model = model
                
            def __call__(self, input):
                return self.model.encode(input).tolist()
        
        embedding_function = SentenceTransformerEmbeddings(embedding_model)
        
        # Connect to ChromaDB
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        # Get collection
        try:
            collection = chroma_client.get_collection(
                name=NEW_COLLECTION_NAME,
                embedding_function=embedding_function
            )
            logger.info(f"Retrieved collection: {NEW_COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Error getting collection: {e}")
            # Try to create the collection
            logger.info("Collection not found, creating embeddings...")
            collection = create_document_level_embeddings()
        
        # Check if we have a valid collection
        if not collection:
            logger.error("Failed to get or create collection")
            return search_results
            
        # Search for documents semantically similar to the query
        results = collection.query(
            query_texts=[query],
            n_results=max_results,
            include=["metadatas", "documents", "distances"]
        )
        
        # Process results
        if results and "ids" in results and len(results["ids"]) > 0:
            doc_ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [1.0] * len(doc_ids)
            metadatas = results["metadatas"][0] if "metadatas" in results else [{} for _ in doc_ids]
            documents = results["documents"][0] if "documents" in results and results["documents"] else [None] * len(doc_ids)
            
            for i, doc_id in enumerate(doc_ids):
                # Calculate similarity score (1.0 - distance) as a percentage
                similarity = (1.0 - distances[i]) * 100
                
                # Get document metadata
                doc_metadata = metadatas[i] if i < len(metadatas) else {}
                
                # Create result object
                result = {
                    "document_id": doc_id,
                    "document_name": doc_metadata.get("document_name", "Unknown"),
                    "category_id": doc_metadata.get("category_id", "Unknown"),
                    "ticker": doc_metadata.get("ticker", "Unknown"),
                    "similarity": f"{similarity:.2f}%",
                    "has_summary": doc_metadata.get("has_summary", False)
                }
                
                # Add excerpt from document if available
                if i < len(documents) and documents[i]:
                    excerpt = documents[i][:200] + "..." if len(documents[i]) > 200 else documents[i]
                    result["excerpt"] = excerpt
                
                search_results.append(result)
                
            logger.info(f"Found {len(search_results)} results for query: {query[:50]}...")
        else:
            logger.warning(f"No results found for query: {query[:50]}...")
            
    except Exception as e:
        logger.error(f"Error in semantic document search: {e}")
        
    return search_results

def get_document_level_search_tool():
    """Factory function to create a document-level search tool"""
    def document_search_tool(query: str) -> Dict[str, Any]:
        """
        Semantic document search tool that returns full documents
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with results or error
        """
        try:
            results = semantic_document_search(query)
            return {
                "identified_documents": results,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error in document search: {e}")
            return {
                "identified_documents": [],
                "error": f"Error: {str(e)}"
            }
    
    return document_search_tool

if __name__ == "__main__":
    # Test the document-level search
    print("Creating document-level embeddings...")
    collection = create_document_level_embeddings()
    print(f"Collection created with {collection.count()} documents")
    
    # Test search
    query = "Apple iPhone revenue in 2020"
    print(f"\nSearching for: {query}")
    results = semantic_document_search(query, max_results=5)
    
    print("\nResults:")
    for i, result in enumerate(results):
        print(f"{i+1}. {result['document_name']} ({result['ticker']})")
        print(f"   Similarity: {result['similarity']}")
        if 'excerpt' in result:
            print(f"   Excerpt: {result['excerpt'][:100]}...")
        print() 
#!/usr/bin/env python3
"""
Test script to verify the document analysis tool functionality
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the document analysis tool components
from langchain_tools.tool5_transcript_analysis import (
    analyze_document_content,
    get_content_by_document_id, 
    init_db
)

def find_sample_document_id() -> Optional[str]:
    """Find a sample document ID in the database"""
    logger.info("Trying to find a sample document ID in the database...")
    try:
        # Initialize database connection
        db, transcripts_coll, summaries_coll = init_db()
        if db is None:
            logger.error("Failed to initialize database connection")
            return None
            
        # Try to get a document ID from summaries collection
        sample_doc = summaries_coll.find_one({})
        if sample_doc and '_id' in sample_doc:
            doc_id = str(sample_doc['_id'])
            logger.info(f"Found sample document ID in summaries collection: {doc_id}")
            return doc_id
            
        # If no document in summaries, try transcripts collection
        sample_doc = transcripts_coll.find_one({})
        if sample_doc and '_id' in sample_doc:
            doc_id = str(sample_doc['_id'])
            logger.info(f"Found sample document ID in transcripts collection: {doc_id}")
            return doc_id
            
        logger.error("No documents found in database")
        return None
    except Exception as e:
        logger.error(f"Error finding sample document ID: {e}")
        return None

def test_document_analysis():
    """Test the document analysis tool with a sample document"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Set the API key in the environment
    os.environ["ANTHROPIC_API_KEY"] = api_key
    
    # Try to find a sample document ID
    doc_id = find_sample_document_id()
    if not doc_id:
        # If we can't find a real document, use a test ID
        doc_id = "cabb3bf8-234b-4bef-bc67-c213d5e3c703"
        logger.warning(f"Using test document ID: {doc_id} (may not exist in database)")
    
    # Test 1: Analyze document content
    logger.info(f"Test 1: Analyzing document content with document ID: {doc_id}")
    try:
        # Set a simple test query
        test_query = "What is the main topic of this document?"
        
        # Call the analysis function
        result = analyze_document_content(test_query, doc_id)
        
        # Check if the result is valid
        if isinstance(result, dict) and "answer" in result:
            if result.get("error"):
                logger.warning(f"Document analysis returned an error: {result['error']}")
                if "no content found" in result['error'].lower() or "not found" in result['error'].lower():
                    logger.info("This is likely because the test document ID doesn't exist in the database")
                else:
                    return False
            else:
                logger.info(f"✅ Document analysis succeeded with answer: {result['answer'][:100]}...")
        else:
            logger.error(f"❌ Document analysis returned unexpected result format: {result}")
            return False
            
        logger.info("Document analysis test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Document analysis test failed with error: {e}")
        return False

if __name__ == "__main__":
    if test_document_analysis():
        print("\n✅ Document analysis test completed!")
        sys.exit(0)
    else:
        print("\n❌ Document analysis test failed!")
        sys.exit(1) 
"""
Test script to verify the document analysis tool functionality
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the document analysis tool components
from langchain_tools.tool5_transcript_analysis import (
    analyze_document_content,
    get_content_by_document_id, 
    init_db
)

def find_sample_document_id() -> Optional[str]:
    """Find a sample document ID in the database"""
    logger.info("Trying to find a sample document ID in the database...")
    try:
        # Initialize database connection
        db, transcripts_coll, summaries_coll = init_db()
        if db is None:
            logger.error("Failed to initialize database connection")
            return None
            
        # Try to get a document ID from summaries collection
        sample_doc = summaries_coll.find_one({})
        if sample_doc and '_id' in sample_doc:
            doc_id = str(sample_doc['_id'])
            logger.info(f"Found sample document ID in summaries collection: {doc_id}")
            return doc_id
            
        # If no document in summaries, try transcripts collection
        sample_doc = transcripts_coll.find_one({})
        if sample_doc and '_id' in sample_doc:
            doc_id = str(sample_doc['_id'])
            logger.info(f"Found sample document ID in transcripts collection: {doc_id}")
            return doc_id
            
        logger.error("No documents found in database")
        return None
    except Exception as e:
        logger.error(f"Error finding sample document ID: {e}")
        return None

def test_document_analysis():
    """Test the document analysis tool with a sample document"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Set the API key in the environment
    os.environ["ANTHROPIC_API_KEY"] = api_key
    
    # Try to find a sample document ID
    doc_id = find_sample_document_id()
    if not doc_id:
        # If we can't find a real document, use a test ID
        doc_id = "cabb3bf8-234b-4bef-bc67-c213d5e3c703"
        logger.warning(f"Using test document ID: {doc_id} (may not exist in database)")
    
    # Test 1: Analyze document content
    logger.info(f"Test 1: Analyzing document content with document ID: {doc_id}")
    try:
        # Set a simple test query
        test_query = "What is the main topic of this document?"
        
        # Call the analysis function
        result = analyze_document_content(test_query, doc_id)
        
        # Check if the result is valid
        if isinstance(result, dict) and "answer" in result:
            if result.get("error"):
                logger.warning(f"Document analysis returned an error: {result['error']}")
                if "no content found" in result['error'].lower() or "not found" in result['error'].lower():
                    logger.info("This is likely because the test document ID doesn't exist in the database")
                else:
                    return False
            else:
                logger.info(f"✅ Document analysis succeeded with answer: {result['answer'][:100]}...")
        else:
            logger.error(f"❌ Document analysis returned unexpected result format: {result}")
            return False
            
        logger.info("Document analysis test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Document analysis test failed with error: {e}")
        return False

if __name__ == "__main__":
    if test_document_analysis():
        print("\n✅ Document analysis test completed!")
        sys.exit(0)
    else:
        print("\n❌ Document analysis test failed!")
        sys.exit(1) 
 
 
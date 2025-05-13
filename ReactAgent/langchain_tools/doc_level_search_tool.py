"""
Tool: Document-Level Semantic Search Tool

Uses pure semantic search at document level with no metadata filtering.
Returns whole documents based on their relevance to the query.
"""

import logging
import sys
import os
from typing import Dict, Any, Callable, Optional

# Add parent directory to path to import document_level_search
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the document-level search implementation
from final_document_level_search import get_document_level_search_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_doc_level_search_tool() -> Callable:
    """
    Factory function to get the document-level semantic search tool
    
    Returns:
        A callable document-level search tool for use with Langchain
    """
    # Get the core document search tool
    doc_search_tool = get_document_level_search_tool()
    
    # Wrap it for Langchain
    def langchain_doc_search_tool(query: str) -> str:
        """
        Wrapper for document-level semantic search, compatible with Langchain
        
        Args:
            query: The search query
            
        Returns:
            A formatted string with search results
        """
        try:
            # Call the document search tool
            result = doc_search_tool(query)
            
            # Check for errors
            if result["error"]:
                return f"Error searching documents: {result['error']}"
            
            # Format the results
            documents = result["identified_documents"]
            if not documents:
                return f"No relevant documents found for query: {query}"
            
            # Build a response string
            response = f"Found {len(documents)} relevant documents for '{query}':\n\n"
            
            # Add each document to the response
            for i, doc in enumerate(documents):
                doc_name = doc.get("document_name", "Unknown")
                ticker = doc.get("ticker", "Unknown")
                similarity = doc.get("similarity", "Unknown")
                document_id = doc.get("document_id", "Unknown")
                
                # Make the document ID very prominent in the output
                response += f"{i+1}. {doc_name} ({ticker}) - Relevance: {similarity}\n"
                response += f"   DOCUMENT_ID: {document_id} (Use this ID for document analysis)\n"
                
                # Add excerpt if available
                if "excerpt" in doc:
                    excerpt = doc["excerpt"]
                    # Truncate excerpt if too long
                    if len(excerpt) > 300:
                        excerpt = excerpt[:300] + "..."
                    response += f"   Excerpt: {excerpt}\n"
                
                response += "\n"
            
            # Add a reminder at the end about using document IDs
            response += "IMPORTANT: When analyzing specific documents, use the exact DOCUMENT_ID value shown above, not the document name.\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in document level search tool: {e}")
            return f"Error searching documents: {str(e)}"
    
    return langchain_doc_search_tool

# For testing
if __name__ == "__main__":
    print("Testing Document-Level Search Tool...")
    test_query = "NVIDIA AI strategy in 2020"
    search_tool = get_doc_level_search_tool()
    results = search_tool(test_query)
    
    print("\nResults:")
    if results.get("error"):
        print(f"Error: {results['error']}")
    else:
        print(f"Found {len(results.get('identified_documents', []))} relevant documents")
        for i, doc in enumerate(results.get("identified_documents", []), 1):
            print(f"\nDocument {i}:")
            print(f"  Name: {doc.get('document_name', 'Unknown')}")
            print(f"  Company: {doc.get('ticker', 'Unknown')}")
            print(f"  Similarity: {doc.get('similarity', 'Unknown')}")
            print(f"  Document ID: {doc.get('document_id', 'Unknown')}") 
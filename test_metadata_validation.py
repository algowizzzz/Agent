#!/usr/bin/env python3

import json
import logging
from langchain_tools.tool_factory import validate_metadata_lookup_response

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Test the validate_metadata_lookup_response function"""
    
    # Create a test response with all required fields of correct types
    test_response = {
        "relevant_category_id": "MSFT",
        "relevant_doc_ids": ["id1", "id2"],
        "category_summary_available": True,
        "doc_ids_with_summaries": ["id1"]
    }
    
    # Validate the response
    logger.info("Validating correct metadata response...")
    is_valid, errors = validate_metadata_lookup_response(test_response)
    
    # Print the results
    print(f"\nValidation Result: {'Valid' if is_valid else 'Invalid'}")
    if not is_valid:
        print("Errors found:")
        for error in errors:
            print(f"- {error}")
    
    # Print the test response for reference
    print("\nTest Response:")
    print(json.dumps(test_response, indent=2))
    
if __name__ == "__main__":
    main() 
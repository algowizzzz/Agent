"""
Tool 4: LLM-Driven Metadata Lookup Tool

Uses an LLM to analyze a query against a provided metadata context 
to identify relevant category and document IDs, and check for available summaries.
WARNING: Passing all metadata in the prompt is not scalable.
"""

import logging
import re
import json
import os
from typing import Dict, Any, List, Optional, Callable, Set
from pymongo import MongoClient
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage
from .config import sanitize_json_response # Reverted to relative import
from langchain_core.language_models import BaseChatModel # Add if not present

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Connection --- 
def get_mongodb_client():
    """Get MongoDB client with proper error handling."""
    try:
        client = MongoClient('mongodb://localhost:27017/')
        client.admin.command('ping') # Test connection
        logger.info("Metadata Tool: MongoDB connection successful.")
        return client
    except Exception as e:
        logger.error(f"Metadata Tool: MongoDB connection failed: {e}")
        return None

def init_db():
    """Initialize database connection."""
    client = get_mongodb_client()
    if client is None:
        return None
    return client['earnings_transcripts']

# --- Metadata Fetching --- 
def fetch_all_metadata(db) -> Optional[Dict[str, Any]]:
    """Fetch minimal transcript details, category mappings, and summary availability for ALL documents."""
    if db is None:
        logger.error("Metadata Tool: Database connection is None.")
        return None
    try:
        logger.info("Metadata Tool: Fetching minimal metadata for ALL documents...")
        
        # 1. Fetch minimal transcript document details (ID, category_id, date, quarter, fiscal_year)
        documents = {}
        category_to_doc_ids = {}
        all_doc_ids = set()
        
        # Fetch ALL documents, only essential fields
        for doc in db.transcripts.find({}, {"document_id": 1, "category_id": 1, "date": 1, "quarter": 1, "fiscal_year": 1, "_id": 0}):
            doc_id_str = doc.get("document_id")
            category_id = doc.get("category_id")
            if not doc_id_str or not category_id:
                continue

            all_doc_ids.add(doc_id_str)
            if category_id not in category_to_doc_ids:
                category_to_doc_ids[category_id] = []
            category_to_doc_ids[category_id].append(doc_id_str)

            # Keep only essential details
            details = {"category_id": category_id} 
            if doc.get("date"):
                doc_date = doc["date"]
                if isinstance(doc_date, datetime):
                    details["date"] = doc_date.strftime("%Y-%m-%d") 
                elif isinstance(doc_date, str): 
                    # Ensure date is in YYYY-MM-DD format
                    try:
                        details["date"] = datetime.strptime(doc_date[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
                    except ValueError:
                        logger.warning(f"Metadata Tool: Could not parse date format for doc {doc_id_str}: {doc_date}")
            else:
                details["date"] = None
                
            if doc.get("quarter") and doc.get("fiscal_year"):
                details["quarter"] = f"Q{doc['quarter']} {doc['fiscal_year']}"
            else:
                details["quarter"] = None
                
            documents[doc_id_str] = details

        logger.info(f"Metadata Tool: Fetched minimal details for {len(documents)} documents across {len(category_to_doc_ids)} categories.")

        # 2. Fetch Document IDs with available individual summaries (for ALL docs)
        doc_ids_with_summaries = set()
        try:
            # Fetch all summary IDs
            summary_cursor = db.document_summaries.find({}, {"document_id": 1, "_id": 0})
            doc_ids_with_summaries = {s['document_id'] for s in summary_cursor if s.get('document_id')}
            logger.info(f"Metadata Tool: Found {len(doc_ids_with_summaries)} documents with individual summaries (total).")
        except Exception as e:
            logger.warning(f"Metadata Tool: Could not fetch document summary availability: {e}")

        # 3. Fetch Category IDs with available synthesized summaries (for ALL categories)
        categories_with_summaries = set()
        try:
            # Fetch all category summary IDs
            cat_summary_cursor = db.category_summaries.find({"summary_type": "category_synthesis"}, {"category_id": 1, "_id": 0})
            categories_with_summaries = {s['category_id'] for s in cat_summary_cursor if s.get('category_id')}
            logger.info(f"Metadata Tool: Found {len(categories_with_summaries)} categories with synthesized summaries (total).")
        except Exception as e:
            logger.warning(f"Metadata Tool: Could not fetch category summary availability: {e}")

        return {
            "categories": category_to_doc_ids, # ALL Categories -> List of ALL Document IDs
            "documents": documents, # ALL Document IDs -> Minimal Details {category_id, date, quarter}
            "doc_ids_with_summaries": doc_ids_with_summaries, # ALL docs with summaries
            "categories_with_summaries": categories_with_summaries, # ALL categories with summaries
            "departments_with_summaries": set() # Simplified
        }
        
    except Exception as e:
        logger.error(f"Metadata Tool: Failed to fetch metadata: {e}", exc_info=True)
        return None

# --- LLM Prompt Formatting ---
def format_metadata_prompt(query: str, metadata: Dict[str, Any]) -> str:
    """Formats the prompt for the LLM metadata lookup with minimal document details, requesting structured JSON output."""
    # Log a sample of the raw documents metadata before conversion
    raw_docs_sample = dict(list(metadata.get("documents", {}).items())[:2]) # Log first 2 entries
    logger.debug(f"Metadata Tool: Raw documents metadata sample (minimal): {json.dumps(raw_docs_sample, separators=(',', ':'))}")

    # Convert metadata to strings for the prompt, using compact JSON format
    categories_str = json.dumps(metadata.get("categories", {}), separators=(',', ':'))
    # Ensure only minimal fields (category_id, date, quarter) are in documents_str
    minimal_documents = { 
        doc_id: { 
            k: v for k, v in details.items() if k in ["category_id", "date", "quarter"] 
        } 
        for doc_id, details in metadata.get("documents", {}).items() 
    }
    documents_str = json.dumps(minimal_documents, separators=(',', ':'))
    doc_ids_with_summaries_str = json.dumps(list(metadata.get("doc_ids_with_summaries", set())), separators=(',', ':'))
    categories_with_summaries_str = json.dumps(list(metadata.get("categories_with_summaries", set())), separators=(',', ':'))

    # --- Log individual component lengths --- 
    logger.debug(f"Metadata Tool: Pre-truncation lengths (minimal doc details) -> Categories: {len(categories_str)}, Documents: {len(documents_str)}, DocSummaries: {len(doc_ids_with_summaries_str)}, CatSummaries: {len(categories_with_summaries_str)}")

    # --- Basic Truncation (Re-evaluate if still needed) ---
    max_len = 30000 # Increase limit as we send less detail per doc
    total_len = len(categories_str) + len(documents_str) + len(doc_ids_with_summaries_str) + len(categories_with_summaries_str)
    if total_len > max_len:
        logger.warning(f"Metadata Tool: Metadata context length ({total_len}) still exceeds limit ({max_len}). Simple truncation applied (may break JSON). Consider reducing data passed.")
        # Proportional truncation (very rough)
        scale = max_len / total_len
        categories_str = categories_str[:int(len(categories_str) * scale)]
        documents_str = documents_str[:int(len(documents_str) * scale)] # This is the main part now
        doc_ids_with_summaries_str = doc_ids_with_summaries_str[:int(len(doc_ids_with_summaries_str) * scale)]
        categories_with_summaries_str = categories_with_summaries_str[:int(len(categories_with_summaries_str) * scale)]
    else:
         logger.info(f"Metadata Tool: Metadata context length ({total_len}) fits within limit ({max_len}). No truncation needed.")

    # --- Updated Prompt Template with Minimal Document Info --- 
    prompt_template = """You are a metadata analysis assistant. Your task is to identify relevant information resources based on a user query and provided metadata context.

METADATA CONTEXT:

1. Document Details (Document ID -> {{category_id, date, quarter}}):
{documents_metadata}

2. Category Mappings (Category ID -> List of associated Document IDs):
{categories_metadata}

3. Availability of Pre-computed Summaries:
   - Document IDs with Individual Summaries: {doc_ids_with_summaries}
   - Category IDs with Synthesized Summaries: {categories_with_summaries}

USER QUERY: {query}

Based ONLY on the User Query and the METADATA CONTEXT provided, perform the following steps:
1. Identify the primary Category ID (e.g., company ticker like 'MSFT', 'AAPL') mentioned or implied in the User Query. If none, use null.
2. Scan the 'Document Details' context. Use the 'category_id', 'date' (YYYY-MM-DD), and 'quarter' (e.g., 'Q3 2020') fields to find documents matching the identified Category ID and any time period mentioned in the User Query.
3. If the query asks for 'most recent', use the 'date' field to select the document(s) with the latest date(s) for the relevant category.
4. Select up to 5 of the most relevant Document IDs based on the category and time period matching. Prioritize exact matches for quarter/year if specified.
5. Check if a synthesized Category Summary is available for the identified Category ID (from step 1) by seeing if it's in the 'Category IDs with Synthesized Summaries' list.
6. Create a list of the selected relevant Document IDs (from step 4) for which individual summaries are available by checking against the 'Document IDs with Individual Summaries' list.

Format your response strictly as a JSON object containing the following keys:
- "relevant_category_id": [string|null]
- "relevant_doc_ids": [list of strings]
- "category_summary_available": [boolean]
- "doc_ids_with_summaries": [list of strings]

Example Response:
```json
{{
  "relevant_category_id": "MSFT",
  "relevant_doc_ids": ["doc-id-q3-2020", "doc-id-q3-2020-alt"],
  "category_summary_available": true,
  "doc_ids_with_summaries": ["doc-id-q3-2020"]
}}
```

CRITICAL: Your response MUST be a single valid JSON object enclosed in ```json\n...\n``` blocks, containing only the specified keys and value types. Do not include any other text, comments, or explanations outside the JSON structure.
"""

    return prompt_template.format(
        documents_metadata=documents_str,
        categories_metadata=categories_str,
        doc_ids_with_summaries=doc_ids_with_summaries_str,
        categories_with_summaries=categories_with_summaries_str,
        query=query
    )

# --- Main Tool Logic (LLM Based + JSON Post-processing) ---
# MODIFIED: Added llm parameter, removed internal LLM creation
def llm_metadata_lookup(query_term: str, llm: BaseChatModel) -> Dict[str, Any]:
    """Uses the provided LLM instance to find relevant category/document IDs and check summary availability,
       splitting the document metadata to fit context limits.
       Expects JSON output from LLM.
       Returns: Structured dictionary with aggregated findings or error.
    """
    # Default return structure in case of errors
    default_error_return = {
        "relevant_category_id": None,
        "relevant_doc_ids": [],
        "category_summary_available": False,
        "doc_ids_with_summaries": [],
        "error": "Tool logic failed", # More specific errors set below
    }

    logger.info(f"Metadata Tool: Received query: '{query_term[:100]}...'")
    db = init_db()
    if db is None:
        default_error_return["error"] = "Failed to connect to database"
        return default_error_return

    # Fetch all minimal metadata
    metadata = fetch_all_metadata(db)
    if metadata is None:
        default_error_return["error"] = "Failed to fetch metadata"
        return default_error_return

    # Extract validation sets and common metadata
    valid_category_ids = set(metadata.get("categories", {}).keys())
    valid_doc_ids = set(metadata.get("documents", {}).keys())
    doc_ids_with_summaries_set = metadata.get("doc_ids_with_summaries", set())
    categories_with_summaries_set = metadata.get("categories_with_summaries", set())
    all_categories_map = metadata.get("categories", {})
    all_doc_summaries_list = list(doc_ids_with_summaries_set)
    all_cat_summaries_list = list(categories_with_summaries_set)

    # Split the documents metadata into two halves
    all_documents_dict = metadata.get("documents", {})
    doc_items = list(all_documents_dict.items())
    split_point = len(doc_items) // 2
    docs_part1 = dict(doc_items[:split_point])
    docs_part2 = dict(doc_items[split_point:])

    logger.info(f"Metadata Tool: Splitting {len(all_documents_dict)} documents into two parts: {len(docs_part1)} and {len(docs_part2)}")

    # --- Function to perform single LLM call ---
    # MODIFIED: Added llm parameter
    def _call_llm_with_metadata(documents_part: Dict[str, Any], part_num: int, llm_instance: BaseChatModel) -> Optional[Dict[str, Any]]:
        metadata_chunk = {
            "categories": all_categories_map, # Send all categories
            "documents": documents_part,
            "doc_ids_with_summaries": all_doc_summaries_list, # Send all summary info
            "categories_with_summaries": all_cat_summaries_list
        }
        try:
            prompt = format_metadata_prompt(query_term, metadata_chunk)
            logger.info(f"Metadata Tool: Sending request to LLM (Part {part_num})...")
            # Use the passed LLM instance
            response = llm_instance.invoke(prompt)
            logger.debug(f"Metadata Tool: Received response object (Part {part_num}) of type: {type(response)}")
            
            # Extract raw output
            raw_llm_output = ""
            if isinstance(response, AIMessage) and isinstance(response.content, str):
                raw_llm_output = response.content.strip()
            elif isinstance(response, str):
                raw_llm_output = response.strip()
            else:
                logger.warning(f"Metadata Tool: Unexpected LLM response format (Part {part_num}): {type(response)}")
                return None # Indicate failure

            logger.debug(f"Metadata Tool: Raw LLM output received (Part {part_num}): {repr(raw_llm_output)}")
            
            # Parse JSON
            parsed_json = json.loads(sanitize_json_response(raw_llm_output))
            logger.info(f"Metadata Tool: Successfully parsed JSON response (Part {part_num}) from LLM.")
            return parsed_json
        except json.JSONDecodeError as json_err:
            logger.error(f"Metadata Tool: Failed to parse JSON response (Part {part_num}): {json_err}\nRaw response: {raw_llm_output}")
            return None
        except Exception as e:
            logger.error(f"Metadata Tool: Error during LLM call or processing (Part {part_num}): {e}", exc_info=True)
            return None

    # --- Make the two LLM calls ---
    # MODIFIED: Pass the llm instance
    result1 = _call_llm_with_metadata(docs_part1, 1, llm_instance=llm)
    result2 = _call_llm_with_metadata(docs_part2, 2, llm_instance=llm)

    # --- Aggregate the results ---
    final_results = {
        "relevant_category_id": None,
        "relevant_doc_ids": [],
        "category_summary_available": False,
        "doc_ids_with_summaries": [],
        "error": None
    }
    
    # Aggregate Document IDs
    all_found_doc_ids = set()
    if result1 and isinstance(result1.get("relevant_doc_ids"), list):
        all_found_doc_ids.update(result1["relevant_doc_ids"])
    if result2 and isinstance(result2.get("relevant_doc_ids"), list):
        all_found_doc_ids.update(result2["relevant_doc_ids"])
        
    # Validate aggregated doc IDs
    validated_doc_ids = []
    for doc_id in all_found_doc_ids:
        if isinstance(doc_id, str) and doc_id in valid_doc_ids:
            validated_doc_ids.append(doc_id)
        else:
            logger.warning(f"Metadata Tool: LLM returned aggregated doc_id '{doc_id}' not found in metadata or invalid type.")
    final_results["relevant_doc_ids"] = validated_doc_ids[:5] # Enforce limit after aggregation
    
    # Aggregate Doc IDs with Summaries
    all_found_docs_with_summaries = set()
    if result1 and isinstance(result1.get("doc_ids_with_summaries"), list):
        all_found_docs_with_summaries.update(result1["doc_ids_with_summaries"])
    if result2 and isinstance(result2.get("doc_ids_with_summaries"), list):
        all_found_docs_with_summaries.update(result2["doc_ids_with_summaries"])
         
    # Filter based on the final validated relevant docs
    final_docs_with_summaries = [ 
        doc_id for doc_id in all_found_docs_with_summaries 
        if doc_id in final_results["relevant_doc_ids"] 
    ]
    final_results["doc_ids_with_summaries"] = final_docs_with_summaries
    
    # Determine Category ID (Prioritize result1, then result2)
    cat_id1 = result1.get("relevant_category_id") if result1 else None
    cat_id2 = result2.get("relevant_category_id") if result2 else None
    
    chosen_cat_id = None
    # Ensure cat_id1 is either a valid string or None
    if cat_id1 and isinstance(cat_id1, str) and cat_id1 in valid_category_ids:
        chosen_cat_id = cat_id1
    # Ensure cat_id2 is either a valid string or None
    elif cat_id2 and isinstance(cat_id2, str) and cat_id2 in valid_category_ids:
        chosen_cat_id = cat_id2
    # Explicitly ensure chosen_cat_id is a valid string or None
    elif cat_id1 == "null" or cat_id1 == "":
        logger.warning(f"Metadata Tool: LLM (Part 1) returned invalid category_id string '{cat_id1}', converting to None.")
        chosen_cat_id = None
    elif cat_id2 == "null" or cat_id2 == "":
        logger.warning(f"Metadata Tool: LLM (Part 2) returned invalid category_id string '{cat_id2}', converting to None.")
        chosen_cat_id = None
    elif cat_id1: # Log if invalid
        logger.warning(f"Metadata Tool: LLM (Part 1) returned category_id '{cat_id1}' not found in metadata.")
    elif cat_id2:
        logger.warning(f"Metadata Tool: LLM (Part 2) returned category_id '{cat_id2}' not found in metadata.")
         
    # Ensure the final result is definitely either a string or None
    if chosen_cat_id is not None and not isinstance(chosen_cat_id, str):
        logger.warning(f"Metadata Tool: Forcing non-string category_id '{chosen_cat_id}' ({type(chosen_cat_id)}) to None")
        chosen_cat_id = None
    
    final_results["relevant_category_id"] = chosen_cat_id
    
    # Determine Category Summary Availability
    if chosen_cat_id:
        final_results["category_summary_available"] = chosen_cat_id in categories_with_summaries_set
        
    if not result1 and not result2:
        final_results["error"] = "Both LLM calls failed to produce valid results."
    elif not final_results["relevant_doc_ids"]:
        logger.warning("Metadata Tool: Aggregated results contain no relevant document IDs.")

    logger.info(f"Metadata Tool: Aggregated lookup results: {final_results}")
    return final_results

# --- Tool Factory Function ---
# MODIFIED: Added api_key parameter, instantiate LLM here, return wrapper lambda
def get_metadata_lookup_tool(api_key: Optional[str] = None) -> Callable:
    """Factory function to create and return the LLM metadata lookup tool."""
    logger.info("Metadata Tool Factory: Creating tool instance.")

    # --- Create LLM Instance ---
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Metadata Tool Factory: ANTHROPIC_API_KEY not provided or set in environment.")
        # Return a dummy function that reports the error
        def error_func(query_term: str):
             logger.error("Metadata Tool executing with error: API Key missing.")
             return {"error": "ANTHROPIC_API_KEY not configured for metadata tool"}
        # Add dunder attributes to the error function for consistency
        error_func.__name__ = "metadata_lookup_error_tool"
        error_func.__doc__ = "Error: Tool could not be initialized due to missing API key."
        return error_func

    try:
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0,
            max_tokens=1024, # Ensure sufficient tokens for JSON output
            anthropic_api_key=api_key
        )
        logger.info("Metadata Tool Factory: LLM initialized successfully.")
    except Exception as e:
        logger.error(f"Metadata Tool Factory: Failed to initialize LLM: {e}")
        def error_func(query_term: str):
             logger.error(f"Metadata Tool executing with error: LLM Init failed ({e}).")
             return {"error": f"LLM Initialization Error: {e}"}
        # Add dunder attributes to the error function
        error_func.__name__ = "metadata_lookup_error_tool"
        error_func.__doc__ = f"Error: Tool could not be initialized due to LLM error ({e})."
        return error_func

    # --- Tool Function Wrapper ---
    # Return a function that takes only the query and calls the main logic with the LLM
    def tool_wrapper(query_term: str):
        # Ensure the LLM instance is passed to the core logic function
        return llm_metadata_lookup(query_term, llm=llm)

    # Set standard dunder attributes for better introspection if needed
    tool_wrapper.__name__ = "llm_metadata_lookup_tool"
    tool_wrapper.__doc__ = (
        "Identifies relevant transcripts and available summaries (category, individual) based on a user query "
        "and MINIMAL metadata context for ALL documents. Input is the user query string. Returns a structured dictionary with findings."
    )
    return tool_wrapper # Return the wrapper function

# Example Usage (for testing)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM-based Metadata Lookup.")
    parser.add_argument("query_term", help="Natural language query or term to search for.")
    args = parser.parse_args()
    
    result = get_metadata_lookup_tool()(args.query_term)
    print(json.dumps(result, indent=2)) 
# Wrapper for earnings call transcript search/summary 
import logging
import os
from typing import Dict, Any, Optional, List

from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

# Import the actual tool implementations
from langchain_tools.tool2_category import category_summary_tool
from langchain_tools.tool4_metadata_lookup import get_metadata_lookup_tool
from langchain_tools.tool5_transcript_analysis import get_document_analysis_tool

logger = logging.getLogger(__name__)

# Implement proper wrapper functions that use the actual tools
def create_category_tool_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for category tool. Input format: '<query>, category=<CATEGORY_ID>'
    """
    logger.info(f"[Transcript Tool] Category tool called with: {input_str[:100]}...")
    
    # Parse query and category_id from the input string
    query = input_str
    category_id = None
    import re
    match = re.search(r"category=([\w\.\-]+)", input_str, re.IGNORECASE)
    if match:
        category_id = match.group(1)
        # Remove the category part from the query string
        query = re.sub(r",?\s*category=[\w\.\-]+$", "", query, flags=re.IGNORECASE).strip().rstrip(",")
    else:
        logger.warning(f"Category ID not found in input format: '{input_str}'")
        return {"error": "Category ID missing in input format 'query, category=<ID>'", "summary": None, "relevant_doc_ids": []}
    
    try:
        # Call the actual category_summary_tool
        return category_summary_tool(query, category_id)
    except Exception as e:
        logger.error(f"Error in category tool: {e}", exc_info=True)
        return {"error": f"Error in category tool: {str(e)}", "summary": None, "relevant_doc_ids": []}

def create_metadata_lookup_wrapper(api_key: Optional[str] = None):
    """
    Create the metadata lookup tool using the actual implementation
    """
    try:
        # Get the actual tool implementation
        metadata_lookup_fn = get_metadata_lookup_tool(api_key)
        
        def metadata_lookup_wrapper(query_term: str) -> Dict[str, Any]:
            logger.info(f"[Transcript Tool] Metadata lookup called with: {query_term[:100]}...")
            try:
                return metadata_lookup_fn(query_term)
            except Exception as e:
                logger.error(f"Error in metadata lookup: {e}", exc_info=True)
                return {
                    "relevant_category_id": None,
                    "relevant_doc_ids": [],
                    "category_summary_available": False,
                    "doc_ids_with_summaries": [],
                    "error": f"Error in metadata lookup: {str(e)}"
                }
                
        return metadata_lookup_wrapper
    except Exception as e:
        logger.error(f"Failed to initialize metadata lookup tool: {e}", exc_info=True)
        # Return a function that reports the initialization error
        return lambda query: {
            "relevant_category_id": None,
            "relevant_doc_ids": [],
            "category_summary_available": False,
            "doc_ids_with_summaries": [],
            "error": f"Failed to initialize metadata lookup tool: {str(e)}"
        }

def create_document_analysis_wrapper(api_key: Optional[str] = None):
    """
    Create the document analysis tool using the actual implementation
    """
    try:
        # Get the actual tool implementation
        document_analysis_fn = get_document_analysis_tool(api_key)
        
        def document_analysis_wrapper(input_str: str) -> Dict[str, Any]:
            logger.info(f"[Transcript Tool] Document analysis called with: {input_str[:100]}...")
            
            # Parse query and document_id from the input string
            query = input_str
            doc_id = None
            import re
            match = re.search(
                r"document_id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                input_str,
                re.IGNORECASE,
            )
            if match:
                doc_id = match.group(1)
                # Remove the parameter part from the query string
                query = re.sub(r",?\s*document_id=[0-9a-f\-]+\s*$", "", query, flags=re.IGNORECASE).strip().rstrip(",")
            else:
                logger.warning(f"Document ID not found in input format: '{input_str}'")
                return {"answer": None, "error": "Document ID missing in input format 'query, document_id=<UUID>'"}
            
            try:
                # Call the actual document analysis tool
                return document_analysis_fn(query, doc_id)
            except Exception as e:
                logger.error(f"Error in document analysis: {e}", exc_info=True)
                return {"answer": None, "error": f"Error in document analysis: {str(e)}"}
                
        return document_analysis_wrapper
    except Exception as e:
        logger.error(f"Failed to initialize document analysis tool: {e}", exc_info=True)
        # Return a function that reports the initialization error
        return lambda query: {"answer": None, "error": f"Failed to initialize document analysis tool: {str(e)}"}

# Define the prompt for the Transcript Agent
TRANSCRIPT_AGENT_PROMPT_TEMPLATE = """You are an expert **Equity Research Analyst** specializing in analyzing company earnings calls and related documents.
Your primary goal is to answer the user's query by producing a **concise analytical summary/report** based *only* on the information found within the relevant documents or their pre-computed summaries. 
**(Note: Transcript data covers roughly 2016 to 2020).**

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: As an analyst, I need to break down the question and gather information step-by-step.
1. First, identify the company categories (tickers like AAPL, MSFT, NVDA) mentioned in the Question.
2. For **each** identified category, call the `category_tool` to get a high-level summary. The Action Input MUST be in the format: '<Brief query about category>, category=<CATEGORY_ID>' (e.g., 'Summarize recent growth, category=AAPL').
3. Review the results (`Observation`) from all `category_tool` calls. Is this high-level information sufficient to answer the original Question?
4. **If** the high-level summaries are insufficient OR the Question asks for specific examples/details from specific quarters, THEN I need to find specific documents. Use the `metadata_lookup_tool` with the original Question (or relevant parts) to find relevant document IDs for the necessary categories and time periods.
5. Carefully examine the JSON output from `metadata_lookup_tool`. Pay close attention to the `relevant_doc_ids` list.
6. **CRITICAL:** If the `metadata_lookup_tool` was used and the `relevant_doc_ids` list in its JSON output is empty, it means no specific relevant documents were found. Synthesize your Final Answer using the information gathered so far (from `category_tool`), explaining that more specific details could not be found.
7. If `relevant_doc_ids` is NOT empty, proceed to analyze the specific documents. For **each** `document_id` in the `relevant_doc_ids` list: Call the `document_content_analysis_tool`. The Action Input MUST be in the format: '<Original Query or relevant sub-query>, document_id=<uuid>' (e.g., 'What was revenue growth?, document_id=uuid-goes-here'). Analyze the 'Observation' (the analysis result) returned by each call.
8. After gathering information from `category_tool` and potentially `document_content_analysis_tool`, synthesize the key findings from all relevant 'Observation' steps into your Final Answer.

Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action. **CRITICAL: Ensure the input strictly matches the format specified in the tool's description.** Examples:
    - For 'category_tool': `query, category=<ticker>` (e.g., `summarize performance, category=AAPL`) 
    - For 'metadata_lookup_tool': `natural language query` (e.g., `MSFT earnings call Q4 2019`)
    - For 'document_content_analysis_tool': `query, document_id=<uuid>` (e.g., `What was revenue growth?, document_id=123e4567-e89b-12d3-a456-426614174000`) --- **Provide only ONE document_id per call.**
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times as you gather information)
Thought: I have gathered sufficient information from the category summaries and/or specific document analyses. Now I will synthesize these findings into a concise analyst report answering the original question. OR If insufficient information was found, I will state that clearly.
Final Answer: **[Analyst Report Format]**
Synthesize the key findings from the 'Observation' steps above into a clear, concise report that directly answers the user's original 'Question'. Structure the report logically. Focus on the aspects relevant to an equity analyst. Explicitly state if the answer relies only on category summaries or includes details from specific documents. **If insufficient information was found (e.g., no relevant category summaries, no specific documents found by metadata lookup), state that clearly and explain that the query could not be fully answered based on the available data (mentioning the 2016-2020 date range if relevant).**

Begin!

Question: {input}
Thought:{agent_scratchpad}
"""
TRANSCRIPT_AGENT_PROMPT = PromptTemplate.from_template(TRANSCRIPT_AGENT_PROMPT_TEMPLATE)

def run_transcript_agent(query: str, llm: BaseChatModel, api_key: Optional[str] = None) -> str:
    """
    Runs the specialized transcript analysis agent.
    Handles initialization of internal tools and execution.
    Returns the final analysis as a string, or an error message string.
    """
    logger.info(f"[Transcript Agent Tool] Initializing for query: {query[:100]}...")
    try:
        # --- Instantiate Internal Tools with actual implementations ---
        metadata_lookup_tool_instance = create_metadata_lookup_wrapper(api_key)
        document_analysis_tool_instance = create_document_analysis_wrapper(api_key)
        
        internal_tools = [
            Tool(
                name="category_tool",
                func=create_category_tool_wrapper,
                description="Analyzes summaries for a specific category (company ticker)... Input format: '<query>, category=<CATEGORY_ID>'.",
            ),
            Tool(
                name="metadata_lookup_tool",
                func=metadata_lookup_tool_instance,
                description="Finds relevant document IDs and checks for summaries... Input is the natural language query. Output is JSON.",
            ),
            Tool(
                name="document_content_analysis_tool",
                func=document_analysis_tool_instance,
                description="Analyzes content of a specific document_id... Input MUST be: '<query>, document_id=<uuid>'.",
            ),
        ]
        logger.info(f"[Transcript Agent Tool] Internal tools created: {[t.name for t in internal_tools]}")

        # --- Create React Agent and Executor --- 
        react_agent = create_react_agent(llm, internal_tools, TRANSCRIPT_AGENT_PROMPT)
        agent_executor = AgentExecutor(
            agent=react_agent,
            tools=internal_tools,
            handle_parsing_errors="Check your output and make sure it conforms to the expected format!",
            verbose=True # Good for debugging this sub-agent
        )

        # --- Execute the Sub-Agent --- 
        logger.info("[Transcript Agent Tool] Executing sub-agent...")
        result = agent_executor.invoke({"input": query})
        output = result.get("output", "Transcript agent finished but provided no output.")
        logger.info(f"[Transcript Agent Tool] Execution finished. Output: {output[:200]}...")
        return output

    except Exception as e:
        logger.error(f"[Transcript Agent Tool] Error during execution: {e}", exc_info=True)
        return f"Error: Transcript analysis failed. Details: {type(e).__name__}: {e}" 
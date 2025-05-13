# Wrapper for earnings call transcript search/summary 
import logging
import os
from typing import Dict, Any, Optional, List

from langchain.agents import AgentExecutor, Tool, create_react_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

# Import the actual tool implementations
from langchain_tools.tool2_category import category_summary_tool
from langchain_tools.doc_level_search_tool import get_doc_level_search_tool
from langchain_tools.tool5_transcript_analysis import get_document_analysis_tool

logger = logging.getLogger(__name__)

# Implement proper wrapper functions that use the actual tools
def create_category_tool_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for category tool. Input format: '<query>, category: <category_id>'
    Example: 'What are the business segments?, category: 8ba26d53'
    """
    # Try to parse the input
    parts = input_str.split('category:')
    if len(parts) != 2:
        return {"error": f"Invalid input format: {input_str}. Expected format: '<query>, category: <category_id>'"}
    
    query = parts[0].strip().strip(',')
    category_id = parts[1].strip()
    
    # Call the actual tool
    result = category_summary_tool(query, category_id)
    return result

def create_doc_level_search_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for document-level search tool. Accepts a natural language query.
    Example: 'Find earnings calls discussing NVIDIA AI strategy in 2020'
    """
    # Call the document-level search tool
    doc_level_search_tool = get_doc_level_search_tool()
    result = doc_level_search_tool(input_str)
    
    # Return the results with proper formatting
    return {"result": result}

def create_document_analysis_wrapper(input_str: str) -> Dict[str, Any]:
    """
    Wrapper for document analysis tool. Input format: '<query>, document: <document_id>'
    Example: 'Analyze the revenue growth, document: ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3'
    """
    # Try to parse the input
    parts = input_str.split('document:')
    if len(parts) != 2:
        return {"error": f"Invalid input format: {input_str}. Expected format: '<query>, document: <document_id>'"}
    
    query = parts[0].strip().strip(',')
    document_id = parts[1].strip()
    
    # Call the actual tool
    document_analysis_tool = get_document_analysis_tool()
    result = document_analysis_tool(query, document_id)
    return result

# Create the Earnings Call Tool
def create_earnings_call_toolset(llm: BaseChatModel) -> List[Tool]:
    """Creates the tools for earnings call analysis"""
    
    tools = [
        Tool(
            name="DocumentLevelSearch",
            func=create_doc_level_search_wrapper,
            description="""
            Use this tool to search across all earnings call transcripts without filtering.
            Input should be a detailed natural language query describing what you're looking for.
            This tool performs semantic search to find the most relevant documents based on meaning.
            
            Example inputs:
            - "Find earnings calls discussing NVIDIA AI chip strategy"
            - "Which companies mentioned supply chain issues in Q1 2020?"
            - "Find earnings calls where Apple discusses iPhone revenue growth"
            - "Which semiconductor companies discussed manufacturing challenges in 2019?"
            """
        ),
        Tool(
            name="CategorySummary",
            func=create_category_tool_wrapper,
            description="""
            Use this tool to get summaries based on a specific category/company.
            Input format: '<query>, category: <category_id>'
            
            Example inputs:
            - "Summarize the business segments, category: AAPL"
            - "What were the key growth drivers?, category: MSFT"
            - "Explain their AI strategy, category: NVDA"
            """
        ),
        Tool(
            name="DocumentAnalysis",
            func=create_document_analysis_wrapper,
            description="""
            Use this tool to analyze a specific document deeply.
            Input format: '<query>, document: <document_id>'
            
            Example inputs:
            - "Analyze the revenue growth, document: ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3"
            - "Summarize the key business segments, document: 7e538606-f18b-410f-8284-59e5929f2aaa"
            - "What challenges did they mention?, document: e64e6c04-9a86-4c8b-9802-868c62930f5e"
            """
        )
    ]
    
    return tools

# Define the prompt for the Transcript Agent - Updated to explain the new search approach
TRANSCRIPT_AGENT_PROMPT_TEMPLATE = """You are an expert **Equity Research Analyst** specializing in analyzing company earnings calls and related documents.
Your primary goal is to answer the user's query by producing a **comprehensive analytical summary/report** based *only* on the information found within the relevant documents or their pre-computed summaries. Your objective is to provide contextual answers holistically covering the topics while preserving facts, so read as much relevant information as possible before drafting a response.
**(Note: Transcript data covers roughly 2016 to 2020).**

You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: As an analyst, I need to break down the question and gather information step-by-step.
1. First, identify the company categories (tickers like AAPL, MSFT, NVDA) mentioned in the Question.
2. For **each** identified category, call the `category_tool` to get a high-level summary. The Action Input MUST be in the format: '<Brief query about category>, category: <CATEGORY_ID>' (e.g., 'Summarize recent growth, category: AAPL').
3. Review the results (`Observation`) from all `category_tool` calls. Is this high-level information sufficient to answer the original Question?
4. **If** the high-level summaries are insufficient OR the Question asks for specific examples/details from specific documents, THEN use the `document_level_search_tool` with the original Question (or relevant parts) to find relevant document IDs for the necessary details.
5. The `document_level_search_tool` uses pure semantic search without metadata filtering to find the most relevant documents. Examine its JSON output. It will contain a key "identified_documents", which is a list of objects, each with "document_id", "document_name", "category_id", and "ticker".
6. **If the query contains more than one category/company**, make separate calls to the `document_level_search_tool` for each category, using more specific queries that focus on that particular company (e.g., "Apple iPhone revenue in Q1 2020" for AAPL, then "Microsoft cloud revenue in Q1 2020" for MSFT).
7. **CRITICAL:** If the `document_level_search_tool` was used and the `identified_documents` list in its JSON output is empty, it means no specific relevant documents were found. Synthesize your Final Answer using the information gathered so far (from `category_tool`), explaining that more specific details could not be found.
8. If `identified_documents` list is NOT empty, proceed to analyze the specific documents. Iterate through the **`identified_documents` list**. For **each document object** in the list: 
   a. Check if its `ticker` matches the company you are interested in for the query.
   b. If it matches (or if you need info from multiple documents), call the `document_content_analysis_tool` using the actual UUID in the `document_id` field (NOT the document_name field) from the current object. The Action Input MUST be in the format: '<Original Query or relevant sub-query>, document: <document_id>' (e.g., 'What was revenue growth?, document: ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3'). The document_id should be the exact UUID string that appears in the "document_id" field of the search results.
   c. Analyze the 'Observation' (the analysis result) returned by each call.
   d. IMPORTANT: The database looks up documents by their unique IDs (UUIDs), not by their human-readable names. Using the wrong ID format will result in not finding the document.
9. **To get a more holistic answer, review multiple documents per category** rather than just the top result. Aim to analyze at least 2-3 relevant documents per category when available, prioritizing those with the highest similarity scores. This will give you a more complete understanding of the topic across different time periods or aspects of the business.
10. After gathering information from `category_tool` and potentially `document_content_analysis_tool` (after iterating through relevant documents), synthesize the key findings from all relevant 'Observation' steps into your Final Answer.

Action: the action to take, must be one of [{tool_names}]
Action Input: the input to the action. **CRITICAL: Ensure the input strictly matches the format specified in the tool's description.** Examples:
    - For 'category_tool': `query, category: <ticker>` (e.g., `summarize performance, category: AAPL`) 
    - For 'document_level_search_tool': `natural language query` (e.g., `MSFT earnings call Q4 2019`)
    - For 'document_content_analysis_tool': `query, document: <uuid>` (e.g., `What was revenue growth?, document: 123e4567-e89b-12d3-a456-426614174000`) --- **Provide only ONE document_id per call. Use the exact UUID from the "document_id" field in search results, not the document name.**
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times as you gather information)
Thought: I have gathered sufficient information from the category summaries and/or specific document analyses. Now I will synthesize these findings into a comprehensive analyst report answering the original question. I've made sure to read multiple documents where available to get a holistic view of the topic. OR If insufficient information was found, I will state that clearly.
Final Answer: **[Analyst Report Format]**
Synthesize the key findings from the 'Observation' steps above into a clear, comprehensive report that directly answers the user's original 'Question'. Structure the report logically. Focus on the aspects relevant to an equity analyst. Explicitly state if the answer relies only on category summaries or includes details from specific documents. **If insufficient information was found (e.g., no relevant category summaries, no specific documents found by document search), state that clearly and explain that the query could not be fully answered based on the available data (mentioning the 2016-2020 date range if relevant).**

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
        document_level_search_tool_instance = create_doc_level_search_wrapper
        
        document_analysis_tool_instance = create_document_analysis_wrapper
        
        internal_tools = [
            Tool(
                name="category_tool",
                func=create_category_tool_wrapper,
                description="Analyzes summaries for a specific category (company ticker) to answer high-level queries or determine if deeper analysis is needed. Input format: 'query, category: <CATEGORY_ID>' (e.g., 'Summarize performance, category: AAPL')",
            ),
            Tool(
                name="document_level_search_tool",
                func=document_level_search_tool_instance,
                description="Finds relevant documents using pure semantic search without metadata filtering. This tool searches across all documents and uses document-level semantic understanding to find the most relevant matches for your query. Input is just the natural language query. Output is a structured JSON with 'identified_documents', each containing document ID, name, and company ticker.",
            ),
            Tool(
                name="document_content_analysis_tool",
                func=document_analysis_tool_instance,
                description="Analyzes the content of a specific document (identified by document_id) to answer a detailed query. Prioritizes using pre-computed summaries if available, otherwise uses the full transcript. Input MUST be in the format: '<query>, document: <document_id>' (e.g., 'What was revenue growth?, document: uuid-goes-here'). Use this AFTER document_level_search_tool identifies a relevant document ID. The document_id must be the UUID from the 'document_id' field in search results, not the human-readable name.",
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
        try:
            result = agent_executor.invoke({"input": query})
            output = result.get("output", "Transcript agent finished but provided no output.")
            logger.info(f"[Transcript Agent Tool] Execution finished. Output: {output[:200]}...")
            return output
        except TypeError as e:
            # Handle the specific NoneType and int calculation error in the Anthropic library
            if "NoneType" in str(e) and "int" in str(e) and "_create_usage_metadata" in str(e):
                logger.warning(f"[Transcript Agent Tool] Handled known token usage calculation error: {e}")
                # Return a helpful message about the error without crashing
                return "The transcript analysis encountered a known issue with token usage calculation in the Anthropic library. Unfortunately, this prevented successful completion of your query. This is a technical issue and not related to the availability of data."
            else:
                # Re-raise other TypeError exceptions
                raise
                
    except Exception as e:
        logger.error(f"[Transcript Agent Tool] Error during execution: {e}", exc_info=True)
        return f"Error: Transcript analysis failed. Details: {type(e).__name__}: {e}" 
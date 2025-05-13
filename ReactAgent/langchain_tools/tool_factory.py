"""
Factory for creating and configuring tools with consistent interfaces.
"""

import os
import logging
from typing import Callable, Dict, Any, Optional, Tuple, List
import json
from langchain_anthropic import ChatAnthropic
from datetime import datetime
import re
import time  # Added time import

# Import utility modules
from .config import sanitize_json_response
from .tool4_metadata_lookup import (
    get_metadata_lookup_tool,
)  # Use the modified tool factory
from .tool5_transcript_analysis import (
    get_document_analysis_tool,
)  # Use the modified tool factory

# Added imports for SQL Tool
from langchain.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain  # Changed import
from langchain.tools import Tool
from langchain_core.language_models import BaseChatModel  # Correct import path
from langchain_core.prompts import PromptTemplate  # <--- Added import
from langchain.agents import (
    AgentExecutor,
    create_react_agent,
)  # <--- Added create_react_agent
import sqlite3  # Added for specific error handling
import traceback  # Added for detailed error logging

# --- Add new import for our tool ---
from langchain_community.utilities import (
    SerpAPIWrapper,
)  # Example: Assuming SerpAPI is used by web_search, adjust if different

# Configure logging
logger = logging.getLogger(__name__)


def create_llm(
    api_key: Optional[str] = None,
    model: str = "claude-3-haiku-20240307",
    temperature: float = 0,
) -> ChatAnthropic:
    """
    Create an instance of the ChatAnthropic LLM.

    Args:
        api_key (str, optional): Anthropic API key. If None, uses environment variable.
        model (str): Model name to use
        temperature (float): Temperature for generation

    Returns:
        ChatAnthropic: Configured LLM instance
    """
    # Use provided API key or try environment variable
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("Anthropic API key not provided and not found in environment")

    logger.info(f"Initializing ChatAnthropic with model: {model}")
    return ChatAnthropic(
        model=model, temperature=temperature, anthropic_api_key=api_key
    )


def create_tool_with_validation(
    tool_fn: Callable, tool_name: str, response_validator: Callable
) -> Callable:
    """Create a tool with validation and metadata handling."""

    def validated_tool(*args, **kwargs) -> Dict[str, Any]:
        try:
            # Execute the tool
            result = tool_fn(*args, **kwargs)

            # Validate the response
            is_valid, errors = response_validator(result)
            if not is_valid:
                logger.error(f"Invalid {tool_name} response: {errors}")
                # Return the error within the expected structure, if the tool itself didn't return an error structure
                if (
                    isinstance(result, dict)
                    and "error" in result
                    and result.get("error")
                ):
                    # Tool already returned an error, perhaps just add validation info?
                    result["metadata"] = {
                        "tool_name": tool_name,
                        "validation_errors": errors,
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": False,
                        "original_error": result["error"],
                    }
                    return result
                else:
                    # Tool output was invalid but didn't report an error itself
                    return {
                        "error": f"Tool response validation failed: {errors}",  # Main error message
                        "metadata": {
                            "tool_name": tool_name,
                            "validation_errors": errors,
                            "timestamp": datetime.utcnow().isoformat(),
                            "success": False,
                            "original_output": result,  # Include original bad output if helpful
                        },
                    }
            # Add metadata if not present (success case)
            if "metadata" not in result:
                result["metadata"] = {}
            result["metadata"].update(
                {
                    "tool_name": tool_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": True,
                }
            )

            return result

        except Exception as e:
            logger.error(f"Error executing {tool_name}: {e}", exc_info=True)
            # Return error in a structure compatible with expected output
            return {
                "error": f"Execution Error in {tool_name}: {type(e).__name__}: {e}",
                "metadata": {
                    "tool_name": tool_name,
                    "error_type": type(e).__name__,
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": False,
                },
            }

    # Copy original function attributes if possible
    validated_tool.__name__ = getattr(tool_fn, "__name__", tool_name)
    validated_tool.__doc__ = getattr(
        tool_fn, "__doc__", f"Validated wrapper for {tool_name}"
    )
    return validated_tool


def create_department_tool(api_key: Optional[str] = None) -> Callable:
    """Create department tool with validation."""
    from langchain_tools.tool1_department import department_summary_tool

    def department_tool(query: str) -> Dict[str, Any]:
        """
        Analyze department-level summaries to determine if a query can be answered
        at the high level or identify which specific category (company) to explore next.

        Args:
            query (str): User query about companies or trends

        Returns:
            Dict[str, Any]: Analysis results
        """
        return department_summary_tool(query, api_key)

    return create_tool_with_validation(
        department_tool, "department_tool", validate_department_response
    )


def create_category_tool() -> Callable:
    """Create category tool with validation."""
    from .tool2_category import category_summary_tool

    # Modify to accept single string input and parse
    def category_tool_wrapper(input_str: str) -> Dict[str, Any]:
        """
        Analyze category-level summaries. Input format: "<query>, category=<CATEGORY_ID>"
        """
        # Parse query and category_id from the input string
        query = input_str
        category_id = None
        match = re.search(r"category=([\w\.\-]+)", input_str, re.IGNORECASE)
        if match:
            category_id = match.group(1)
            # Remove the category part from the query string if desired
            query = (
                re.sub(r",?\s*category=[\w\.\-]+$", "", query, flags=re.IGNORECASE)
                .strip()
                .rstrip(",")
            )  # Remove tag and potential trailing comma
        else:
            logger.warning(
                f"Category ID not found in input format for category_tool: '{input_str}'. Tool will fail."
            )
            return {
                "error": "Category ID missing in input format 'query, category=<ID>'"
            }  # Return error immediately

        # Call the underlying tool
        return category_summary_tool(query, category_id)

    return create_tool_with_validation(
        category_tool_wrapper, "category_tool", validate_category_response
    )


def create_metadata_lookup_tool_wrapper(api_key: Optional[str] = None) -> Callable:
    """Create metadata lookup tool wrapper with validation."""
    # Get the actual tool function by calling its factory
    metadata_lookup_fn = get_metadata_lookup_tool(api_key)

    # Define a simple wrapper (needed for validation layer)
    def metadata_lookup_wrapper(query_term: str) -> Dict[str, Any]:
        return metadata_lookup_fn(query_term)

    return create_tool_with_validation(
        metadata_lookup_wrapper,
        "metadata_lookup_tool",
        validate_metadata_lookup_response,  # Use the (updated) validation function
    )


def create_document_analysis_tool_wrapper(api_key: Optional[str] = None) -> Callable:
    """Create document analysis tool wrapper with validation."""
    # Import renamed factory function
    document_analysis_fn = get_document_analysis_tool(api_key)

    # Wrapper to parse single string input from agent: "query, document_id=<id>"
    def document_analysis_wrapper(input_str: str) -> Dict[str, Any]:
        """Wrapper for document analysis tool. Input format: '<query>, document_id=<uuid>'"""
        query = input_str
        doc_id = None
        # Look for the mandatory document_id parameter (UUID format)
        match = re.search(
            r"document_id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
            input_str,
            re.IGNORECASE,
        )
        if match:
            doc_id = match.group(1)
            # Remove the parameter part from the query string
            query = (
                re.sub(
                    r",?\s*document_id=[0-9a-f\-]+\s*$", "", query, flags=re.IGNORECASE
                )
                .strip()
                .rstrip(",")
            )  # Adjusted regex
            logger.debug(
                f"Document analysis wrapper parsed query='{query}', doc_id='{doc_id}'"
            )
            # Call the actual tool function with parsed args
            return document_analysis_fn(query=query, document_id=doc_id)
        else:
            # Document ID is required
            logger.error(
                f"Document analysis wrapper failed: document_id missing or invalid format in input: '{input_str}'"
            )
            return {
                "answer": None,
                "error": "Input format requires 'document_id=<valid_uuid>'",
            }

    return create_tool_with_validation(
        document_analysis_wrapper,
        "document_content_analysis_tool",  # Use the new underlying tool name here for clarity
        validate_transcript_analysis_response,  # Reuse validation as it checks for 'answer'/'error'
    )


# --- Add the Web Search Wrapper Function ---
# NOTE: This assumes the underlying web_search tool can be called via an API or library.
# We'll use SerpAPIWrapper as a placeholder example. This might need adjustment
# depending on how the environment's `web_search` is actually implemented.
# It requires SERPAPI_API_KEY environment variable.
def _run_web_search(query: str) -> str:
    """
    Performs a web search using the provided query and returns formatted results.
    This is a wrapper around the environment's web search capability.
    """
    logger.info(f"Executing web search for query: {query}")
    try:
        # Example using SerpAPI - REPLACE THIS with the actual call
        # to the environment's web_search mechanism if different.
        # This requires SERPAPI_API_KEY to be set in the environment.
        search = SerpAPIWrapper()
        results = search.run(query)
        # Simple formatting for demonstration
        if isinstance(results, list):
            return "\n".join(results)
        elif isinstance(results, dict):
            return json.dumps(results, indent=2)
        else:
            return str(results)
    except ImportError:
        logger.error(
            "SerpAPIWrapper not available. Install `pip install google-search-results`"
        )
        return "Error: Web search dependency not installed."
    except Exception as e:
        logger.error(f"Error during web search: {e}")
        return f"Error during web search: {str(e)}"


def create_financial_news_search_tool() -> Tool:
    """
    Factory function to create the financial news search tool.
    Wraps the web search functionality with specific instructions.
    """
    # Assuming _run_web_search is defined elsewhere or imported

    # The description guides the LLM on *how* and *when* to use the tool.
    description = (
        "Searches the web for **current or recent** financial news, market sentiment, **live stock price estimates**, "
        "or general information about companies, markets, or economic events. To focus results on reliable financial sources, "
        "preferentially construct the search term using the 'site:' operator. For example: 'query site:reuters.com OR site:marketwatch.com OR site:finance.yahoo.com OR site:seekingalpha.com'. "
        "Use this for information **not** found in the historical financial database or the CCR reporting database."
    )

    return Tool(
        name="financial_news_search",
        func=_run_web_search,  # Use the generic web search wrapper
        description=description,
    )


# --- SQL Tools (Financial and CCR) ---


def create_financial_sql_tool(db_path: str, llm: BaseChatModel) -> Tool:
    """
    Factory function to create the SQL query tool for the financial database.
    Includes dynamic metadata hints and validation.
    Returns generated SQL and result/error.
    """
    logger.info(f"[Financial Tool] Connecting to SQL Database: {db_path}")
    try:
        # Ensure the path is treated correctly (relative to project root or absolute)
        # This assumes the db_path provided is correct relative to where the script runs
        # Or it's an absolute path.
        db_object = SQLDatabase.from_uri(f"sqlite:///{db_path}")

        # Basic check to see if connection is okay
        tables = db_object.get_usable_table_names()
        logger.info(
            f"[Financial Tool] SQLDatabase connection successful. Tables: {tables}"
        )

        # --- Fetch Metadata Dynamically ---
        db_metadata_hints = ""  # Initialize empty string
        try:
            conn = sqlite3.connect(db_path)
            db_metadata_hints = _get_financial_db_metadata(conn, db_object)
            conn.close()
            logger.info("[Financial Tool] Generated DB Metadata Hints for LLM.")
        except Exception as meta_err:
            logger.error(
                f"[Financial Tool] Error fetching dynamic metadata: {meta_err}",
                exc_info=True,
            )
            db_metadata_hints = (
                " (Error fetching metadata hints - LLM should rely on schema only) "
            )

        # --- Define Custom Prompt for SQL Generation ---
        FINANCIAL_SQL_PROMPT_TEMPLATE = """
        Given an input question, create a syntactically correct {dialect} query to run.
        Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per {dialect}.
        Never query for all columns from a table. You must query only the columns that are needed to answer the question.
        Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist.
        Also, pay attention to which table is implicitly referenced in the question.

        **IMPORTANT: You MUST generate ONLY the SQL query for the user's question.**
        **Do NOT include any explanatory text, comments, or markdown formatting (like ```sql).**
        **Output ONLY the raw SQL query itself.**

        Only use the following tables:
        {table_info}

        Question: {input}
        SQLQuery:
        """
        CUSTOM_FINANCIAL_SQL_PROMPT = PromptTemplate(
            input_variables=["input", "table_info", "dialect", "top_k"],
            template=FINANCIAL_SQL_PROMPT_TEMPLATE,
        )
        # ------------------------------------------------

        # --- REMOVED SQLDatabaseChain Initialization ---

        # --- Wrapper function to generate SQL, execute, and return both ---
        def _run_financial_sql_wrapper(query: str) -> Dict[str, Any]: # Return type changed
            """
            Wrapper to generate SQL via LLM, execute it for the financial DB.
            Returns a dictionary {"sql_query": ..., "sql_result": ..., "error": ...}.
            """
            logger.info(f"[Financial Tool] Processing query: {query[:100]}...")
            start_time = time.time()
            generated_sql = ""
            sql_result = None # Changed from result = ""
            error = None
            try:
                # 1. Prepare prompt input
                table_info = db_object.get_table_info(table_names=tables)
                prompt_input = {
                    "input": query,
                    "table_info": table_info,
                    "dialect": db_object.dialect,
                    "top_k": 10, # Default limit, adjust if needed
                }

                # 2. Generate SQL using LLM with the custom prompt
                logger.info("[Financial Tool] Generating SQL query...")
                sql_generation_prompt = CUSTOM_FINANCIAL_SQL_PROMPT.format(**prompt_input)
                llm_response = llm.invoke(sql_generation_prompt)
                generated_sql = (
                    llm_response.content.strip()
                )

                # Basic check if generated content looks like SQL
                if not generated_sql or not (
                    generated_sql.upper().startswith("SELECT")
                    or generated_sql.upper().startswith("WITH")
                ):
                     raise ValueError(
                        f"LLM did not return a valid SQL query starting with SELECT/WITH. Output: {generated_sql[:200]}"
                    )

                logger.info(f"[Financial Tool] Generated SQL: {generated_sql[:200]}...")

                # 3. Execute the generated SQL
                logger.info("[Financial Tool] Executing generated SQL query...")
                sql_result = db_object.run(generated_sql) # Execute the SQL directly
                logger.info(
                    f"[Financial Tool] SQL execution successful. Result: {str(sql_result)[:200]}..."
                )

            except sqlite3.OperationalError as oe:
                logger.error(f"[Financial Tool] SQL Operational Error: {oe} running SQL: {generated_sql}")
                error = f"SQL Operational Error: {oe}"
            except Exception as e:
                logger.error(
                    f"[Financial Tool] Error during SQL tool execution: {e}",
                    exc_info=True,
                )
                error = f"Error: {type(e).__name__}: {e}"

            end_time = time.time()
            logger.info(
                f"[Financial Tool] Query processing time: {end_time - start_time:.2f}s"
            )

            # Return dictionary with query, result, and error
            return {
                "sql_query": generated_sql,
                "sql_result": sql_result,
                "error": error,
            }

        # --- Tool Description ---
        # Include dynamic metadata hints in the description
        tool_description = ( # Updated description slightly
            "Queries the `financial_data.db` database containing structured financial market data. "
            "Use this for specific questions about **historical (2016-2020) daily stock prices** (OHLC), "
            "**historical quarterly financials** (income/balance sheet, limited dates), **dividends**, or **stock splits** "
            "for known public companies. {metadata_hints}Input is a natural language question about specific historical data points. "
            "Persona: SQL Database Expert (Historical Financial Data). Output includes generated SQL and result/error."
        )
        # Format hints safely
        try:
            formatted_description = tool_description.format(
                metadata_hints=db_metadata_hints
            )
        except Exception as fmt_err:
            logger.error(f"[Financial Tool] Error formatting description: {fmt_err}")
            formatted_description = tool_description.format(
                metadata_hints="(Hints unavailable)"
            )

        # --- Return the Langchain Tool ---
        return Tool(
            name="financial_sql_query_tool",
            func=_run_financial_sql_wrapper,
            description=formatted_description,
        )

    except Exception as e:
        error_message_for_tool = (
            f"Error setting up Financial SQL Tool: {type(e).__name__}: {e}"
        )
        logger.error(f"[Financial Tool] Failed setup: {e}\\n{traceback.format_exc()}")

        # Return a dummy tool that reports the error
        def _error_tool_wrapper(query: str) -> Dict[str, Any]: # Return type adjusted
            return {
                "sql_query": None,
                "sql_result": None,
                "error": error_message_for_tool
                }

        return Tool(
            name="financial_sql_query_tool_error",
            description=f"Error setting up Financial SQL Tool: {e}. Returns error message.",
            func=_error_tool_wrapper,
        )


def _get_financial_db_metadata(db_conn, db_object) -> str:
    """Fetches dynamic metadata (examples) for the financial DB prompt hint."""
    hints = []
    cursor = db_conn.cursor()
    try:
        # Example tickers from daily prices
        cursor.execute(
            "SELECT DISTINCT ticker FROM daily_stock_prices WHERE ticker IS NOT NULL ORDER BY RANDOM() LIMIT 3"
        )
        tickers = [row[0] for row in cursor.fetchall()]
        if tickers:
            hints.append(f"Example available tickers: {tickers}.")

        # Example date range from daily prices
        cursor.execute("SELECT MIN(date), MAX(date) FROM daily_stock_prices")
        min_date, max_date = cursor.fetchone()
        if min_date and max_date:
            hints.append(
                f"Stock price data covers range {min_date[:10]} to {max_date[:10]}."
            )

        # Check table existence before querying
        table_names = db_object.get_usable_table_names()
        if "quarterly_income_statement" in table_names:
            cursor.execute("SELECT COUNT(*) FROM quarterly_income_statement")
            if cursor.fetchone()[0] > 0:
                hints.append(
                    "Quarterly financials (income/balance sheet) available for some companies/dates."
                )
    except Exception as e:
        logger.warning(f"[Financial Tool] Error getting metadata hints: {e}")
        return "(Metadata hints query failed)"
    finally:
        cursor.close()

    return "Some relevant examples: " + " ".join(hints) if hints else ""


def create_ccr_sql_tool(db_path: str, llm: BaseChatModel) -> Tool:
    """
    Factory function to create the SQL query tool for the CCR reporting database.
    Includes dynamic metadata hints and validation.
    Now returns both SQL query and result.
    """
    logger.info(f"[CCR Tool] Connecting to SQL Database: {db_path}")
    try:
        db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
        conn = sqlite3.connect(db_path)
        db_metadata_hints = _get_ccr_db_metadata(conn, db)
        conn.close()
        table_names = db.get_usable_table_names()
        logger.info(
            f"[CCR Tool] SQLDatabase connection successful. Tables: {table_names}"
        )

        # --- Define Custom Prompt for SQL Generation ---
        # (Keep the same prompt that strictly asks for only SQL output)
        SQL_PROMPT_TEMPLATE = """
        Given an input question, create a syntactically correct {dialect} query to run.
        Unless the user specifies in the question a specific number of examples to obtain, query for at most {top_k} results using the LIMIT clause as per {dialect}.
        Never query for all columns from a table. You must query only the columns that are needed to answer the question.
        Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist.
        Also, pay attention to which table is implicitly referenced in the question.
        
        **IMPORTANT: You MUST generate ONLY the SQL query for the user's question.**
        **Do NOT include any explanatory text, comments, or markdown formatting (like ```sql).**
        **Output ONLY the raw SQL query itself.**

        Only use the following tables:
        {table_info}

        Question: {input}
        SQLQuery: 
        """

        CUSTOM_SQL_PROMPT = PromptTemplate(
            input_variables=["input", "table_info", "dialect", "top_k"],
            template=SQL_PROMPT_TEMPLATE,
        )
        # ------------------------------------------------

        # --- Removed SQLDatabaseChain ---
        # We will call LLM and db.run() directly in the wrapper

        # --- Wrapper function to generate SQL, execute, and return both ---
        def _run_ccr_sql_wrapper(query: str) -> Dict[str, Any]:  # Return type changed
            logger.info(f"[CCR Tool] Processing query: {query[:100]}...")
            start_time = time.time()
            generated_sql = ""
            sql_result = None
            error = None

            try:
                # 1. Prepare prompt input
                table_info = db.get_table_info(table_names=table_names)
                prompt_input = {
                    "input": query,
                    "table_info": table_info,
                    "dialect": db.dialect,
                    "top_k": 10,  # Default limit, adjust if needed
                }

                # 2. Generate SQL using LLM with the custom prompt
                logger.info("[CCR Tool] Generating SQL query...")
                sql_generation_prompt = CUSTOM_SQL_PROMPT.format(**prompt_input)
                # Assuming llm.invoke returns AIMessage with 'content' attribute
                llm_response = llm.invoke(sql_generation_prompt)
                generated_sql = (
                    llm_response.content.strip()
                )  # Extract content and strip whitespace

                # Basic check if generated content looks like SQL
                if not generated_sql or not (
                    generated_sql.upper().startswith("SELECT")
                    or generated_sql.upper().startswith("WITH")
                ):
                    raise ValueError(
                        f"LLM did not return a valid SQL query starting with SELECT/WITH. Output: {generated_sql[:200]}"
                    )

                logger.info(f"[CCR Tool] Generated SQL: {generated_sql[:200]}...")

                # 3. Execute the generated SQL
                logger.info("[CCR Tool] Executing generated SQL query...")
                sql_result = db.run(generated_sql)  # Execute the SQL
                logger.info(
                    f"[CCR Tool] SQL execution successful. Result: {str(sql_result)[:200]}..."
                )

            except sqlite3.OperationalError as oe:
                logger.error(
                    f"[CCR Tool] SQL Operational Error: {oe} running SQL: {generated_sql}"
                )
                error = f"SQL Operational Error: {oe}"
            except Exception as e:
                logger.error(
                    f"[CCR Tool] Error during SQL tool execution: {e}", exc_info=True
                )
                error = f"Error: {type(e).__name__}: {e}"

            end_time = time.time()
            logger.info(
                f"[CCR Tool] Query processing time: {end_time - start_time:.2f}s"
            )

            # Return dictionary with query, result, and error
            return {
                "sql_query": generated_sql,
                "sql_result": sql_result,
                "error": error,
            }

        # --- Tool Description (remains largely the same) ---
        tool_description = (  # Description might need slight update if output format changes significantly for agent
            "Queries the `ccr_reporting.db` database containing structured Counterparty Credit Risk (CCR) reporting data (sample data). "
            "Use this for specific questions about **counterparty details (ratings, country)**, **daily risk exposures** (Net MTM, Gross, PFE, Settlement), "
            "**risk limits**, **limit utilization**, **breach status**, or individual **trade details** related to known counterparties. "
            "{metadata_hints}Input is a natural language question about specific CCR metrics or counterparty/trade details within this database. "
            "Persona: SQL Database Expert (CCR Reporting Data). Output includes the generated SQL and the result."
        )  # Added note about output
        # Format hints safely
        try:
            formatted_description = tool_description.format(
                metadata_hints=db_metadata_hints
            )
        except Exception as fmt_err:
            logger.error(f"[CCR Tool] Error formatting description: {fmt_err}")
            formatted_description = tool_description.format(
                metadata_hints="(Hints unavailable)"
            )

        # --- Return the Langchain Tool ---
        return Tool(
            name="ccr_sql_query_tool",
            func=_run_ccr_sql_wrapper,
            description=formatted_description,
        )

    except Exception as e:
        # ... (existing error handling for tool setup failure remains the same) ...
        error_message_for_tool = (
            f"Error setting up CCR SQL Tool: {type(e).__name__}: {e}"
        )
        logger.error(f"[CCR Tool] Failed setup: {e}\n{traceback.format_exc()}")

        def _error_tool_wrapper(query: str) -> Dict[str, str]:
            return {
                "sql_query": None,
                "sql_result": None,
                "error": error_message_for_tool,
            }

        return Tool(
            name="ccr_sql_query_tool_error",
            description=f"Error setting up CCR SQL Tool: {e}. Returns error message.",
            func=_error_tool_wrapper,
        )


def _get_ccr_db_metadata(db_conn, db_object) -> str:
    """Fetches dynamic metadata (examples) for the CCR DB prompt hint."""
    hints = []
    cursor = db_conn.cursor()
    table_names = db_object.get_usable_table_names()
    try:
        # Example counterparties
        if "report_counterparties" in table_names:
            cursor.execute(
                "SELECT DISTINCT short_name FROM report_counterparties WHERE short_name IS NOT NULL ORDER BY RANDOM() LIMIT 3"
            )
            counterparties = [row[0] for row in cursor.fetchall()]
            if counterparties:
                hints.append(f"Example counterparties: {counterparties}.")

        # Example exposure date range
        if "report_daily_exposures" in table_names:
            cursor.execute(
                "SELECT MIN(report_date), MAX(report_date) FROM report_daily_exposures"
            )
            min_date, max_date = cursor.fetchone()
            if min_date and max_date:
                hints.append(f"Exposure data covers range {min_date} to {max_date}.")

        # Example product types
        if "products" in table_names:
            cursor.execute(
                "SELECT DISTINCT product_type FROM products WHERE product_type IS NOT NULL ORDER BY RANDOM() LIMIT 3"
            )
            product_types = [row[0] for row in cursor.fetchall()]
            if product_types:
                hints.append(f"Example product types: {product_types}.")
    except Exception as e:
        logger.warning(f"[CCR Tool] Error getting metadata hints: {e}")
        return "(Metadata hints query failed)"
    finally:
        cursor.close()

    return "Some relevant examples: " + " ".join(hints) if hints else ""


# --- Validation Functions ---


def validate_department_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate the response from the department tool."""
    errors = []
    if not isinstance(response, dict):
        return False, ["Response is not a dictionary."]
    if "thought" not in response or not isinstance(response["thought"], str):
        errors.append("Missing or invalid field: thought (string)")
    if "answer" not in response or not isinstance(response["answer"], str):
        errors.append("Missing or invalid field: answer (string)")
    # Confidence is optional? Assume optional if not present.
    if "confidence" in response and not isinstance(
        response["confidence"], (int, float)
    ):
        errors.append("Invalid field type: confidence (number)")
    return not errors, errors


def validate_category_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate the response from the category tool."""
    errors = []
    if not isinstance(response, dict):
        return False, ["Response is not a dictionary."]
    # Allow for error key instead of thought/answer on failure
    if "error" in response and response["error"]:
        return True, []  # Tool reported its own error, consider valid structure
    if "thought" not in response or not isinstance(response["thought"], str):
        errors.append("Missing or invalid field: thought (string)")
    if "answer" not in response or not isinstance(response["answer"], str):
        errors.append("Missing or invalid field: answer (string)")
    if "confidence" in response and not isinstance(
        response["confidence"], (int, float)
    ):
        errors.append("Invalid field type: confidence (number)")
    # Allow for missing 'document_ids' if confidence is low or answer indicates no docs
    if "document_ids" in response and not isinstance(response["document_ids"], list):
        errors.append("Invalid field type: document_ids (list)")
    elif "document_ids" in response:
        if not all(isinstance(item, str) for item in response["document_ids"]):
            errors.append("Invalid item type in document_ids list (must be strings)")

    return not errors, errors


def validate_metadata_lookup_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate the structured response from the metadata lookup tool."""
    errors = []
    if not isinstance(response, dict):
        return False, ["Response is not a dictionary."]

    # If the tool reported an error, consider the structure valid
    if "error" in response and response["error"]:
        return True, []

    # Check required keys and types
    required_fields = {
        "relevant_category_id": (str, type(None)),  # Allow string or None
        "relevant_doc_ids": list,
        "category_summary_available": bool,
        "doc_ids_with_summaries": list,
    }

    for field, expected_type in required_fields.items():
        if field not in response:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(response[field], expected_type):
            # --- Add detailed logging here ---
            if field == "relevant_category_id":
                logger.debug(
                    f"VALIDATION_DEBUG: Checking field '{field}'. Value: '{response[field]}', Type: {type(response[field])}"
                )
                # Add fallback coercion for relevant_category_id
                if (
                    response[field] == "null"
                    or response[field] == ""
                    or response[field] is False
                ):
                    logger.warning(
                        f"Validation: Coercing invalid relevant_category_id value '{response[field]}' to None"
                    )
                    response[field] = None
                    continue  # Skip to next field after coercion
            # --- End added logging ---

            # Special handling for bool which might be parsed as int 0/1
            if (
                expected_type == bool
                and isinstance(response[field], int)
                and response[field] in [0, 1]
            ):
                response[field] = bool(response[field])  # Coerce
        else:
            errors.append(
                f"Invalid type for field {field}: Expected {expected_type}, got {type(response[field])}"
            )

    # Check list item types
    if "relevant_doc_ids" in response and isinstance(
        response["relevant_doc_ids"], list
    ):
        if not all(isinstance(item, str) for item in response["relevant_doc_ids"]):
            errors.append(
                "Invalid item type in relevant_doc_ids list (must be strings)"
            )
    if "doc_ids_with_summaries" in response and isinstance(
        response["doc_ids_with_summaries"], list
    ):
        if not all(
            isinstance(item, str) for item in response["doc_ids_with_summaries"]
        ):
            errors.append(
                "Invalid item type in doc_ids_with_summaries list (must be strings)"
            )

    return not errors, errors


def validate_transcript_analysis_response(response: Dict) -> Tuple[bool, List[str]]:
    """Validate the response from the transcript analysis tool."""
    errors = []
    if not isinstance(response, dict):
        return False, ["Response is not a dictionary."]

    # Check if either 'answer' (string) or 'error' (string/None) is present
    has_answer = "answer" in response and isinstance(
        response["answer"], (str, type(None))
    )
    has_error = "error" in response and isinstance(response["error"], (str, type(None)))

    if not (has_answer or has_error):
        errors.append(
            "Response must contain either 'answer' (string/None) or 'error' (string/None)"
        )
    elif has_answer and has_error and response["error"] is not None:
        # Technically possible, but might indicate confusion
        logger.warning(
            "Transcript analysis response contains both non-None answer and error."
        )
        # We'll allow it for now.

    # Optional: Validate metadata if it exists
    if "metadata" in response and not isinstance(response["metadata"], dict):
        errors.append("Invalid field type: metadata (dict)")

    return not errors, errors


# --- Transcript Agent Tool Factory ---


def create_transcript_agent_tool(
    llm: BaseChatModel, api_key: Optional[str] = None
) -> Tool:
    """
    Creates a specialized agent (as a Tool) that focuses on transcript
    search and analysis using its own set of internal tools.
    """
    logger.info("[Transcript Agent Tool] Initializing...")
    try:
        # 1. Create instances of the internal tools for the Transcript Agent
        category_tool_instance = create_category_tool()
        metadata_lookup_tool_instance = create_metadata_lookup_tool_wrapper(api_key)
        document_analysis_tool_instance = create_document_analysis_tool_wrapper(api_key)

        internal_tools = [
            Tool(
                name="category_tool",
                func=category_tool_instance,
                description="Analyzes summaries for a specific category (company ticker) to answer high-level queries or determine if deeper analysis is needed. Input format: 'query, category=<CATEGORY_ID>' (e.g., 'Summarize performance, category=AAPL')",
            ),
            Tool(
                name="metadata_lookup_tool",
                func=metadata_lookup_tool_instance,
                description="Finds relevant document IDs and checks for available summaries (category synthesis, individual document) based on query terms (e.g., ticker, dates, keywords). Use this AFTER category_tool if more specific document details are required. Input is the natural language query. Output is a structured JSON detailing findings (e.g., {'relevant_doc_ids': [...], 'category_summary_available': true, ...}).",
            ),
            Tool(
                name="document_content_analysis_tool",
                func=document_analysis_tool_instance,
                description="Analyzes the content of a specific document (identified by document_id) to answer a detailed query. Prioritizes using pre-computed summaries if available, otherwise uses the full transcript. Input MUST be in the format: '<query>, document_id=<uuid>' (e.g., 'What was revenue growth?, document_id=uuid-goes-here'). Use this AFTER metadata_lookup_tool identifies a relevant document ID.",
            ),
        ]
        logger.info(
            f"[Transcript Agent Tool] Internal tools created: {[t.name for t in internal_tools]}"
        )

        # 2. Define the prompt for the Transcript Agent (Prioritizing category_tool)
        # ** UPDATED PROMPT **
        TRANSCRIPT_AGENT_PROMPT = """You are an expert **Equity Research Analyst** specializing in analyzing company earnings calls and related documents.
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
7. If `relevant_doc_ids` is NOT empty, proceed to analyze the specific documents. For **each** `document_id` in the `relevant_doc_ids` list: Call the `document_content_analysis_tool`. The Action Input MUST be in the format: '<Original Query or relevant sub-query>, document_id=<the specific document_id>'. Analyze the 'Observation' (the analysis result) returned by each call.
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

        # 3. Create the Transcript Agent tool
        try:
            # Create the react agent
            react_agent = create_react_agent(
                llm,
                internal_tools,
                prompt=PromptTemplate.from_template(TRANSCRIPT_AGENT_PROMPT),
            )

            # Create an AgentExecutor
            agent_executor = AgentExecutor(
                agent=react_agent,
                tools=internal_tools,
                handle_parsing_errors="Check your output and make sure it conforms to the expected format!",
            )

            # --- Define helper function for execution ---
            def _run_transcript_sub_agent(query: str, executor: AgentExecutor) -> Dict[str, Any] | str:
                try:
                    # Execute the sub-agent
                    result = executor.invoke({"input": query})
                    # Return the output if successful
                    return result.get("output", "Transcript agent finished but provided no output.")
                except Exception as sub_agent_error:
                    # Log the error from the sub-agent
                    logger.error(f"[Transcript Agent Tool] Error during sub-agent execution: {sub_agent_error}", exc_info=True)
                    # Return a structured error dictionary consistent with SQL tools
                    return {"error": f"Transcript analysis failed: {type(sub_agent_error).__name__} - {sub_agent_error}"}
            # ------------------------------------------

            # Return the Tool, using the helper function for its func
            return Tool(
                name="transcript_agent",
                func=lambda q: _run_transcript_sub_agent(q, agent_executor),
                description="A specialized agent for analyzing company earnings calls and related documents.",
            )
        except Exception as e:
            logger.error(f"Error creating transcript agent: {e}")
            # Return a dummy error tool if agent *creation* fails
            return Tool(
                name="transcript_agent_error",
                func=lambda q: {"error": f"Error during transcript agent creation: {e}"},
                description="Error creating transcript agent.",
            )

    except Exception as e:
        logger.error(f"Outer Error creating transcript agent tool: {e}", exc_info=True)
        # Return a dummy error tool if outer creation fails
        return Tool(
            name="transcript_agent_error",
            func=lambda q: {"error": f"Error creating transcript agent structure: {e}"},
            description="Error creating transcript agent structure.",
        )

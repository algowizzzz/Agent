# Wrapper for CCR SQL queries
import logging
import time
import sqlite3
from typing import Dict, Any

from langchain.sql_database import SQLDatabase
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import PromptTemplate

logger = logging.getLogger(__name__)

# --- Define Custom Prompt for SQL Generation (Copied from tool_factory) ---
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

def run_ccr_sql(query: str, llm: BaseChatModel, db_path: str) -> Dict[str, Any]:
    """
    Generates and executes SQL via LLM for the CCR reporting DB.
    Returns a dictionary {"sql_query": ..., "sql_result": ..., "error": ...}.
    Includes granular error handling for generation and execution.
    """
    logger.info(f"[CCR Tool] Initializing for query: {query[:100]}... DB: {db_path}")
    start_time = time.time()
    generated_sql = ""
    sql_result = None
    error = None
    db_object = None

    try:
        # Connect to DB
        try:
            db_object = SQLDatabase.from_uri(f"sqlite:///{db_path}")
            tables = db_object.get_usable_table_names()
            logger.info(f"[CCR Tool] DB Connection OK. Tables: {tables}")
        except Exception as db_conn_err:
            logger.error(f"[CCR Tool] Error connecting to DB: {db_conn_err}", exc_info=True)
            error = f"Error: Could not connect to CCR DB at {db_path}. Details: {type(db_conn_err).__name__}"
            return {"sql_query": None, "sql_result": None, "error": error}

        # 1. Prepare prompt input
        table_info = db_object.get_table_info(table_names=tables)
        prompt_input = {
            "input": query,
            "table_info": table_info,
            "dialect": db_object.dialect,
            "top_k": 10, # Default limit, adjust if needed
        }

        # 2. Generate SQL using LLM with the custom prompt
        logger.info("[CCR Tool] Generating SQL query...")
        sql_generation_prompt = CUSTOM_SQL_PROMPT.format(**prompt_input)
        try:
            llm_response = llm.invoke(sql_generation_prompt)
            generated_sql = llm_response.content.strip()
            # Basic check if generated content looks like SQL
            if not generated_sql or not (
                generated_sql.upper().startswith("SELECT")
                or generated_sql.upper().startswith("WITH")
            ):
                 raise ValueError(
                    f"LLM did not return a valid SQL query starting with SELECT/WITH. Output: {generated_sql[:200]}"
                )
            logger.info(f"[CCR Tool] Generated SQL: {generated_sql[:200]}...")

        except Exception as llm_err:
            logger.error(f"[CCR Tool] Error during SQL generation: {llm_err}", exc_info=True)
            error = f"Error: Failed to generate SQL query. LLM Error: {type(llm_err).__name__}"
            # Return immediately if generation failed
            return {"sql_query": generated_sql, "sql_result": None, "error": error}

        # 3. Execute the generated SQL
        logger.info("[CCR Tool] Executing generated SQL query...")
        try:
            sql_result = db_object.run(generated_sql) # Execute the SQL directly
            logger.info(f"[CCR Tool] SQL execution successful. Result: {str(sql_result)[:200]}...")
        except sqlite3.Error as db_err: # Catch specific DB errors
            logger.error(f"[CCR Tool] Database Error executing SQL: {db_err}. SQL: {generated_sql}")
            error = f"Error: Database error executing query. Details: {db_err}"
        except Exception as exec_err: # Catch other potential execution errors
            logger.error(f"[CCR Tool] Unexpected error executing SQL: {exec_err}. SQL: {generated_sql}", exc_info=True)
            error = f"Error: Unexpected error during query execution. Details: {type(exec_err).__name__}"

    except Exception as e: # Catch any other unexpected errors in setup/logic
        logger.error(f"[CCR Tool] Unexpected error in tool wrapper: {e}", exc_info=True)
        error = f"Error: Unexpected internal tool error: {type(e).__name__}"

    end_time = time.time()
    logger.info(f"[CCR Tool] Query processing time: {end_time - start_time:.2f}s")

    # Return dictionary with query, result, and error
    return {
        "sql_query": generated_sql,
        "sql_result": sql_result,
        "error": error, # Will contain the specific error if one occurred
    } 
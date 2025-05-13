# direct_ccr_test.py
import os
import sys
import logging
import json
from dotenv import load_dotenv

# Adjust path to import modules from the project
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required components
from langchain_anthropic import ChatAnthropic
from tools.ccr_sql_tool import run_ccr_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_direct_ccr_call():
    """Directly calls the run_ccr_sql tool with a specific query."""
    print("\n===== DIRECT CCR SQL TOOL TEST =====")

    # Load environment variables
    load_dotenv()
    logger.info("Environment variables loaded.")

    # --- Initialize Required Components ---
    try:
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found.")

        model_name = "claude-3-5-sonnet-20240620" # The LLM is needed by the tool to generate SQL
        llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=anthropic_api_key)
        logger.info(f"LLM Initialized: {getattr(llm, 'model', model_name)}")

        project_root = os.path.abspath(os.path.dirname(__file__))
        ccr_db_path = os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
        logger.info(f"Using CCR DB Path: {ccr_db_path}")
        if not os.path.exists(ccr_db_path):
             logger.warning(f"CCR DB not found at {ccr_db_path}")
             # Decide if you want to exit or let the tool handle the error
             # return

    except Exception as e:
        logger.error(f"Initialization Failed: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize components. Error: {e}")
        return

    # --- Define the Query ---
    # Using the query that caused discrepancies
    test_query = "List the top 3 counterparties by Net MTM exposure on most recent date"
    print(f"\nTesting Query: \"{test_query}\"")

    # --- Call the Tool Directly ---
    try:
        print("\nCalling run_ccr_sql...")
        result = run_ccr_sql(query=test_query, llm=llm, db_path=ccr_db_path)
        print("\nTool Execution Complete.")

        # Print the raw result dictionary
        print("\nRaw Result Dictionary:")
        print(json.dumps(result, indent=2))

        # Print components for clarity
        print("\nComponents:")
        print(f"  Generated SQL: {result.get('sql_query', 'N/A')}")
        print(f"  SQL Result   : {result.get('sql_result', 'N/A')}")
        print(f"  Error        : {result.get('error', 'None')}")

    except Exception as e:
        logger.error(f"Error calling run_ccr_sql: {e}", exc_info=True)
        print(f"\nERROR during tool call: {e}")

    print("\n===== TEST COMPLETE =====")


if __name__ == "__main__":
    test_direct_ccr_call() 
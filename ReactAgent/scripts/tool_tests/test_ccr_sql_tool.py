#!/usr/bin/env python3
"""
Script to test the CCR SQL Query Tool directly.
"""

import os
import sys
import argparse
import json
import logging
import traceback
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import tool factory functions after adjusting path
try:
    # Import the CCR tool creation function
    from langchain_tools.tool_factory import create_ccr_sql_tool, create_llm
except ImportError as e:
    print(f"Error importing tool factory: {e}\nPlease ensure you run this script from the project root or that the 'langchain_tools' directory is in your PYTHONPATH.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Define the default path for the CCR database
DEFAULT_DB_PATH = project_root / "scripts" / "data" / "ccr_reporting.db"

def run_test(query: str, db_path_str: str):
    """Runs the CCR SQL tool with the given query and DB path."""
    logger.info(f"Testing CCR SQL Tool with Query: '{query}'")
    logger.info(f"Using Database: {db_path_str}")

    # Check if DB exists
    db_path = Path(db_path_str)
    if not db_path.is_file():
        logger.error(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    try:
        # 1. Create LLM instance
        llm = create_llm(api_key=api_key)
        logger.info("LLM instance created.")

        # 2. Create the CCR SQL Tool
        ccr_tool = create_ccr_sql_tool(db_path=str(db_path), llm=llm)
        logger.info(f"CCR SQL Tool '{ccr_tool.name}' created.")

        # 3. Execute the tool's function directly
        result_dict = ccr_tool.func(query)

        # 4. Print the structured result
        print("\n--- CCR SQL Tool Result ---")
        print(json.dumps(result_dict, indent=2))
        print("---------------------------")

    except Exception as e:
        logger.error(f"An error occurred during tool testing: {e}\n{traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test CCR SQL Query Tool Directly")
    parser.add_argument("-q", "--query", required=True, help="The user query string.")
    parser.add_argument("--db_path", default=str(DEFAULT_DB_PATH), help=f"Path to the CCR SQLite database file (default: {DEFAULT_DB_PATH}).")

    args = parser.parse_args()

    db_path_to_use = Path(args.db_path).resolve()

    run_test(args.query, str(db_path_to_use)) 
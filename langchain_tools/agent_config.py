"""
Configuration for the multi-tool hierarchical retrieval agent (Financial and Risk Analyst).
Dynamically fetches examples for tool descriptions.
"""

import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# --- Constants ---
# Assuming DBs are in the project root or a standard 'data' subfolder
# Adjust these relative paths if DBs are located elsewhere
FINANCIAL_DB_RELATIVE_PATH = "financial_data.db"
CCR_DB_RELATIVE_PATH = "ccr_reporting.db"

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- Helper Functions ---

# Basic project root finding (adjust if needed)
def _get_project_root() -> str:
    """Find the project root based on this file's location."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def _get_db_path(relative_path: str) -> Optional[str]:
    """Construct absolute path for DB, return None if not found."""
    project_root = _get_project_root()
    # Prefer path from .env if set, otherwise try relative path
    env_var_name = "FINANCIAL_DB_PATH" if "financial" in relative_path else "CCR_DB_PATH"
    load_dotenv(os.path.join(project_root, '.env')) # Ensure .env is loaded
    db_path_env = os.getenv(env_var_name)

    if db_path_env:
        if os.path.exists(db_path_env):
            logger.info(f"Using DB path from env var {env_var_name}: {db_path_env}")
            return db_path_env
        else:
            logger.warning(f"DB path from env var {env_var_name} does not exist: {db_path_env}")

    # Fallback to relative path calculation
    potential_paths = [
        os.path.join(project_root, relative_path),
        os.path.join(project_root, 'data', relative_path),
        os.path.join(project_root, 'scripts', 'data', relative_path)
    ]

    for path in potential_paths:
        if os.path.exists(path):
            logger.info(f"Using DB path: {path}")
            return path
        else:
            logger.debug(f"Tried DB path (not found): {path}")

    logger.warning(
        f"Database file not found. Tried:\n"
        f"1. Environment variable '{env_var_name}': {db_path_env or 'not set'}\n"
        f"2. Relative paths:\n   " + "\n   ".join(potential_paths)
    )
    return None


def _fetch_db_examples(db_rel_path: str, query: str, limit: int = 3) -> List[str]:
    """Connects to DB, runs query to fetch examples, handles errors."""
    logger.info(f"--- Attempting to fetch DB examples for: {db_rel_path} ---")
    db_path = _get_db_path(db_rel_path)
    if not db_path:
        logger.warning(f"--- DB path not found for {db_rel_path}, skipping example fetch. ---")
        return [] # Return empty list if DB not found

    examples = []
    conn = None
    try:
        logger.info(f"--- Connecting to DB at: {db_path} ---")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info(f"--- Executing query: {query} on {db_rel_path} ---")
        try:
            cursor.execute(query) # Query already includes LIMIT
            results = cursor.fetchall()
            examples = [str(row[0]) for row in results] # Get first column as string
            logger.info(f"--- Successfully fetched {len(examples)} examples from {db_rel_path} ---")
        except sqlite3.Error as e:
            # Log a warning instead of an error/exception if the query fails (e.g., table not found)
            logger.warning(f"--- SQLITE WARNING fetching examples from {db_rel_path}: {e}. Proceeding without these examples. ---")
            examples = [] # Ensure examples is empty list on error
    except sqlite3.Error as e:
        # Keep logging connection errors etc. as errors
        logger.error(f"--- SQLITE ERROR connecting to or setting up cursor for {db_rel_path}: {e} ---")
        examples = [] # Ensure examples is empty list on error
    finally:
        if conn:
            logger.info(f"--- Closing DB connection for: {db_path} ---")
            conn.close()
    logger.info(f"--- Finished fetching DB examples for: {db_rel_path} ---")
    return examples


# --- Agent Configuration ---
AGENT_CONFIG = {
    "max_iterations": 10,
    "verbose": True,
    "agent_type": "zero_shot_react_description",
    "early_stopping_method": "force",
}

# --- Base Tool Descriptions (Templates) ---
BASE_TOOL_DESCRIPTIONS = {
    "financial_sql_query_tool": (
        "Queries the `financial_data.db` database containing structured financial market data. Use this for specific questions about **historical (2016-2020) daily stock prices** (OHLC), **historical quarterly financials** (income/balance sheet, limited dates), **dividends**, or **stock splits** for known public companies like **{financial_examples}**, etc. "
        "Input is a natural language question about specific historical data points."
        " Persona: SQL Database Expert (Historical Financial Data)."
    ),
    "ccr_sql_query_tool": (
        "Queries the `ccr_reporting.db` database containing structured Counterparty Credit Risk (CCR) reporting data (sample data). Use this for specific questions about **counterparty details (ratings, country)**, **daily risk exposures** (Net MTM, Gross, PFE, Settlement), **risk limits**, **limit utilization**, **breach status**, or individual **trade details** related to counterparties like **{ccr_examples}**, etc. "
        "Input is a natural language question about specific CCR metrics or counterparty/trade details within this database."
        " Persona: SQL Database Expert (CCR Reporting Data)."
    ),
    "transcript_search_summary_tool": (
         "Answers questions requiring qualitative analysis, summaries, or context from **earnings call transcripts**. Use for queries about company performance narratives, strategies, management commentary, outlook, or specific events discussed in calls (e.g., queries like **'What was management\'s outlook for cloud growth in the MSFT Q4 2020 call?'**). Input should be the original user query."
         " Persona: Equity Research Analyst (Transcript Specialist)."
    ),
    "financial_news_search": (
        "Searches the web for **current or recent** financial news, market sentiment, **live stock price estimates**, or general information about companies, markets, or economic events. "
        "To focus results on reliable financial sources, preferentially construct the search term using the 'site:' operator. "
        "For example: 'query site:reuters.com OR site:marketwatch.com OR site:finance.yahoo.com OR site:seekingalpha.com'. "
        "Use this for information **not** found in the historical financial database or the CCR reporting database."
    )
}

# --- Dynamic Tool Description Generation ---
def get_tool_descriptions() -> Dict[str, str]:
    """
    Generates tool descriptions, dynamically fetching examples from databases.
    Falls back to generic examples if DB fetching fails.
    """
    # Fetch examples
    logger.info("--- Starting dynamic tool description generation... ---")
    fin_examples = _fetch_db_examples(
        FINANCIAL_DB_RELATIVE_PATH,
        # Using companies table as it's more likely to exist than daily_stock_prices
        "SELECT DISTINCT ticker FROM companies WHERE ticker IS NOT NULL ORDER BY ticker LIMIT 3"
    )
    ccr_examples = _fetch_db_examples(
        CCR_DB_RELATIVE_PATH,
        # Using limits table as report_counterparties might be missing
        "SELECT DISTINCT limit_id FROM limits WHERE limit_id IS NOT NULL ORDER BY limit_id LIMIT 3"
    )
    logger.info("--- Finished fetching all DB examples. ---")

    # Format examples or use fallbacks
    # Use fallback examples more reliably if fetching failed
    fin_examples_str = f"including **{', '.join(f'{ex}' for ex in fin_examples)}**" if fin_examples else "'AAPL', 'MSFT', 'GOOG'"
    ccr_examples_str = f"including **{', '.join(f'{ex}' for ex in ccr_examples)}**" if ccr_examples else "'JPMorgan', 'BankOfAmerica', 'Citigroup'"

    # Populate templates
    final_descriptions = {}
    for tool_name, template in BASE_TOOL_DESCRIPTIONS.items():
        try:
            # Simplified formatting - use kwargs for clarity
            format_kwargs = {}
            if '{financial_examples}' in template:
                format_kwargs['financial_examples'] = fin_examples_str
            if '{ccr_examples}' in template:
                format_kwargs['ccr_examples'] = ccr_examples_str

            if format_kwargs:
                 final_descriptions[tool_name] = template.format(**format_kwargs)
            else:
                 # For tools without dynamic examples
                 final_descriptions[tool_name] = template # Use template directly

        except KeyError as e:
             logger.warning(f"KeyError formatting description for {tool_name}: {e}. Using template directly (check placeholders).")
             # Use template directly if formatting fails unexpectedly
             final_descriptions[tool_name] = template

    # Ensure all base descriptions are included, even if formatting failed entirely
    for tool_name in BASE_TOOL_DESCRIPTIONS:
        if tool_name not in final_descriptions:
             logger.warning(f"Adding description for {tool_name} manually after formatting failure.")
             # Attempt basic fallback formatting
             fallback_kwargs = {
                 'financial_examples': "'AAPL', 'MSFT', 'GOOG'",
                 'ccr_examples': "'JPMorgan', 'BankOfAmerica', 'Citigroup'"
             }
             try:
                 final_descriptions[tool_name] = BASE_TOOL_DESCRIPTIONS[tool_name].format(**fallback_kwargs)
             except KeyError: # If even fallback placeholders are wrong
                 final_descriptions[tool_name] = BASE_TOOL_DESCRIPTIONS[tool_name].replace('{financial_examples}', fallback_kwargs['financial_examples']).replace('{ccr_examples}', fallback_kwargs['ccr_examples'])


    return final_descriptions


# --- Master Agent Prompt ---
MASTER_AGENT_PROMPT = """You are a diligent **Financial and Risk Analyst**. Your primary function is to understand user queries and route them accurately to the appropriate specialized tool based on the type of information required. You must be careful to attribute information to its source.

You have access to the following specialized tools:

{tools}

Based on the user's query, determine the most appropriate data source and tool:
- For specific, quantitative facts about **historical (2016-2020) stock market data or company financials** (prices, dividends, quarterly figures) from the `financial_data.db`, use the 'financial_sql_query_tool'.
- For specific, quantitative facts about **Counterparty Credit Risk (CCR)** data from the internal `ccr_reporting.db` (sample data), such as **customer/bank exposure, counterparty ratings, risk limits, limit utilization, breach status, or specific trade details for a customer ID or name**, use the 'ccr_sql_query_tool'. **Prioritize this tool for queries explicitly mentioning CCR, counterparty risk, exposure, limits, or specific customer IDs/trades.**
- For **recent news, current events, LIVE stock prices, market sentiment, or general web information** about companies, markets, or economic topics (especially if the financial or CCR databases lack the data), use the 'financial_news_search'.
- For **qualitative analysis, summaries, context, management commentary, strategy discussions, or performance narratives** requiring interpretation of **earnings call transcripts** or other documents, use the 'transcript_search_summary_tool'.

Use the following format precisely:

Question: The input question you must answer.
Thought: As a Financial and Risk Analyst, I must first analyze the query to identify the core information need. Does it ask for historical financial market data (`financial_sql_query_tool`), internal CCR reporting data like customer exposure/trades/limits (`ccr_sql_query_tool`), recent news/live prices (`financial_news_search`), or qualitative analysis of transcripts (`transcript_search_summary_tool`)? Based on keywords and the type of data requested, I will select the single best specialized tool. I need to explain my reasoning for choosing this tool, referencing the type of query and the tool's specialization using its description.
Action: The name of the single most appropriate tool to use (must be one of [{tool_names}]). # Tool names list will be updated automatically
Action Input: The input required for the selected tool (usually the original user query, unless the tool description specifies otherwise).
Observation: The direct result received from the specialized tool.
Thought: I have received the response from the specialized tool ([Tool Name]). This tool acts as a specialist ([Tool Persona mentioned in its description]). I will now present this information clearly, attributing it directly to the specialist tool's analysis.
Final Answer: Based on the analysis performed by the specialized [Tool Name] ([Tool Persona]), here is the response to your query: [Insert the full Observation received from the tool here].

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

# --- Custom Output Parser Configuration ---
OUTPUT_PARSER_CONFIG = {
    "required_fields": ["thought", "action", "action_input"],
    "optional_fields": ["observation", "final_answer"],
    "output_format": {
        "status": "success",
        "result": "<final_answer>"
    }
}

# --- Getter Functions ---
def get_agent_config() -> Dict[str, Any]:
    """Get the agent configuration"""
    return AGENT_CONFIG

# get_tool_descriptions() is now defined above

def get_agent_prompt() -> str:
    """Get the agent prompt template"""
    return MASTER_AGENT_PROMPT

def category_tool_response_structure() -> Dict[str, Any]:
    """Get the expected response structure for category tool (might be deprecated for main agent)."""
    return {
        "summary": "comprehensive analysis...",
        "relevant_doc_ids": [],
        "confidence": 0
    } 
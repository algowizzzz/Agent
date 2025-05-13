#!/usr/bin/env python3
"""
Test script for the React Agent implementation that tests follow-up queries.
"""

import os
import sys
import logging
import time
import re
from dotenv import load_dotenv

# Adjust path to import modules from the project
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the React Agent
from react_agent import ReactAgentWrapper

# Import required tools and components
from langchain_anthropic import ChatAnthropic
from tools.financial_sql_tool import run_financial_sql
from tools.ccr_sql_tool import run_ccr_sql
from tools.financial_news_tool import run_financial_news_search
from tools.earnings_call_tool import run_transcript_agent

# Configure logging to capture the full conversation
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# DirectAnswer Tool Function
def run_direct_answer(query: str, **kwargs) -> str:
    print(f"[Tool:DirectAnswer] Received instruction: {query}")
    return f"The user asked for a direct response based on the instruction: '{query}'. I should formulate the final answer now."

# Conversation Handler
def run_conversation_handler(query: str, **kwargs) -> str:
    print(f"[Tool:conversation_handler] Handling: {query}")
    return f"Handled conversationally: '{query}'"

def initialize_agent():
    """Initialize the React Agent with all necessary components."""
    print("Initializing React Agent for follow-up testing...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
    
    # Initialize LLM
    model_name = "claude-3-5-sonnet-20240620"
    llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=anthropic_api_key)
    print(f"LLM Initialized: {getattr(llm, 'model', model_name)}")
    
    # Define DB Paths
    project_root = os.path.abspath(os.path.dirname(__file__))
    db_paths = {
        "financial": os.path.join(project_root, "scripts", "data", "financial_data.db"),
        "ccr": os.path.join(project_root, "ccr_reporting.db")
    }
    
    # Create Tools Map
    tools_map = {
        "FinancialSQL": lambda query: run_financial_sql(query, llm=llm, db_path=db_paths["financial"]),
        "CCRSQL": lambda query: run_ccr_sql(query, llm=llm, db_path=db_paths["ccr"]),
        "FinancialNewsSearch": run_financial_news_search,
        "EarningsCallSummary": lambda query: run_transcript_agent(query, llm=llm, api_key=anthropic_api_key),
        "DirectAnswer": run_direct_answer,
        "conversation_handler": run_conversation_handler
    }
    
    return ReactAgentWrapper(
        llm=llm,
        tools_map=tools_map,
        db_paths=db_paths,
        api_key=anthropic_api_key,
        max_iterations=5
    )

if __name__ == "__main__":
    try:
        # Initialize the agent
        agent = initialize_agent()
        
        # Define the initial query
        initial_query = "Summarize Microsoft's Q4 2017 earnings call with a focus on cloud performance"
        
        # Run the initial query
        print(f"\n===== RUNNING INITIAL QUERY =====")
        print(f"Query: {initial_query}")
        print(f"================================\n")
        
        initial_response = agent.run(initial_query)
        
        # Print first result
        print(f"\n===== INITIAL RESPONSE =====")
        print(initial_response)
        print(f"===========================\n")
        
        # Wait a moment
        time.sleep(2)
        
        # Define the follow-up query
        followup_query = "What was their outlook for future cloud growth?"
        
        # Run the follow-up query
        print(f"\n===== RUNNING FOLLOW-UP QUERY =====")
        print(f"Query: {followup_query}")
        print(f"==================================\n")
        
        followup_response = agent.run(followup_query)
        
        # Print follow-up result
        print(f"\n===== FOLLOW-UP RESPONSE =====")
        print(followup_response)
        print(f"=============================\n")
        
    except Exception as e:
        print(f"Failed to complete React Agent testing: {e}") 
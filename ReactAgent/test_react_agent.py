#!/usr/bin/env python3
"""
Test script for the React Agent implementation.
This script sends various financial queries to test different tools and functionality.
"""

import os
import sys
import logging
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.FileHandler("react_agent_test.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# DirectAnswer Tool Function
def run_direct_answer(query: str, **kwargs) -> str:
    logger.info(f"[Tool:DirectAnswer] Received instruction: {query}")
    return f"The user asked for a direct response based on the instruction: '{query}'. I should formulate the final answer now."

# Conversation Handler
def run_conversation_handler(query: str, **kwargs) -> str:
    logger.info(f"[Tool:conversation_handler] Handling: {query}")
    return f"Handled conversationally: '{query}'"

def initialize_agent():
    """Initialize the React Agent with all necessary components."""
    logger.info("Initializing React Agent for testing...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
    
    # Initialize LLM
    model_name = "claude-3-5-sonnet-20240620"
    llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=anthropic_api_key)
    logger.info(f"LLM Initialized: {getattr(llm, 'model', model_name)}")
    
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
    
    # Initialize React Agent
    agent = ReactAgentWrapper(
        llm=llm,
        tools_map=tools_map,
        db_paths=db_paths,
        api_key=anthropic_api_key,
        max_iterations=10
    )
    
    logger.info("React Agent initialized for testing")
    return agent

def run_test_queries(agent):
    """Run a series of test queries to verify the agent's functionality."""
    test_queries = [
        {
            "name": "MSFT Stock Price",
            "query": "What was Microsoft's closing price on October 25, 2018?",
            "expected_tool": "FinancialSQL"
        },
        {
            "name": "JPMorgan Rating",
            "query": "What is JPMorgan's credit rating?",
            "expected_tool": "CCRSQL"
        },
        {
            "name": "MSFT Earnings Call",
            "query": "Summarize Microsoft's Q4 2017 earnings call",
            "expected_tool": "EarningsCallSummary"
        },
        {
            "name": "Tariff News",
            "query": "What's the latest tariff news impacting the energy sector?",
            "expected_tool": "FinancialNewsSearch"
        },
        {
            "name": "General Knowledge",
            "query": "What's the difference between a stock and a bond?",
            "expected_tool": "DirectAnswer"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_queries):
        logger.info(f"Running test {i+1}/{len(test_queries)}: {test['name']}")
        logger.info(f"Query: {test['query']}")
        
        try:
            response = agent.run(test['query'])
            
            # Log result
            logger.info(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
            
            # Store result
            results.append({
                "test": test["name"],
                "query": test["query"],
                "response": response,
                "success": True
            })
            
        except Exception as e:
            logger.error(f"Error executing test '{test['name']}': {e}")
            results.append({
                "test": test["name"],
                "query": test["query"],
                "error": str(e),
                "success": False
            })
    
    return results

def print_results(results):
    """Print a summary of test results."""
    print("\n======= REACT AGENT TEST RESULTS =======")
    
    success_count = sum(1 for r in results if r.get("success", False))
    print(f"Passed: {success_count}/{len(results)} tests\n")
    
    for i, result in enumerate(results):
        print(f"Test {i+1}: {result['test']}")
        print(f"Query: {result['query']}")
        
        if result.get("success", False):
            response = result["response"]
            preview = response[:150] + "..." if len(response) > 150 else response
            print(f"Response: {preview}")
            print("Status: ✅ Success")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")
            print("Status: ❌ Failed")
        
        print("")
    
    print("=======================================")

if __name__ == "__main__":
    try:
        # Initialize the agent
        agent = initialize_agent()
        
        # Run test queries
        print("Running test queries. This may take a few minutes...")
        results = run_test_queries(agent)
        
        # Print results
        print_results(results)
        
    except Exception as e:
        logger.error(f"Failed to complete React Agent testing: {e}", exc_info=True)
        print(f"Error: {e}") 
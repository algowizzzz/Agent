#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- LangChain Imports ---
try:
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.prompts import PromptTemplate # Or specific prompt logic if needed
    # A basic ReAct prompt template - adjust if a custom one is needed
    from langchain import hub
except ImportError as e:
    logger.error(f"Failed to import LangChain components: {e}")
    sys.exit(1)

# --- Tool and LLM Imports ---
try:
    from langchain_tools.tool_factory import create_llm, create_financial_news_search_tool
except ImportError as e:
    logger.error(f"Failed to import tool/LLM factory: {e}. Ensure langchain_tools is in Python path.")
    sys.exit(1)

def run_news_agent(query: str):
    """Initializes and runs a simple agent with only the financial news tool."""
    logger.info(f"Testing News Agent with query: '{query}'")

    # Load environment variables (ANTHROPIC_API_KEY, SERPAPI_API_KEY)
    load_dotenv()
    
    # Check for necessary API keys
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    serpapi_api_key = os.getenv("SERPAPI_API_KEY")
    
    if not anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables.")
        sys.exit(1)
    if not serpapi_api_key:
        logger.error("SERPAPI_API_KEY not found in environment variables.")
        sys.exit(1) # Tool test confirmed this is needed for the current implementation
        
    try:
        # 1. Create LLM
        llm = create_llm(api_key=anthropic_api_key)
        logger.info("LLM created.")

        # 2. Create Tool
        news_tool = create_financial_news_search_tool()
        tools = [news_tool]
        logger.info(f"Tool created and added: {news_tool.name}")

        # 3. Create Agent
        # Using a standard ReAct prompt from LangChain Hub
        prompt = hub.pull("hwchase17/react")
        
        agent = create_react_agent(llm, tools, prompt)
        logger.info("ReAct agent created.")

        # 4. Create Agent Executor
        agent_executor = AgentExecutor(
             agent=agent, 
             tools=tools, 
             verbose=True, # Show agent thought process
             handle_parsing_errors=True # Handle potential LLM output format issues
        )
        logger.info("Agent Executor created.")

        # 5. Run Agent
        logger.info("Running agent executor...")
        # Use invoke for potentially richer output if needed, run for simpler string output
        # result = agent_executor.invoke({"input": query})
        result = agent_executor.invoke({"input": query})
        final_answer = result.get("output", "Agent did not produce a final answer.")

        # Print the final answer
        logger.info("--- Agent Final Answer ---")
        print(final_answer)
        logger.info("--- End of Answer ---")

    except Exception as e:
        logger.error(f"An error occurred during agent execution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test an Agent with only the Financial News Search Tool")
    parser.add_argument("-q", "--query", required=True, help="The user query for the agent.")
    args = parser.parse_args()
    
    run_news_agent(args.query) 
#!/usr/bin/env python3
"""
Test script for the React Agent implementation with interactive multi-turn conversation.
"""

import os
import sys
import logging
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
    level=logging.INFO,  # Set to INFO to reduce verbosity
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
    print("Initializing React Agent for interactive conversation testing...")
    
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

def run_interactive_session(agent, output_file=None):
    """Run an interactive session with the agent."""
    # Define a conversation to simulate
    conversation = [
        "What is JPMorgan's credit rating?",
        "How does that compare to other major banks?",
        "What recent news might affect their rating?",
        "Do they have good growth prospects?",
        "exit"
    ]
    
    print("\n===== STARTING MULTI-TURN CONVERSATION =====\n")
    
    # Open file for writing if specified
    file_handle = None
    if output_file:
        file_handle = open(output_file, 'w')
        file_handle.write("===== REACT AGENT CONVERSATION TRANSCRIPT =====\n\n")
    
    try:
        for i, query in enumerate(conversation):
            if query.lower() in ["exit", "quit"]:
                print("\nEnding conversation...")
                if file_handle:
                    file_handle.write("\nEnding conversation...\n")
                break
                
            print(f"\n--- Turn {i+1} ---")
            print(f"User: {query}")
            
            # Write to file if specified
            if file_handle:
                file_handle.write(f"\n--- Turn {i+1} ---\n")
                file_handle.write(f"User: {query}\n")
            
            # Process the query
            response = agent.run(query)
            
            # Display the response
            print(f"Agent: {response}")
            
            # Write to file if specified
            if file_handle:
                file_handle.write(f"Agent: {response}\n")
            
        print("\n===== CONVERSATION COMPLETE =====\n")
        if file_handle:
            file_handle.write("\n===== CONVERSATION COMPLETE =====\n")
    
    finally:
        if file_handle:
            file_handle.close()

if __name__ == "__main__":
    try:
        # Initialize the agent
        agent = initialize_agent()
        
        # Define output file path
        output_file = "react_conversation_transcript.txt"
        
        # Run the interactive session with file output
        run_interactive_session(agent, output_file)
        
        print(f"Conversation transcript saved to {output_file}")
        
    except Exception as e:
        print(f"Failed to complete React Agent testing: {e}") 
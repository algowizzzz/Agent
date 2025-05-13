#!/usr/bin/env python3
"""
Simple script to directly test the agent functionality without a web server.
This script allows you to query the agent from the command line.
"""

import os
import sys
import logging
import json
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import the agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from langchain_tools.agent import HierarchicalRetrievalAgent

def process_query(agent, query):
    """Process a query using the agent."""
    logger.info(f"Processing query: {query}")
    
    start_time = time.time()
    
    try:
        # Use the query method directly
        result = agent.query(query)
            
        elapsed_time = time.time() - start_time
        logger.info(f"Query processed in {elapsed_time:.2f} seconds")
        
        return {
            "query": query,
            "response": result,
            "elapsed_time": f"{elapsed_time:.2f}s"
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error processing query: {str(e)}")
        return {
            "query": query,
            "error": str(e),
            "elapsed_time": f"{elapsed_time:.2f}s"
        }

def main():
    """Main function to run the script."""
    # Load environment variables
    logger.info("Loading environment variables...")
    load_dotenv()
    logger.info("Environment variables loaded.")
    
    # Initialize the agent
    logger.info("Initializing HierarchicalRetrievalAgent...")
    try:
        agent = HierarchicalRetrievalAgent()
        logger.info("HierarchicalRetrievalAgent initialized successfully.")
        
        # Print agent details
        logger.info(f"Agent type: {type(agent)}")
        logger.info(f"Agent has run method: {hasattr(agent, 'run')}")
        logger.info(f"Agent has agent_executor: {hasattr(agent, 'agent_executor')}")
        logger.info(f"Agent has orchestrator: {hasattr(agent, 'orchestrator')}")
        
        if len(sys.argv) > 1:
            # Get query from command line
            query = " ".join(sys.argv[1:])
            result = process_query(agent, query)
            print(json.dumps(result, indent=2))
        else:
            # Interactive mode
            print("\nBussGPT Agent Test")
            print("Type 'exit' or 'quit' to end")
            print("Enter empty line to send the query")
            
            while True:
                print("\nEnter your query:")
                lines = []
                while True:
                    try:
                        line = input()
                        if not line:
                            break
                        lines.append(line)
                    except EOFError:
                        break
                
                query = "\n".join(lines)
                if query.lower() in ['exit', 'quit']:
                    break
                
                if query.strip():
                    result = process_query(agent, query)
                    print(json.dumps(result, indent=2))
                else:
                    print("Empty query. Please try again.")
    
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
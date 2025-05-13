from langchain_tools.agent import HierarchicalRetrievalAgent
import os
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Get query from command line argument
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Summarize AAPL performance in Q1 2017 and Q2 2017"  # Default query
        
    logger.info(f"Using query: {query}")
    
    # First try the category tool directly
    logger.info("\nTrying category tool directly:")
    logger.info("(Skipping direct category tool call for this test)")
    
    # Then try through the agent
    agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
    logger.info(f"\nRunning through agent: {query}")
    
    try:
        response = agent.query(query)
        print("\nAgent response:", response)
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main() 
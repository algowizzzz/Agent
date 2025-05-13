#!/usr/bin/env python3
"""
Main entry point for the Enterprise Internal Agent (CLI Mode).
Initializes the BasicAgent and runs the interactive CLI.
"""

import os
import sys
import logging
import time

# Adjust path to import modules from the project
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import BasicAgent
from basic_agent import BasicAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
# Uncomment to reduce verbosity if needed
# logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def handle_query(query: str, agent) -> None:
    """Process a user query and display the response."""
    logger.info(f"Received user query: {query}")
    
    print("\nAssistant thinking...")
    response = agent.run(query)
    
    # Split the response into thinking steps and answer
    response_parts = response.split("\n\n", 1)
    
    # If the response contains thinking steps (format: "Thinking...\n- step1\n- step2\n\nAnswer")
    if len(response_parts) > 1 and response_parts[0].startswith("Thinking..."):
        thinking_steps = response_parts[0]
        answer = response_parts[1]
        
        # Display thinking steps with slight delay to simulate thinking
        print(f"\n{thinking_steps}")
        time.sleep(0.5)  # Short pause before showing answer
        
        # Display the final answer
        print(f"\nA: {answer}")
    else:
        # Fall back to the old format if thinking steps aren't present
        print(f"\nA: {response}")

def main():
    """Main function to initialize agent and run interaction loop."""
    logger.info("Starting Enterprise Agent (CLI Mode)...")
    
    try:
        # Initialize BasicAgent (handles its own LLM, tools, paths setup)
        agent = BasicAgent()
        logger.info("BasicAgent initialized successfully.")
        
        # Interaction Loop
        print("\n--- Enterprise Agent --- Type 'exit' or 'quit' to end.")
        while True:
            try:
                user_query = input("\nUser > ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ("exit", "quit"):
                    print("\nAssistant: Goodbye!")
                    break

                handle_query(user_query, agent)

            except KeyboardInterrupt:
                print("\nAssistant: Session interrupted by user. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error during interaction: {e}", exc_info=True)
                print(f"\nAssistant: An error occurred: {str(e)}")
    
    except Exception as e:
        logger.error(f"Agent initialization failed: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize agent. Error: {str(e)}")
        return

    logger.info("Agent shutdown complete.")

if __name__ == "__main__":
    main() 
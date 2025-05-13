#!/usr/bin/env python3
"""
Main entry point for the Enterprise Agent CLI
"""

import os
import sys
import logging
from basic_agent import BasicAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point."""
    try:
        logger.info("Starting Enterprise Agent (CLI Mode)...")
        agent = BasicAgent()
        logger.info("BasicAgent initialized successfully.")

        print("\n--- Enterprise Agent --- Type 'exit' or 'quit' to end.\n")
        
        # Main interaction loop
        while True:
            try:
                # Get user input with proper prompt
                user_input = input("\nUser > ").strip()
                
                # Check for exit command
                if user_input.lower() in ['exit', 'quit']:
                    print("\nThank you for using the BMO Enterprise Risk Assistant. Goodbye!")
                    break
                    
                # Skip empty inputs
                if not user_input:
                    continue
                    
                logger.info(f"Received user query: {user_input}")
                
                # Process the query
                print("\nAssistant thinking...")
                response = agent.run(user_input)
                
                # Format and display the response
                print(f"\nA: {response}")
                
            except KeyboardInterrupt:
                print("\n\nOperation interrupted by user.")
                continue
                
            except Exception as e:
                logger.error(f"Error processing query: {e}", exc_info=True)
                print(f"\nI apologize, but an error occurred while processing your request: {str(e)}")
                continue
    
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        print(f"A fatal error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
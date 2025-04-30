#!/usr/bin/env python3
"""
Main entry point for the Enterprise Internal Agent.
Initializes components and runs the agent's interaction loop.
"""

import os
import sys
import logging

# Adjust path to import modules from the project
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Import the main agent orchestrator function
from agents.internal_agent import run_agent_session

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()] # Log to console
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Enterprise Internal Agent...")
    
    # Load environment variables (.env file at project root)
    # Make sure this is loaded before internal_agent initializes components
    load_dotenv()
    logger.info("Environment variables loaded from .env")

    # Run the main agent session loop
    try:
        run_agent_session()
    except Exception as e:
        logger.error(f"Agent session terminated due to unexpected error in main: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        logger.info("Agent shutdown complete.")

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Run the BasicAgent in interactive mode to manually test functionality
"""

import os
import sys
from dotenv import load_dotenv

# Import the BasicAgent
from basic_agent import BasicAgent

def main():
    """Run BasicAgent in interactive mode"""
    print("\nInitializing BasicAgent for interactive testing...")
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Create the agent
        agent = BasicAgent()
        print("BasicAgent initialized successfully!")
        
        print("\n" + "=" * 40)
        print("INTERACTIVE BASIC AGENT")
        print("=" * 40)
        print("- Enter your query to test the agent")
        print("- Type 'exit' or 'quit' to end the session")
        print("- Available tools: CCRSQL, FinancialSQL, FinancialNewsSearch, EarningsCallSummary,")
        print("                  ControlAnalysis, SECFilingsAnalysis")
        print("=" * 40 + "\n")
        
        # Interactive loop
        while True:
            # Get user query
            query = input("Enter your query (or 'exit' to quit):\n")
            
            # Check for exit command
            if query.lower() in ["exit", "quit", "q"]:
                print("\nExiting interactive session. Goodbye!")
                break
                
            # Run the agent with the query
            print("\n--- Executing query ---")
            try:
                response = agent.run(query)
                print("\n--- Agent Response ---\n")
                print(response)
                print("\n" + "=" * 40 + "\n")
            except Exception as e:
                print(f"\nError running agent: {e}")
    
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        return
        
if __name__ == "__main__":
    main() 
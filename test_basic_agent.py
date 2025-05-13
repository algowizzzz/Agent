#!/usr/bin/env python3
"""
Test script for Phase 2: Basic Agent with CCRSQL Tool
"""

import sys
import os

# Adjust path to import agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from basic_agent import BasicAgent

def run_phase2_tests():
    print("--- Starting Phase 2 Agent Test (CCRSQL) ---")
    
    try:
        agent = BasicAgent()
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        return

    test_queries = [
        # Query likely needing CCRSQL
        "List the top 3 counterparties by Net MTM exposure on most recent date", 
        # Query likely NOT needing CCRSQL
        "What is the weather like today?",
        # Another query likely needing CCRSQL
        "What is the credit limit for JPMorgan Chase & Co.?"
    ]

    for i, query in enumerate(test_queries):
        print(f"\n--- Test {i+1} ---")
        print(f'Query: "{query}"')
        print("Running agent...")
        response = agent.run(query)
        print(f"""\
Final Agent Response:
---
{response}
---""" )

    print("\n--- Phase 2 Agent Test Complete ---")

if __name__ == "__main__":
    run_phase2_tests() 
#!/usr/bin/env python3
"""
Test script for conversation history in BasicAgent
This script simulates a multi-turn conversation to test if the agent
uses previous conversation context.
"""

import os
import sys
import builtins
from unittest.mock import patch
from basic_agent import BasicAgent
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def color_print(text, color):
    """Print text in color."""
    colors = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'end': '\033[0m'
    }
    print(f"{colors.get(color, '')}{text}{colors['end']}")

def test_conversation_history():
    """Run a multi-turn conversation to test history functionality."""
    # Create the agent
    print("\n🔍 Creating BasicAgent instance...")
    agent = BasicAgent()
    
    # Define a sequence of related questions
    conversation = [
        "What are the main financial metrics for evaluating company performance?",
        "Which of these metrics is most important for tech companies?",
        "How do these metrics apply to NVIDIA specifically?"
    ]
    
    # Use the unittest.mock patch to auto-approve plans
    with patch('builtins.input', return_value='y'):
        for i, query in enumerate(conversation):
            turn_num = i + 1
            
            color_print(f"\n==== TURN {turn_num} ====", "magenta")
            color_print(f"User Query: {query}", "cyan")
            
            # Call agent
            print(f"\n🤖 Agent processing turn {turn_num}...")
            response = agent.run(query)
            
            # Extract the final answer part (after thinking steps)
            response_parts = response.split("\n\n", 1)
            if len(response_parts) > 1:
                thinking = response_parts[0]
                answer = response_parts[1]
                
                color_print(f"\nAgent Thinking:", "yellow")
                print(thinking)
                
                color_print(f"\nAgent Response (Turn {turn_num}):", "green")
                print(answer)
            else:
                color_print(f"\nAgent Response (Turn {turn_num}):", "green")
                print(response)
            
            # Optional: show memory contents
            if hasattr(agent, 'memory') and agent.memory:
                color_print("\nCurrent Conversation Memory:", "blue")
                for j, (q, a) in enumerate(agent.memory):
                    print(f"  Memory {j+1} - Q: {q[:50]}... A: {a[:50]}...")
            
            # Pause between turns
            if i < len(conversation) - 1:
                input("\nPress Enter for next turn...")

if __name__ == "__main__":
    try:
        # Run the test
        test_conversation_history()
        color_print("\n✅ Conversation history test completed!", "green")
    except Exception as e:
        color_print(f"\n❌ An error occurred during testing: {e}", "red")
        import traceback
        traceback.print_exc() 
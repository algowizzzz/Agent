#!/usr/bin/env python3
"""
Test script for Control Analysis Tool
"""

import os
import sys
from tools.control_analysis_tool import (
    run_control_analyzer_agent,
    load_controls_data,
    DEFAULT_CONTROLS_PATH
)

def test_controls_data():
    """Test if controls data can be loaded properly"""
    print("Testing control data loading functionality...")
    
    # Check if the default path exists
    print(f"Default controls path: {DEFAULT_CONTROLS_PATH}")
    print(f"Path exists: {os.path.exists(DEFAULT_CONTROLS_PATH)}")
    
    # Try to load the controls data
    controls_data = load_controls_data()
    if isinstance(controls_data, str):
        print(f"❌ Error loading controls data: {controls_data}")
    else:
        print(f"✅ Successfully loaded {len(controls_data)} controls")
        print("\nControl IDs:")
        for control in controls_data:
            print(f"  - {control.get('id')}: {control.get('name')}")

def test_simple_queries():
    """Test basic control analysis queries without LLM"""
    print("\nTesting basic control analysis queries (no LLM)...")
    
    # Test queries (without actually running the LLM)
    test_queries = [
        "List all controls",
        "Tell me about control CTRL-001",
        "Analyze this control: 'Access to the production database is restricted to authorized DBAs only'",
        "Do a 5W analysis on CTRL-002"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        # Don't actually run the agent as it would require an API key
        # Just check if the controls data can be loaded
        controls_data = load_controls_data()
        if isinstance(controls_data, str):
            print(f"❌ Error loading controls data: {controls_data}")
        else:
            print(f"✅ Controls data loaded successfully")
            # Use basic string checking to see what kind of query it is
            if "list all" in query.lower():
                print("  Query type: List all controls")
            elif "ctrl-" in query.lower():
                control_id = query.lower().split("ctrl-")[1].split()[0]
                print(f"  Query type: Get specific control (CTRL-{control_id})")
                # Check if this control exists
                found = False
                for control in controls_data:
                    if control.get("id", "").lower() == f"ctrl-{control_id}":
                        found = True
                        print(f"  Control exists: {control.get('name')}")
                        break
                if not found:
                    print(f"  Control not found: CTRL-{control_id}")
            elif "analyze" in query.lower() or "analysis" in query.lower() or "5w" in query.lower():
                print("  Query type: Analyze control")
                
if __name__ == "__main__":
    print("=== Control Analysis Tool Test ===")
    test_controls_data()
    test_simple_queries()
    print("\nTest completed!") 
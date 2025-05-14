#!/usr/bin/env python3
"""
Simple test for Control Analysis Tool (without using the API)
"""

import os
import json
from tools.control_analysis_tool import (
    load_controls_data,
    DEFAULT_CONTROLS_PATH
)

def main():
    """Test the control analysis tool without making API calls"""
    print("=== CONTROL ANALYSIS TOOL BASIC TEST ===\n")
    
    # Test 1: Check if the tool imports correctly
    print("✅ Successfully imported control_analysis_tool modules")
    
    # Test 2: Check the DEFAULT_CONTROLS_PATH value
    print(f"Default controls path: {DEFAULT_CONTROLS_PATH}")
    
    # Test 3: Create a controls.json file if it doesn't exist
    controls_dir = os.path.dirname(DEFAULT_CONTROLS_PATH)
    os.makedirs(controls_dir, exist_ok=True)
    
    if not os.path.exists(DEFAULT_CONTROLS_PATH):
        print(f"Creating sample controls.json file at {DEFAULT_CONTROLS_PATH}")
        sample_controls = {
            "controls": [
                {
                    "id": "CTRL-001",
                    "name": "Dual Authorization for Large Transfers",
                    "description": "The system requires a secondary authorization for all transfers above $10,000",
                    "type": "Preventative",
                    "category": "Financial",
                    "owner": "Treasury Department",
                    "status": "Active"
                },
                {
                    "id": "CTRL-002",
                    "name": "Personnel Change Approval",
                    "description": "All personnel changes require documented approval from both HR and the department head.",
                    "type": "Detective",
                    "category": "Operational",
                    "owner": "Human Resources",
                    "status": "Active"
                },
                {
                    "id": "CTRL-003",
                    "name": "Data Center Access Control",
                    "description": "Biometric authentication is required for access to the data center, along with an access log that is reviewed monthly.",
                    "type": "Preventative",
                    "category": "Security",
                    "owner": "IT Security",
                    "status": "Active"
                }
            ]
        }
        
        with open(DEFAULT_CONTROLS_PATH, 'w') as f:
            json.dump(sample_controls, f, indent=2)
        print("✅ Created sample controls.json file")
    else:
        print("✅ Controls file already exists")
    
    # Test 4: Load the controls data
    controls_data = load_controls_data()
    
    if isinstance(controls_data, str):
        print(f"❌ Error loading controls data: {controls_data}")
    else:
        print(f"✅ Successfully loaded {len(controls_data)} controls")
        print("\nControl IDs:")
        for control in controls_data:
            print(f"  - {control.get('id')}: {control.get('name')}")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    main() 
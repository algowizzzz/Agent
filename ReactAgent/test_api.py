#!/usr/bin/env python3
"""
Simple script to test the BussGPT API endpoint.
This is an alternative to using the web interface at /test.
"""

import requests
import json
import sys
import time

# API endpoint URL
API_URL = "http://localhost:5001/api/query"

def send_query(query):
    """Send a query to the API and get the response."""
    try:
        print(f"Sending query: {query}")
        print("Waiting for response...")
        
        start_time = time.time()
        response = requests.post(
            API_URL,
            json={"query": query},
            timeout=180  # 3 minutes timeout for long-running queries
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nResponse received in {elapsed_time:.2f} seconds:")
            print(json.dumps(result, indent=2))
            return result
        else:
            print(f"Error: HTTP {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Get query from command line argument
        query = " ".join(sys.argv[1:])
        send_query(query)
    else:
        # Interactive mode
        print("BussGPT API Test")
        print("Type 'exit' or 'quit' to end")
        print("Enter empty line to send the query")
        
        while True:
            print("\nEnter your query:")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            query = "\n".join(lines)
            if query.lower() in ['exit', 'quit']:
                break
            
            if query.strip():
                send_query(query)
            else:
                print("Empty query. Please try again.") 
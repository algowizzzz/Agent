#!/usr/bin/env python3
"""
Standalone API test server for BussGPT.
This provides a simple REST API endpoint for testing the agent without using the full application.
"""

import os
import sys
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import the agent classes
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from langchain_tools.agent import HierarchicalRetrievalAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Create test HTML page
@app.route('/', methods=['GET'])
def test_page():
    """Render a simple test page for the API."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BussGPT API Test</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            textarea { width: 100%; height: 100px; margin-bottom: 10px; }
            button { padding: 10px 20px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
            #response { margin-top: 20px; white-space: pre-wrap; background-color: #f5f5f5; padding: 15px; border-radius: 5px; }
            #spinner { display: none; margin-left: 10px; }
            #thinking { margin-top: 20px; padding: 10px; background-color: #e9f7fb; border-radius: 5px; display: none; }
        </style>
    </head>
    <body>
        <h1>BussGPT API Test Interface</h1>
        <p>Enter your query below to test the agent directly:</p>
        <textarea id="query" placeholder="Enter your query here..."></textarea>
        <div>
            <button onclick="sendQuery()">Send Query</button>
            <span id="spinner">Processing...</span>
        </div>
        <div id="thinking"></div>
        <div id="response"></div>

        <script>
            function sendQuery() {
                const query = document.getElementById('query').value;
                const responseDiv = document.getElementById('response');
                const thinkingDiv = document.getElementById('thinking');
                const spinner = document.getElementById('spinner');
                
                if (!query) {
                    responseDiv.innerText = "Please enter a query";
                    return;
                }
                
                responseDiv.innerText = "Waiting for response...";
                thinkingDiv.style.display = 'none';
                spinner.style.display = 'inline';
                
                fetch('/api/query', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ query: query }),
                })
                .then(response => response.json())
                .then(data => {
                    spinner.style.display = 'none';
                    responseDiv.innerText = JSON.stringify(data, null, 2);
                    
                    // Show thinking steps if available
                    if (data.thinking && data.thinking.length > 0) {
                        thinkingDiv.style.display = 'block';
                        thinkingDiv.innerHTML = '<h3>Agent Thinking Process:</h3><p>' + 
                            data.thinking.join('</p><p>') + '</p>';
                    }
                })
                .catch(error => {
                    spinner.style.display = 'none';
                    responseDiv.innerText = "Error: " + error.message;
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/api/query', methods=['POST'])
def api_query():
    """Handle direct API queries to the agent."""
    data = request.json
    query = data.get('query')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # Process the query
        logger.info(f"Processing API query: {query}")
        
        # Use the query method directly
        response = agent_instance.query(query)
        
        # Return the result
        return jsonify({
            "query": query,
            "response": response
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Load environment variables
    logger.info("Loading environment variables...")
    load_dotenv()
    logger.info("Environment variables loaded.")
    
    # Initialize the agent
    logger.info("Initializing HierarchicalRetrievalAgent...")
    try:
        agent_instance = HierarchicalRetrievalAgent()
        logger.info("HierarchicalRetrievalAgent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        sys.exit(1)
    
    # Start the server
    port = 5002  # Use a different port than the main application
    logger.info(f"Starting API test server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False) 
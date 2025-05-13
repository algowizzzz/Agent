#!/usr/bin/env python3
import os
import logging
import sys
import re  # Added for regex pattern matching
from dotenv import load_dotenv
from langchain_core.runnables import RunnableConfig
from langchain.callbacks.base import BaseCallbackHandler # For potential callback usage if needed

load_dotenv() # Load environment variables from .env file

# Add project root to Python path to find langchain_tools
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging early
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
logger.info("Loading environment variables...")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY") # Needed for the news tool's current implementation

if not ANTHROPIC_API_KEY:
    logger.error("ANTHROPIC_API_KEY not found in environment variables. Exiting.")
    sys.exit(1)
if not SERPAPI_API_KEY:
    logger.error("SERPAPI_API_KEY not found in environment variables. Exiting.")
    sys.exit(1)
logger.info("Environment variables loaded.")

# Use eventlet for async operations with SocketIO
# Note: If eventlet causes issues, you might switch to gevent or Flask's default Werkzeug server (for dev)
import eventlet
eventlet.monkey_patch() # Apply patches for async compatibility

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
from flask_cors import CORS

# Import the agent
try:
    from langchain_tools.agent import HierarchicalRetrievalAgent
except ImportError as e:
    logger.error(f"Failed to import HierarchicalRetrievalAgent: {e}")
    logger.error("Ensure langchain_tools is in the Python path and all dependencies are installed.")
    sys.exit(1)

# --- Flask App Setup ---
logger.info("Initializing Flask app and SocketIO...")
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_very_secret_key_here!' # Change this for production
# Enable CORS for all domains on /socket.io endpoint - adjust for production
CORS(app, resources={r"/socket.io/*": {"origins": "*"}})
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")
logger.info("Flask app and SocketIO initialized.")

# --- Agent Initialization ---
agent_instance = None
try:
    logger.info("Initializing HierarchicalRetrievalAgent...")
    # Initialize agent (ensure API keys are passed if needed, or rely on env vars)
    # Assuming the agent class constructor primarily uses os.getenv internally now
    agent_instance = HierarchicalRetrievalAgent(api_key=ANTHROPIC_API_KEY, debug=True) # Pass key explicitly? Relies on internal usage.
    # Ensure agent_executor is accessible. Assuming it's agent_instance.agent_executor
    if not hasattr(agent_instance, 'agent_executor'):
         raise AttributeError("Agent instance does not have an 'agent_executor' attribute.")
    logger.info("HierarchicalRetrievalAgent initialized successfully.")
except Exception as e:
    logger.exception(f"Fatal error initializing agent: {e}")
    # Optionally, allow server to run without agent or exit
    sys.exit(1) # Exit if agent fails to initialize

# Add this after app initialization but before socketio setup
@app.route('/test', methods=['GET'])
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
        <div id="response"></div>

        <script>
            function sendQuery() {
                const query = document.getElementById('query').value;
                const responseDiv = document.getElementById('response');
                const spinner = document.getElementById('spinner');
                
                if (!query) {
                    responseDiv.innerText = "Please enter a query";
                    return;
                }
                
                responseDiv.innerText = "Waiting for response...";
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
        # Get the agent instance
        agent = app.config.get("AGENT_INSTANCE")
        if not agent:
            return jsonify({"error": "Agent not initialized"}), 500
        
        # Process the query
        logger.info(f"Processing API query: {query}")
        response = agent.run(query)
        
        # Return the result
        return jsonify({
            "query": query,
            "response": response
        })
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": str(e)}), 500

# --- SocketIO Event Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handle new client connection."""
    logger.info(f"Client connected: {request.sid}")
    emit('connection_success', {'message': 'Connected to agent backend!', 'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming chat messages from the client. Using synchronized eventlet-compatible approach."""
    # --- Start Enhanced Logging ---
    logger.info(f"*** CHAT_MESSAGE EVENT RECEIVED: {request.sid} ***")
    logger.info(f"*** chat_message event received for SID: {request.sid} ***")
    if isinstance(data, dict):
        query = data.get('message', '')
        logger.info(f"*** Raw data received (dict): {data} ***")
    else:
        # Handle the case where data is a string
        query = str(data)
        logger.info(f"*** Raw data received (string): {query} ***")
    # --- End Enhanced Logging ---

    if agent_instance is None or not hasattr(agent_instance, 'agent_executor'):
        logger.error("Agent or agent_executor not initialized, cannot process message.")
        emit('agent_error', {'error': 'Agent not initialized on backend.'}, room=request.sid)
        return

    if not query:
        logger.warning(f"Received empty message from {request.sid}")
        emit('agent_error', {'error': 'Received empty message.'}, room=request.sid)
        return

    logger.info(f"Received query from {request.sid}: '{query}'")
    
    # Using the actual agent - simplified execution flow without nested functions
    # First emit thinking state to show the user we're processing their query
    emit('thinking', {'status': 'thinking'}, room=request.sid)
    
    # Define a simpler agent execution function for eventlet
    def execute_agent_query():
        try:
            # Use the synchronous invoke method
            result = agent_instance.agent_executor.invoke(
                {"input": query},
                config={"configurable": {"session_id": request.sid}}
            )
            
            # Extract the final answer
            final_answer = result.get('output', 'No response generated.')
            
            # Emit the final answer
            logger.info(f"Agent execution completed. Final Answer for {request.sid}: '{final_answer}'")
            socketio.emit('agent_response', {'content': final_answer, 'sender': 'agent'}, room=request.sid)
            
        except Exception as e:
            error_message = f"Error during agent execution: {e}"
            logger.exception(f"Error processing query for {request.sid}: {e}")
            socketio.emit('agent_error', {'error': error_message}, room=request.sid)
    
    # Use eventlet's spawn directly (no nested functions)
    eventlet.spawn(execute_agent_query)
    logger.info(f"Spawned agent task for {request.sid}")
    
    # Non-blocking return from the event handler
    logger.info(f"Finished handling chat_message for {request.sid}")

# --- Routes for health check ---
@app.route('/health')
def health_check():
    """Simple health check endpoint."""
    return {'status': 'healthy', 'agent_initialized': agent_instance is not None}

# --- Main Execution ---
if __name__ == '__main__':
    # Loading environment variables
    logger.info("Loading environment variables...")
    load_dotenv()
    logger.info("Environment variables loaded.")
    
    # Initialize Flask app and SocketIO
    logger.info("Initializing Flask app and SocketIO...")
    app = Flask(__name__)
    CORS(app)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")
    logger.info("Flask app and SocketIO initialized.")
    
    # Initialize HierarchicalRetrievalAgent
    logger.info("Initializing HierarchicalRetrievalAgent...")
    try:
        agent_instance = HierarchicalRetrievalAgent()
        app.config["AGENT_INSTANCE"] = agent_instance  # Store agent in app config for API access
        logger.info("HierarchicalRetrievalAgent initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {str(e)}")
        sys.exit(1) # Exit if agent fails to initialize
    
    # Start Backend Server
    logger.info("Starting backend server...")
    try:
        logger.info("Attempting to start SocketIO server on 0.0.0.0:5001...")
    # Use eventlet server
        # Listen on all interfaces (0.0.0.0) on port 5001
        socketio.run(app, host='0.0.0.0', port=5001, use_reloader=False, log_output=True)
        logger.info("--- SocketIO server finished running (graceful shutdown?) ---")
    except Exception as e:
        logger.exception(f"--- CRITICAL ERROR during server run: {e} ---")
    finally:
        logger.info("--- Backend server process ending. ---")
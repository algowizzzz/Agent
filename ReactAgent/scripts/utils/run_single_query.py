"""
Run a single query through the hierarchical retrieval agent with detailed logging.
"""

import os
import json
import logging
import sys
import traceback
import re
from datetime import datetime
from langchain_tools.agent import HierarchicalRetrievalAgent
from typing import Dict, Any, List
from dataclasses import dataclass, asdict
import io

# Set up logging buffer first
log_buffer = io.StringIO()
log_handler = logging.StreamHandler(log_buffer)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
log_handler.setLevel(logging.DEBUG)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[log_handler, logging.StreamHandler(sys.stdout)]
)

# Get the root logger and ensure our handler is attached
root_logger = logging.getLogger()
if log_handler not in root_logger.handlers:
    root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)

@dataclass
class ToolExecution:
    tool_name: str
    timestamp: str
    input_data: Dict[str, Any]
    output_data: Any

class ToolExecutionTracker:
    def __init__(self):
        self.executions: List[ToolExecution] = []
    
    def add_execution(self, tool_name: str, input_data: Dict[str, Any], output_data: Any):
        execution = ToolExecution(
            tool_name=tool_name,
            timestamp=datetime.now().isoformat(),
            input_data=input_data,
            output_data=output_data
        )
        self.executions.append(execution)
        logger.debug(f"Added tool execution: {tool_name} at {execution.timestamp}")
    
    def get_executions(self) -> List[ToolExecution]:
        return self.executions

def sanitize_filename(query: str) -> str:
    """Convert query to a valid filename"""
    # Remove invalid filename characters
    filename = re.sub(r'[<>:"/\\|?*]', '', query)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Add timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{filename}_{timestamp}.txt"

def format_tool_executions(executions: List[ToolExecution]) -> str:
    """Format tool executions into readable text"""
    output = []
    for i, execution in enumerate(executions, 1):
        output.append(f"Tool Execution #{i}")
        output.append("-" * 50)
        output.append(f"Tool: {execution.tool_name}")
        output.append(f"Timestamp: {execution.timestamp}\n")
        
        output.append("Input:")
        output.append(json.dumps(execution.input_data, indent=2))
        output.append("\nOutput:")
        output.append(json.dumps(execution.output_data, indent=2))
        output.append("=" * 50 + "\n")
    
    return "\n".join(output)

def save_response_to_file(query: str, response: Any, tracker: ToolExecutionTracker, complete_log: str):
    """Save the query response, tool executions, and complete log to a file"""
    try:
        filename = sanitize_filename(query)
        output_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write(f"Query: {query}\n")
            f.write(f"Execution Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write("COMPLETE LOG OUTPUT\n")
            f.write("=" * 50 + "\n")
            f.write(complete_log)
            f.write("\n" + "=" * 50 + "\n\n")
            
            f.write("TOOL EXECUTIONS\n")
            f.write("=" * 50 + "\n")
            f.write(format_tool_executions(tracker.get_executions()))
            f.write("\n")
            
            f.write("FINAL RESPONSE\n")
            f.write("=" * 50 + "\n")
            f.write(json.dumps(response, indent=2))
        
        logger.info(f"Response saved to: {filepath}")
        print(f"\nResponse saved to: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving response to file: {str(e)}")
        print(f"Error saving response to file: {str(e)}")
        return False

def wrap_tool_with_tracking(tool, tool_name: str, tracker: ToolExecutionTracker):
    """Wrap a tool to track its execution"""
    original_func = tool.__call__
    
    def tracked_call(*args, **kwargs):
        input_data = {"args": args, "kwargs": kwargs}
        logger.debug(f"Executing tool {tool_name} with input: {input_data}")
        try:
            output = original_func(*args, **kwargs)
            logger.debug(f"Tool {tool_name} output: {output}")
            tracker.add_execution(tool_name, input_data, output)
            return output
        except Exception as e:
            error_data = {
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"Tool {tool_name} failed: {error_data}")
            tracker.add_execution(tool_name, input_data, error_data)
            raise
    
    tool.__call__ = tracked_call
    return tool

def main():
    logger.info("Starting query execution")
    
    # Get API key from environment
    logger.debug("Checking for API key")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    logger.info("API key found")
    
    try:
        # Initialize tool execution tracker
        tracker = ToolExecutionTracker()
        logger.debug("Tool execution tracker initialized")
        
        # Initialize agent with debug logging
        logger.debug("Initializing HierarchicalRetrievalAgent")
        agent = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
        
        # Wrap agent's tools with tracking
        if hasattr(agent, 'tools'):
            for i, tool in enumerate(agent.tools):
                tool_name = f"tool_{i}_{tool.__class__.__name__}"
                agent.tools[i] = wrap_tool_with_tracking(tool, tool_name, tracker)
                logger.debug(f"Wrapped tool: {tool_name}")
        
        logger.info("Agent initialized successfully")
        
        # Get query from command line argument
        if len(sys.argv) < 2:
            logger.error("No query provided in command line arguments")
            print("Please provide a query as a command line argument")
            sys.exit(1)
        
        query = " ".join(sys.argv[1:])
        logger.info(f"Received query: {query}")
        
        # Create output filename from query
        output_file = sanitize_filename(query)
        logger.debug(f"Created output filename: {output_file}")
        
        # Run the query through the agent
        logger.debug("Starting agent query execution")
        response = agent.query(query)
        logger.info("Query execution completed")
        
        # Get tool executions
        tool_executions = tracker.get_executions()
        logger.debug(f"Retrieved {len(tool_executions)} tool executions")
        
        # Get complete log output
        complete_log = log_buffer.getvalue()
        logger.debug("Retrieved complete log output")
        
        # Print the response in a readable format
        print("\nTool Executions:")
        print(format_tool_executions(tool_executions))
        
        print("\nFinal Response:")
        print("-" * 50)
        print(json.dumps(response, indent=2))
        
        # Save complete response to file
        save_response_to_file(query, response, tracker, complete_log)
        print(f"\nComplete execution log saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        error_response = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        # Try to save error response and logs even if execution failed
        save_response_to_file(query, error_response, tracker, log_buffer.getvalue())
        sys.exit(1)
    finally:
        # Clean up
        log_buffer.close()

if __name__ == "__main__":
    main() 
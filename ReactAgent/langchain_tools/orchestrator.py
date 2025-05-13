"""
Orchestrates the execution of tools in the required sequence for the Hierarchical Retrieval Agent.
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Tuple
from langchain.tools import Tool # Assuming BaseTool or Tool is used
import re
import traceback
from datetime import datetime

# Assuming AgentState is defined in state_manager.py
from .state_manager import AgentState

logger = logging.getLogger(__name__)

class ToolChainOrchestrator:
    """Manages the sequential execution of tools based on agent state."""

    def __init__(self, tools: Dict[str, Callable], state: AgentState):
        """Initialize orchestrator with available tools and agent state reference."""
        if not isinstance(tools, dict):
            raise TypeError("Tools must be provided as a dictionary.")
        if not isinstance(state, AgentState):
             raise TypeError("State must be an instance of AgentState.")
             
        self.tools = tools # Store the actual callable functions, not LangChain Tool objects initially
        self.state = state
        # Define the mandatory sequence
        self.required_sequence = ['department_tool', 'category_tool', 'document_tool']
        logger.info(f"Orchestrator initialized with tools: {list(self.tools.keys())}")

    def _get_expected_next_tool(self) -> Optional[str]:
        """Determines the next expected tool based on the sequence and state."""
        current_tool_count = len(self.state.tool_sequence)
        
        # Check sequence completion
        if current_tool_count >= len(self.required_sequence):
             # If sequence is done, but docs are pending, expect document_tool
             if self.state.pending_doc_ids:
                 logger.debug("Sequence complete, but documents pending. Expecting document_tool.")
                 return 'document_tool'
             else:
                 logger.debug("Required tool sequence completed.")
                 return None # Sequence finished
                 
        # Determine next tool in the defined sequence
        expected_tool = self.required_sequence[current_tool_count]
        logger.debug(f"Next expected tool in sequence: {expected_tool}")
        return expected_tool

    def validate_tool_call(self, tool_name: str) -> Tuple[bool, Optional[str]]:
        """Validates if the requested tool call is allowed based on the current state and sequence."""
        if tool_name not in self.tools:
            logger.error(f"Validation failed: Tool '{tool_name}' is not available.")
            return False, f"Tool '{tool_name}' not found."
            
        expected_tool = self._get_expected_next_tool()

        # If documents are pending, only document_tool is allowed
        if self.state.pending_doc_ids and tool_name != 'document_tool':
             logger.warning(f"Validation failed: Tool '{tool_name}' called, but documents are pending. Expected 'document_tool'.")
             return False, "Pending documents must be processed first using 'document_tool'."
             
        # Check against required sequence if no documents are pending or if it's the document tool itself
        if expected_tool is not None and tool_name != expected_tool:
            logger.warning(f"Validation failed: Tool '{tool_name}' called out of sequence. Expected '{expected_tool}'.")
            return False, f"Tool '{tool_name}' called out of sequence. Expected '{expected_tool}'."
            
        logger.debug(f"Tool call validation successful for '{tool_name}'.")
        return True, None # Validation successful

    def execute_tool(self, tool_name: str, tool_input: Any) -> Dict[str, Any]:
        """Executes the specified tool after validation, using the raw callable."""
        is_valid, error_msg = self.validate_tool_call(tool_name)
        if not is_valid:
            # Return a structured error response consistent with tool outputs
            return {
                 "thought": f"Orchestrator validation failed: {error_msg}",
                 "answer": f"Error: {error_msg}",
                 "confidence": 0,
                 "metadata": {
                     "tool_name": tool_name,
                     "error": error_msg,
                     "timestamp": datetime.utcnow().isoformat(),
                     "success": False
                 }
             }

        try:
            tool_function = self.tools[tool_name]
            logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
            
            # Execute the tool function (which should handle its own validation/metadata now)
            # Pass input appropriately - needs careful handling based on how agent provides it
            # Assuming tool_input is a string that might contain parameters like "query, category=X" or "query, doc_ids=[...]"
            # The tool wrappers in the agent or the tool itself should handle parsing this.
            # For now, pass the raw input string.
            
            # **** IMPORTANT REFACTORING NOTE ****
            # This assumes the agent provides the *full* input string including parameters.
            # The tool factory's `create_tool_with_validation` wrapper expects the *base* tool function.
            # The base tool functions (`department_summary_tool`, etc.) expect *parsed* arguments (query, category_id, doc_ids).
            # SOLUTION: The agent's integration (Phase 4) MUST parse the `tool_input` string from the LLM
            # and pass the correct arguments (e.g., query=..., category_id=...) to the tool function here.
            # For now, this will likely fail until Phase 4 integration parses the input correctly.
            # Let's proceed, but mark this as a critical integration point.
            
            # Placeholder for correct argument parsing (to be done in Agent integration)
            if tool_name == "department_tool":
                 # Expects query string
                 result = tool_function(query=tool_input) 
            elif tool_name == "category_tool":
                 # Expects query string, category_id optional extracted from string
                 # Simplified call - actual parsing needed in agent
                 cat_match = re.search(r'category=(\w+)', tool_input, re.IGNORECASE)
                 query_part = re.sub(r',\s*category=\w+', '', tool_input).strip()
                 cat_id = cat_match.group(1).upper() if cat_match else None
                 result = tool_function(query=query_part, category_id=cat_id)
            elif tool_name == "document_tool":
                 # Expects query string, list of doc_ids extracted from string
                 # Simplified call - actual parsing needed in agent
                 doc_match = re.search(r'doc_ids=\[(.*?)\]', tool_input)
                 query_part = re.sub(r',\s*doc_ids=\[.*?\]', '', tool_input).strip()
                 doc_ids_list = [d.strip().strip("'\"") for d in doc_match.group(1).split(',')] if doc_match else []
                 result = tool_function(query=query_part, doc_ids=doc_ids_list)
            else:
                 # Fallback for safety, though validation should prevent this
                 result = tool_function(tool_input)
            
            # Update state AFTER successful execution 
            self.state.update_from_tool_result(tool_name, result)
            
            logger.info(f"Tool {tool_name} executed successfully.")
            return result
            
        except Exception as e:
            logger.exception(f"Exception during execution of tool '{tool_name}': {e}") # Use logger.exception for traceback
            error_result = {
                 "thought": f"Execution error in {tool_name}: {str(e)}",
                 "answer": f"Error executing tool '{tool_name}'",
                 "confidence": 0,
                 "metadata": {
                     "tool_name": tool_name,
                     "error": str(e),
                     "traceback": traceback.format_exc(), # Include traceback
                     "timestamp": datetime.utcnow().isoformat(),
                     "success": False
                 }
            }
            # Update state with error information
            self.state.update_from_tool_result(tool_name, error_result)
            return error_result

    def get_next_required_tool_name(self) -> Optional[str]:
        """Returns the name of the next tool required by the sequence, or None if complete or only docs pending."""
        return self._get_expected_next_tool() 
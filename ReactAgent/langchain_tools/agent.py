"""
Multi-tool hierarchical retrieval agent implementation using structured components.
"""

import logging
import re
import traceback
import time
import json
import os # Added os import
from typing import List, Dict, Any, Optional, Set, Union, Callable
from dataclasses import asdict

from langchain.agents import AgentExecutor, create_react_agent # Using newer AgentExecutor
from langchain_core.agents import AgentAction, AgentFinish
from langchain_anthropic import ChatAnthropic
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from requests.exceptions import ConnectionError
from functools import wraps

# Import new structured components
from .state_manager import AgentState
from .orchestrator import ToolChainOrchestrator
from .output_parser import EnhancedAgentOutputParser # Use the new parser
from .logger import AgentLogger

# Import tool factory and config
from .tool_factory import (
    create_department_tool, 
    create_category_tool, 
    create_metadata_lookup_tool_wrapper as create_metadata_lookup_tool, 
    create_document_analysis_tool_wrapper as create_transcript_analysis_tool, 
    create_financial_sql_tool,  # Updated SQL tool factory import
    create_ccr_sql_tool,  # Added CCR tool factory import
    create_transcript_agent_tool, # <-- Add new transcript agent tool factory
    create_financial_news_search_tool, # <--- Import the new news tool factory
    create_llm
)
from . import agent_config

# Configure detailed logging (basicConfig should ideally be called only once at entry point)
# Assuming it's configured elsewhere, get logger
logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1 # seconds

def retry_on_connection_error(func):
    """Decorator to retry functions on connection errors."""
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except ConnectionError as e:
                if attempt == MAX_RETRIES - 1:
                    logger.error(f"Max retries ({MAX_RETRIES}) reached. Last error: {str(e)}")
                    raise
                logger.warning(f"Connection error on attempt {attempt + 1}/{MAX_RETRIES}. Retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY * (attempt + 1)) # Exponential backoff
    return wrapper

class HierarchicalRetrievalAgent:
    """
    A hierarchical retrieval agent using structured components for state, orchestration, and logging.
    """
    
    def __init__(self, api_key: str = None, debug: bool = False):
        """Initialize the agent with structured components."""
        self.api_key = api_key
        self.debug = debug
        self.agent_id = "HierarchicalAgent_v3_Refactored" # Update version ID
        
        if self.debug:
            logging.getLogger("langchain_tools").setLevel(logging.DEBUG) # Set level for this module
            logging.getLogger(__name__).setLevel(logging.DEBUG)
        else:
             logging.getLogger("langchain_tools").setLevel(logging.INFO)
             logging.getLogger(__name__).setLevel(logging.INFO)

        self.state = AgentState() # Centralized state manager
        self.logger = AgentLogger(self.agent_id) # Structured logger
        
        try:
            # Initialize LLM first
            logger.debug("Initializing LLM")
            self.llm = self._initialize_llm()
            logger.info("LLM initialized successfully")
            
            # Initialize tools via factory - Master Agent Tools
            logger.debug("Initializing tools for Master Agent")
            
            # Define DB paths
            # Assuming script runs from project root where BussGPT is the root
            # Correctly find the project root relative to this file
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            financial_db_path = os.path.join(project_root, "scripts", "data", "financial_data.db") 
            # Make CCR DB path relative to project root as well
            ccr_db_path = os.path.join(project_root, "scripts", "data", "ccr_reporting.db") 
            
            # Only initialize the tools the Master Agent will directly use
            master_agent_tools = {
                "financial_sql_query_tool": create_financial_sql_tool(db_path=financial_db_path, llm=self.llm),
                # --- UNCOMMENTED CCR tool creation ---
                "ccr_sql_query_tool": create_ccr_sql_tool(db_path=ccr_db_path, llm=self.llm),
                # ---
                "transcript_search_summary_tool": create_transcript_agent_tool(llm=self.llm, api_key=self.api_key),
                "financial_news_search": create_financial_news_search_tool() # Instantiate the news tool
            }
            
            # Convert to LangChain Tools (descriptions loaded here)
            # We might need to update agent_config descriptions for the new tool
            self.tools = self._create_langchain_tools(master_agent_tools) 
            logger.info("Master Agent tools initialized successfully")
            if self.tools:
                logger.info(f"Master Agent initialized with tools: {[tool.name for tool in self.tools]}")
            else:
                logger.warning("Master Agent - No tools were initialized!")
            
            # Initialize orchestrator (Does this need changing? Maybe not if it just uses the final tools list)
            self.orchestrator = ToolChainOrchestrator(master_agent_tools, self.state) # Pass the dict of tools
            logger.info("Orchestrator initialized")
            
            # Initialize agent executor with the Master Agent's tools
            logger.debug("Initializing Master Agent executor")
            self.agent_executor = self._initialize_agent_executor() # Uses self.tools
            logger.info("Master Agent executor initialized successfully")
            
        except Exception as e:
            logger.exception("Fatal error during agent initialization")
            raise
            
    def _create_langchain_tools(self, raw_tools_dict: Dict[str, Union[Callable, Tool]]) -> List[Tool]:
        """Convert raw tool callables/Tools into LangChain Tool objects, loading descriptions."""
        # Ensure descriptions from agent_config cover the new high-level tools
        descriptions = agent_config.get_tool_descriptions()
        
        lc_tools = []
        for name, tool_or_func in raw_tools_dict.items():
            if isinstance(tool_or_func, Tool):
                # Use the description from the Tool object by default
                # Override if a description exists in agent_config
                desc = descriptions.get(name, tool_or_func.description)
                tool_or_func.description = desc # Update tool's description
                lc_tools.append(tool_or_func)
                logger.debug(f"Loaded Tool: {name} with description: {desc}")
            elif callable(tool_or_func):
                # This path likely won't be used now if all tools are pre-wrapped
                if name not in descriptions:
                    logger.warning(f"No description found for tool function '{name}'. Skipping.")
                    continue
                lc_tools.append(Tool(name=name, func=tool_or_func, description=descriptions[name]))
                logger.debug(f"Wrapped function tool: {name} with description: {descriptions[name]}")
            else:
                 logger.warning(f"Item '{name}' in raw_tools is neither a Tool nor callable. Skipping.")
                 
        return lc_tools
    
    @retry_on_connection_error
    def _initialize_llm(self) -> ChatAnthropic:
        """Initialize the LLM client using the factory."""
        logger.debug("Initializing LLM")
        try:
            # Use the create_llm function from the factory for consistency
            llm_instance = create_llm(
                api_key=self.api_key,
                # model="claude-3.5-sonnet-20240620" # Typo
                model="claude-3-5-sonnet-20240620" # Corrected model
            )
            logger.debug("ChatAnthropic instance created successfully via factory")
            return llm_instance
        except Exception as e:
            logger.exception(f"Failed to initialize LLM: {e}")
            raise
    
    def _initialize_agent_executor(self):
        """Initialize the Master Agent AgentExecutor with React agent."""
        # Use the enhanced output parser
        output_parser = EnhancedAgentOutputParser()
        
        # Create prompt template from config - THIS PROMPT NEEDS UPDATING for the 3 master tools
        # Make sure agent_config.AGENT_PROMPT reflects the new toolset
        if not hasattr(agent_config, 'MASTER_AGENT_PROMPT'):
             logger.warning("Using generic AGENT_PROMPT for Master Agent. Consider creating MASTER_AGENT_PROMPT in agent_config.py")
             prompt_template_str = agent_config.AGENT_PROMPT
        else:
             prompt_template_str = agent_config.MASTER_AGENT_PROMPT
             
        prompt = PromptTemplate.from_template(prompt_template_str)
        
        # Create the ReAct Agent for the Master Agent
        master_react_agent = create_react_agent(self.llm, self.tools, prompt)
        
        # Get agent executor config
        config = agent_config.AGENT_CONFIG
        
        # Create the AgentExecutor for the Master Agent
        return AgentExecutor(
            agent=master_react_agent,
            tools=self.tools, # Pass the high-level tools (SQLx2, TranscriptAgent)
            verbose=config["verbose"],
            max_iterations=config["max_iterations"], # Maybe fewer iterations for master?
            early_stopping_method=config["early_stopping_method"],
            handle_parsing_errors=self._handle_parsing_error, # Use existing handler
        )
        
    def _handle_parsing_error(self, error: Exception) -> str:
        """Custom handler for parsing errors from the output parser."""
        error_str = str(error)
        logger.error(f"Output parsing error encountered: {error_str}")
        # Check if it's the specific error we expect from our parser
        if "Could not parse LLM output" in error_str:
             # Extract the problematic output from the error message if possible
             match = re.search(r"`(.+)`", error_str)
             problematic_output = match.group(1) if match else "[Could not extract]"
             # Provide specific feedback to the LLM
             feedback = (f"Parsing Error: Your previous response could not be parsed. "
                         f"Ensure you strictly follow the format: Thought:, Action:, Action Input:, or Final Answer:. "
                         f"Problematic Response Snippet: {problematic_output[:500]}")
             return feedback
        else:
             # Generic error handling for other parsing issues
             return f"Error: Could not parse your response. Please ensure correct format. Details: {error_str[:500]}"

    def _run_agent_step(self, inputs: Dict) -> Union[AgentAction, AgentFinish]:
        """ Placeholder for potential custom step execution logic if needed """
        # This might involve interacting with the orchestrator before/after agent steps
        # For now, rely on standard AgentExecutor loop
        raise NotImplementedError("Custom step execution not implemented yet")

    def _format_final_response(self, agent_outcome: Dict) -> Dict[str, Any]:
        """Formats the final response based on agent execution outcome and state."""
        final_answer = agent_outcome.get('output', "No final answer generated.")
        status = "success" if final_answer else "error"
        error_msg = None

        # Check for errors during execution (AgentExecutor might put errors in 'output')
        if isinstance(final_answer, str) and "Error:" in final_answer:
            status = "error"
            error_msg = final_answer
            final_answer = "Agent execution failed." # Clear the error from the primary answer
            
        # Check state for errors or incomplete processing
        if self.state.last_error:
            status = "error"
            error_msg = self.state.last_error
            
        if self.state.pending_doc_ids:
             status = "error" # Or maybe "incomplete"?
             error_msg = f"Query finished with unprocessed documents: {list(self.state.pending_doc_ids)}"
             logger.warning(error_msg)
             
        return {
            "status": status,
            "result": final_answer,
            "error": error_msg,
            "evidence": self.state.evidence_collected,
            "confidence": self.state.current_confidence,
            "tool_sequence": self.state.tool_sequence,
            "category_identified": self.state.category_id
        }

    # @retry_on_connection_error # Apply retry to the main query method
    def query(self, query: str) -> Dict[str, Any]:
        """Execute a query using the structured agent components."""
        self.state.reset() # Reset state for the new query
        self.state.last_query = query
        self.logger.start_query(query)
        
        final_outcome = None
        try:
            # Use the agent executor's invoke method
            # The executor handles the loop of Thought -> Action -> Observation
            # It will use the tools provided, which are wrapped with validation
            # It will use the parser provided via the agent
            inputs = {"input": query} 
            final_outcome = self.agent_executor.invoke(inputs)
            logger.info(f"AgentExecutor finished. Outcome: {final_outcome}")

        except Exception as e:
            logger.exception(f"Unhandled exception during agent execution: {str(e)}")
            self.state.last_error = f"Agent execution failed: {str(e)}"
            # Construct a basic error outcome if invoke fails completely
            final_outcome = {'output': f"Agent execution failed with error: {str(e)}"} 
            
        # Format the response using the final state
        formatted_response = self._format_final_response(final_outcome or {})
        
        # Prepare state for logging (ensure sets are converted)
        loggable_state = asdict(self.state)
        for key, value in loggable_state.items():
            if isinstance(value, set):
                loggable_state[key] = list(value)

        # Log the final state and response
        # self.logger.end_query(formatted_response, asdict(self.state)) # Original
        self.logger.end_query(formatted_response, loggable_state) # Use sanitized state
        
        return formatted_response

# Example usage (for testing)
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        exit(1)
        
    agent_instance = HierarchicalRetrievalAgent(api_key=api_key, debug=True)
    
    test_query = "What was Amazon's cloud revenue in Q2 2019?"
    result = agent_instance.query(test_query)
    
    print("\n--- Final Result ---")
    print(json.dumps(result, indent=2))
    print("-------------------") 
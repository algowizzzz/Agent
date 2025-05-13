"""
ReAct Agent Wrapper for Enterprise Internal Agent

This module implements a ReAct (Reasoning + Acting) agent wrapper around the
existing Enterprise Internal Agent pipeline. It allows for more conversational
and dynamic handling of user queries while leveraging the robust financial
data processing capabilities of the existing agent.
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Optional

# Setup logging
logger = logging.getLogger(__name__)

class ReactAgentWrapper:
    """
    A ReAct agent wrapper that can enhance the existing Enterprise Internal Agent
    with more conversational capabilities and dynamic reasoning.
    """
    
    def __init__(self, 
                llm,
                tools_map: Dict,
                db_paths: Dict,
                api_key: str,
                max_iterations: int = 10):
        """
        Initialize the ReAct agent wrapper.
        
        Args:
            llm: The language model to use for reasoning
            tools_map: Map of tool names to their callable functions
            db_paths: Dictionary of database paths
            api_key: API key for external services
            max_iterations: Maximum number of reasoning iterations
        """
        self.llm = llm
        self.tools_map = tools_map
        self.db_paths = db_paths
        self.api_key = api_key
        self.max_iterations = max_iterations
        self.conversation_history = []
    
    def run(self, query: str) -> str:
        """
        Run the ReAct agent on a user query.
        
        Args:
            query: The user's query
            
        Returns:
            The agent's response
        """
        # Ensure tools_map is populated
        if not self.tools_map:
             logger.error("[ReAct] Tools map is empty during run. Initialization might have failed.")
             return "ERROR: Agent tools are not configured correctly."
             
        # Initialize the system prompt with conversation history
        system_prompt = self._create_system_prompt(query)
        
        # Initialize messages for the LLM
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Track the full ReAct trace for logging
        react_trace = []
        
        # Main ReAct Loop
        for i in range(self.max_iterations):
            logger.info(f"[ReAct] Iteration {i+1}/{self.max_iterations}")
            
            # Get the next reasoning step from the LLM
            response = self.llm.invoke(messages)
            response_text = response.content
            react_trace.append(response_text)
            logger.debug(f"[ReAct] LLM Response: {response_text}") # Add debug logging
            
            # Check if we've reached a final answer
            if "Final Answer:" in response_text:
                final_answer = response_text.split("Final Answer:")[1].strip()
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": final_answer})
                
                logger.info(f"[ReAct] Found final answer after {i+1} iterations")
                return final_answer
            
            # Extract thought and action
            tool_name = None
            tool_input = None
            
            if "Action:" in response_text:
                # Parse the action
                action_text = response_text.split("Action:")[1].split("\n")[0].strip()
                
                # Extract tool name and parameters
                tool_match = re.match(r"(\\w+)\\((.*)\\)", action_text, re.DOTALL) # Use DOTALL to handle multiline inputs
                if tool_match:
                    tool_name = tool_match.group(1).strip()
                    # Handle potential quotes around the input, common with LLM outputs
                    tool_input = tool_match.group(2).strip().strip('\'"') 
                    
                    logger.info(f"[ReAct] Attempting Action: {tool_name}({tool_input[:100]}...)") # Log parsed action
                    
                    # Execute the tool
                    observation = self._execute_tool(tool_name, tool_input)
                    
                    # Add to the message chain
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": observation})
                    react_trace.append(observation)
                else:
                    # If action parsing fails, provide feedback to the LLM
                    logger.warning(f"[ReAct] Could not parse Action: {action_text}")
                    observation = f"Observation: Invalid Action format. Expected 'tool_name(parameters)', got '{action_text}'. Please check your syntax."
                    messages.append({"role": "assistant", "content": response_text})
                    messages.append({"role": "user", "content": observation})
                    react_trace.append(observation)
            else:
                 # If no action found, treat it as needing more thought or maybe a final answer was intended but poorly formatted
                 logger.warning(f"[ReAct] No 'Action:' found in response: {response_text}")
                 # We might just append the assistant's response and let it try again, 
                 # or provide specific feedback if it seems stuck.
                 # For now, let's assume it's part of the thought process and needs another cycle.
                 messages.append({"role": "assistant", "content": response_text}) 
                 # Optionally add a user message like: messages.append({"role": "user", "content": "Observation: Please provide an Action or Final Answer."})
        
        # If we reach here, we've hit max iterations without a final answer
        logger.warning(f"[ReAct] Reached maximum iterations ({self.max_iterations}) without final answer")
        return "I apologize, but I wasn't able to reach a definitive answer to your query after multiple attempts. Please try rephrasing your question or breaking it down into smaller parts."
    
    def _create_system_prompt(self, query: str) -> str:
        """Create the system prompt for the ReAct agent."""
        # Format conversation history
        formatted_history = ""
        if self.conversation_history:
            for msg in self.conversation_history[-6:]:  # Last 3 turns
                role = "User" if msg["role"] == "user" else "Assistant"
                formatted_history += f"{role}: {msg['content']}\n"
        
        # Format tools description
        tools_desc = self._format_tools_description()
        
        return f"""
You are an Enterprise Financial Assistant that helps with financial data queries using a combination of reasoning and acting.

You have access to the following tools:
{tools_desc}

Follow this format:
Thought: your reasoning about what to do next
Action: tool_name(parameters)
Observation: result of the action
... (this Thought/Action/Observation can repeat multiple times)
Thought: I now know the final answer
Final Answer: the response to the user's query

Previous conversation:
{formatted_history}

Begin working on: {query}
"""
    
    def _format_tools_description(self) -> str:
        """Format the tools description for the system prompt using individual tools."""
        # Descriptions adapted from agents/internal_agent.py
        # Make sure the parameter format "(parameter: type)" is clear for the LLM.
        tools_desc = [
            "FinancialSQL(query: str): Query the internal financial database with SQL. Use for financial metrics, e.g. revenue, profit for specific historical periods (2016-2020). Input must be a natural language question about the specific data needed.",
            "CCRSQL(query: str): Query the CCR database for customer credit risk records. Use for credit/risk info, exposures, limits, ratings. Input must be a natural language question about specific CCR data.",
            "FinancialNewsSearch(query: str): Search recent financial news articles or current market info using keywords or company name. Use for finding recent news or information not in historical databases.",
            "EarningsCallSummary(query: str): Retrieve and summarize earnings call transcripts (historical, ~2016-2020) for a given company to understand qualitative performance, strategy, and management commentary. Input must be a natural language query specifying the company and desired information.",
            "DirectAnswer(instruction: str): Use ONLY when no other tools are needed and the LLM can answer directly without external data. For general knowledge questions, writing emails, explaining concepts, etc. Input must be a clear instruction describing what the LLM should respond with.",
            "conversation_handler(query: str): Use to respond to general conversational input (greetings, thanks), provide explanations about capabilities, or handle follow-ups that don't require data tools. Input is the user's conversational text.",
            "clarification_request(question: str): Use to ask the user for clarification when the query is ambiguous or more information is needed to use other tools effectively. Input is the question to ask the user."
        ]
        return "\n".join(tools_desc)
    
    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool by looking up its function in the tools_map and return the observation."""
        logger.info(f"[ReAct] Executing tool: {tool_name} with input: {tool_input[:100]}...")
        
        # Retrieve the tool function from the map
        tool_function = self.tools_map.get(tool_name)
        
        if not tool_function:
            available_tools = ", ".join(self.tools_map.keys())
            logger.warning(f"[ReAct] Unknown tool '{tool_name}'. Available: {available_tools}")
            return f"Observation: Unknown tool '{tool_name}'. Available tools are: {available_tools}"

        try:
            # Call the specific tool function with necessary arguments
            # We need to determine which arguments each tool function requires.
            # Based on internal_agent.py and common patterns:
            if tool_name == "FinancialSQL":
                result = tool_function(query=tool_input, llm=self.llm, db_path=self.db_paths.get("financial"))
            elif tool_name == "CCRSQL":
                result = tool_function(query=tool_input, llm=self.llm, db_path=self.db_paths.get("ccr"))
            elif tool_name == "FinancialNewsSearch":
                result = tool_function(query=tool_input) # Assumes it doesn't need llm, db_path, api_key
            elif tool_name == "EarningsCallSummary":
                 # Handle potential parsing issues if input isn't just the query string
                parsed_input = tool_input # Assume simple string for now
                # Example if tool expects dict: try: parsed_input = json.loads(tool_input) catch...
                result = tool_function(query=parsed_input, llm=self.llm, api_key=self.api_key)
            elif tool_name == "DirectAnswer":
                result = tool_function(query=tool_input) # The original lambda expects 'query'
            elif tool_name == "conversation_handler":
                # This still uses the internal placeholder method
                result = self._handle_conversation(tool_input) 
            elif tool_name == "clarification_request":
                 # This still uses the internal placeholder method
                 return f"Observation: The user would be asked: '{tool_input}'. For this simulation, assume they have not yet responded."
            else:
                 # Should not be reached if tool_function lookup succeeded, but as a safeguard:
                 logger.error(f"[ReAct] Tool '{tool_name}' found in map but not handled in execution logic.")
                 return f"Observation: Tool '{tool_name}' execution logic is not implemented."

            # Ensure result is a string for the observation
            observation_content = str(result)
            logger.info(f"[ReAct] Tool '{tool_name}' executed successfully. Result: {observation_content[:200]}...") # Log success and snippet
            return f"Observation: {observation_content}"

        except Exception as e:
            logger.error(f"[ReAct] Error executing tool '{tool_name}' with input '{tool_input[:100]}...': {e}", exc_info=True)
            return f"Observation: Error executing {tool_name}: {str(e)}"
    
    def _handle_conversation(self, query: str) -> str:
        """Placeholder for handling conversational queries directly through the LLM if needed, 
           or could just return a standard conversational acknowledgement."""
        # Option 1: Simple acknowledgement
        # return f"Acknowledged: {query}" 
        # Option 2: Pass to LLM (might be redundant if DirectAnswer covers this)
        # messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": query}]
        # response = self.llm.invoke(messages)
        # return response.content
        # Option 3: Use DirectAnswer's logic implicitly
        logger.info(f"[ReAct] Handling conversation directly for: {query}")
        # For now, let's just indicate it was handled conversationally.
        # A more sophisticated approach might involve invoking the LLM or using DirectAnswer logic.
        return f"Handled conversationally: '{query}'"

#!/usr/bin/env python3
"""
Phase 3: Basic Agent with Multiple Tools & Confirmation
"""

import os
import sys # Add sys for path append if needed outside main
import logging
import inspect # Needed for argument inspection
import json # Potentially for plan parsing
import re # For plan parsing
from typing import Dict, Any, Callable, List, Tuple # Add types for memory

from dotenv import load_dotenv

# Langchain components
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

# --- Import Tool Functions --- 
sys.path.append(os.path.dirname(os.path.abspath(__file__))) # Ensure tools are importable
from tools.ccr_sql_tool import run_ccr_sql
from tools.financial_sql_tool import run_financial_sql
from tools.financial_news_tool import run_financial_news_search
from tools.earnings_call_tool import run_transcript_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class BasicAgent:
    """Agent implementing Guardrail -> Plan -> Confirm -> Execute -> Synthesize flow."""

    def __init__(self):
        """Initializes the agent, LLM, tools, and DB paths."""
        logger.info("Initializing BasicAgent (Phase 3)...")
        load_dotenv()
        logger.info("Environment variables loaded.")

        try:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")

            # Initialize LLM
            model_name = "claude-3-5-sonnet-20240620" 
            self.llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=self.anthropic_api_key)
            logger.info(f"LLM Initialized: {getattr(self.llm, 'model', model_name)}")
            
            # Define DB Paths
            project_root = os.path.abspath(os.path.dirname(__file__))
            self.db_paths = {
                "financial": os.path.join(project_root, "scripts", "data", "financial_data.db"),
                "ccr": os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
            }
            logger.info(f"DB Paths Initialized: {self.db_paths}")
            # Add DB existence checks if desired
            if not os.path.exists(self.db_paths["financial"]):
                logger.warning(f"Financial DB not found at {self.db_paths['financial']}")
            if not os.path.exists(self.db_paths["ccr"]):
                logger.warning(f"CCR DB not found at {self.db_paths['ccr']}")
            
            # Define available tools for this phase
            self.tools_map: Dict[str, Callable] = {
                "CCRSQL": run_ccr_sql,
                "FinancialSQL": run_financial_sql,
                "FinancialNewsSearch": run_financial_news_search,
                "EarningsCallSummary": run_transcript_agent,
            }
            logger.info(f"Tools map initialized with: {list(self.tools_map.keys())}")
            
            # Add conversation memory
            self.memory: List[Tuple[str, str]] = []  # List of (query, response) tuples
            logger.info("Conversation memory initialized.")
            
            # Initialize thinking steps collection
            self.thinking_steps: List[str] = []
            logger.info("Thinking steps tracking initialized.")

        except Exception as e:
            logger.error(f"Agent Initialization Failed: {e}", exc_info=True)
            raise 

        logger.info("BasicAgent initialized successfully.")

    # --- Agent Methods --- 

    def _add_thinking_step(self, step: str) -> None:
        """Add a simplified thinking step to track agent reasoning."""

    def _format_conversation_history(self, max_turns=3):
        """Format recent conversation history for inclusion in prompts."""
        if not self.memory:
            return ""
            
        # Get last few turns, limited by max_turns
        recent_memory = self.memory[-max_turns:]
        
        formatted_history = "Recent conversation history:\n"
        for i, (user_query, assistant_response) in enumerate(recent_memory):
            # Truncate very long responses
            if len(assistant_response) > 500:
                assistant_response = assistant_response[:500] + "..."
                
            formatted_history += f"User {i+1}: {user_query}\n"
            formatted_history += f"Assistant {i+1}: {assistant_response}\n\n"
            
        return formatted_history
        
        logger.info(f"[Thinking] {step}")
        self.thinking_steps.append(step)

    def _guardrail_check(self, query: str) -> Dict[str, Any]:
        """
        Pre-processes the user query through a guardrail to check for:
        - Safety/appropriateness
        - Query within system's capabilities
        - Content policy compliance
        
        Returns:
            Dict with:
            - "pass": bool indicating if query passes guardrails
            - "query": potentially modified query if needed
            - "message": explanation if query is rejected
        """
        logger.info("[Guardrail] Checking query against guardrails...")
        
        system_prompt = """You are a helpful but cautious AI assistant. Your role is to evaluate incoming user queries for:

1. Safety: No harmful, illegal, unethical or dangerous content
2. Appropriateness: No obscene, offensive or discriminatory content
3. Capabilities: Only financial analysis, data lookup, and business research are within scope
4. Specificity: Ensure the query is clear and specific enough to be processed

For EACH query, FIRST determine if it should be:
- PASSED: The query is safe, appropriate, within scope and specific enough
- MODIFIED: The query needs minor adjustments to be processable (e.g., clarification, rewording)
- REJECTED: The query violates guidelines and should not be processed

THEN respond in the following JSON format ONLY:
{
  "decision": "PASSED|MODIFIED|REJECTED",
  "modified_query": "Only include if decision is MODIFIED, otherwise null",
  "explanation": "Brief explanation of your decision",
  "pass": true|false
}

The "pass" field should be true for both PASSED and MODIFIED decisions, and false for REJECTED.
"""
        
        human_prompt = f"Please evaluate this user query: \"{query}\""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = self.llm.invoke(messages)
            
            # Parse the response
            try:
                result = json.loads(response.content.strip())
                
                # Log the guardrail decision
                if result.get("pass", False):
                    if result.get("decision") == "MODIFIED":
                        modified_query = result.get("modified_query", query)
                        logger.info(f"[Guardrail] Query modified: '{query}' -> '{modified_query}'")
                        return {"pass": True, "query": modified_query, "message": result.get("explanation", "")}
                    else:
                        logger.info(f"[Guardrail] Query passed: '{query}'")
                        return {"pass": True, "query": query, "message": ""}
                else:
                    logger.warning(f"[Guardrail] Query rejected: '{query}', Reason: {result.get('explanation', 'No reason provided')}")
                    return {"pass": False, "query": query, "message": result.get("explanation", "This query cannot be processed.")}
                    
            except json.JSONDecodeError:
                logger.error(f"[Guardrail] Failed to parse guardrail response: {response.content[:100]}...")
                # Fail open - if we can't parse the guardrail response, let the query through
                return {"pass": True, "query": query, "message": ""}
                
        except Exception as e:
            logger.error(f"[Guardrail] Error during guardrail check: {e}", exc_info=True)
            # Fail open
            return {"pass": True, "query": query, "message": ""}
    
    def _generate_plan(self, query: str) -> str:
        """Generates a plan outlining which tool(s) are needed."""
        logger.info("[Planner] Generating plan for multiple tools...")
        
        # --- Define NEW Detailed Tool Descriptions ---
        # Descriptions now include data source, scope, and input hints.
        tool_descriptions = (
            "*   EarningsCallSummary: Finds and analyzes specific company earnings call transcripts (focusing on AAPL, AMD, AMZN, ASML, CSCO, GOOGL, INTC, MSFT, MU, NVDA) for periods roughly 2016-2020 stored in a MongoDB database. Use for qualitative insights: management commentary, strategy discussion, product mentions, Q&A details. Input should specify the company (e.g., 'MSFT') and the desired period (e.g., 'Q1 2017', 'annual 2017'). For comparisons across companies or periods, call this tool separately for each.\n"
            "*   FinancialSQL: Queries a SQL database (`financial_data.db`) containing quantitative financial data (quarterly income statements, balance sheets, daily stock prices, dividends). Use for specific financial figures like revenue, net income, EPS, assets, liabilities, stock price on a specific date, etc. Input is a natural language question about financial data.\n"
            "*   FinancialNewsSearch: Searches the web (currently mocked) for recent financial news articles related to companies, tickers, or market events. Use for latest news, market sentiment analysis, or information about recent events not found in historical databases. Input is a natural language search query.\n"
            "*   CCRSQL: Queries a SQL database (`ccr_reporting.db`) containing customer care reporting (CCR) data. Use only for questions specifically about CCR metrics, reports, or related internal data. Input is a natural language question about CCR data."
        )
        
        # --- Define NEW Planner Prompt --- 
        system_prompt_content = f"""You are an expert financial analysis planning assistant. Your goal is to create an execution plan using the available tools to answer the user's query. Create a sequence of tool calls.

AVAILABLE TOOLS OVERVIEW:
{tool_descriptions}

PLANNING GUIDELINES:
*   Analyze the user query carefully to determine the required information type (qualitative transcript analysis, quantitative financial figures, recent news, CCR data) and the necessary entities (company tickers, time periods).
*   Select the most appropriate tool(s) based on the information type and the data source described above.
*   When the user asks to compare multiple companies or analyze distinct time periods, generate separate, sequential steps using the relevant tools for *each* entity or period. Do not combine comparisons into a single tool input.
*   Ensure tool inputs are specific and contain necessary details as required by the tool (e.g., company ticker, time period for EarningsCallSummary).
*   If a query requires combining information from multiple tools (e.g., financial figures from FinancialSQL and commentary from EarningsCallSummary), create sequential steps for each tool.

EXAMPLES:

Example 1:
User Query: Compare NVIDIA and Microsoft revenue and strategy in 2017.
Generated Plan:
Tool: FinancialSQL
Input: Get NVIDIA revenue for 2017

Tool: FinancialSQL
Input: Get Microsoft revenue for 2017

Tool: EarningsCallSummary
Input: Summarize NVIDIA 2017 annual earnings call strategy

Tool: EarningsCallSummary
Input: Summarize Microsoft 2017 annual earnings call strategy

Example 2:
User Query: What were Apple's results in Q4 2019?
Generated Plan:
Tool: EarningsCallSummary
Input: Summarize Apple's Q4 2019 earnings call results

Tool: FinancialSQL
Input: Get Apple revenue and profit for Q4 2019

Example 3:
User Query: Any recent news about Intel?
Generated Plan:
Tool: FinancialNewsSearch
Input: Recent news about Intel

Example 4:
User Query: Tell me about the CCR reports.
Generated Plan:
Tool: CCRSQL
Input: Describe the available CCR reports

Example 5:
User Query: Hi there!
Generated Plan:
No tool needed

FINAL INSTRUCTIONS:
- For EACH tool needed, respond with exactly two lines: 
  Tool: [Tool Name]
  Input: [Rephrase the user query or extract keywords suitable for the specified tool]
- If multiple tools are needed, list each Tool/Input pair sequentially.
- If no tools are needed (e.g., the query is conversational), respond ONLY with the text:
No tool needed

Respond Now."""
        
        human_prompt_content = f"User Query: \"{query}\""

        try:
            messages = [ 
                SystemMessage(content=system_prompt_content),
                HumanMessage(content=human_prompt_content)
            ]
            response = self.llm.invoke(messages)
            plan_text = response.content.strip()
            logger.info(f"[Planner] Raw plan text:\n{plan_text}")
            
            # Basic validation (check if it contains expected keywords)
            if "Tool:" in plan_text or "No tool needed" in plan_text:
                return plan_text
            else:
                logger.warning(f"[Planner] Plan output did not match expected format: {plan_text}")
                # Consider more sophisticated validation or error reporting if needed
                return "Error: Planner LLM response did not follow expected format."

        except Exception as e:
            logger.error(f"[Planner] Error during plan generation: {e}", exc_info=True)
            return f"Error generating plan: {str(e)}"

    def _execute_plan(self, plan: str) -> Dict[str, Any]:
        """Parses the plan and executes the specified tool steps sequentially."""
        logger.info(f"[Executor] Executing full plan:\n{plan}")
        results = {} # Store results with unique keys
        # Track tool usage counts for unique keys
        tool_usage_counters = {}
        planned_steps = []

        # --- Parse the plan text into steps --- 
        # Assumes format: Tool: [Name]\nInput: [Input] potentially repeated
        lines = plan.strip().split('\n')
        current_tool = None
        current_input_lines = []
        for line in lines:
            line_strip = line.strip()
            tool_match = re.match(r"Tool:\s*(.*)", line_strip)
            input_match = re.match(r"Input:\s*(.*)", line_strip)

            if tool_match:
                # If we were gathering input for a previous tool, store it
                if current_tool and current_input_lines:
                    planned_steps.append({"tool": current_tool, "input": "\n".join(current_input_lines).strip()})
                    current_input_lines = [] # Reset for next input
                current_tool = tool_match.group(1).strip()
            elif input_match and current_tool: # Start gathering input for the current tool
                current_input_lines = [input_match.group(1).strip()]
            elif current_tool and current_input_lines: # Continue gathering multi-line input
                 current_input_lines.append(line) # Append the raw line to preserve formatting
        
        # Add the last step if any
        if current_tool and current_input_lines:
            planned_steps.append({"tool": current_tool, "input": "\n".join(current_input_lines).strip()})
        
        logger.info(f"[Executor] Parsed {len(planned_steps)} steps from plan.")
        if not planned_steps:
            logger.warning("[Executor] No valid steps parsed from plan.")
            self._add_thinking_step("Unable to parse execution steps from plan...")
            return {"error": "No valid execution steps could be parsed from the plan."}

        # --- Execute each step --- 
        print("\nExecuting steps. Press Ctrl+C at any time to interrupt processing.")
        for i, step in enumerate(planned_steps):
            tool_name = step["tool"]
            tool_input = step["input"]
            step_num = i + 1
            logger.info(f"[Executor] Executing Step {step_num}/{len(planned_steps)}: Tool='{tool_name}', Input='{tool_input[:100]}...'")
            
            # Add specific thinking step for each tool execution
            if tool_name == "FinancialSQL":
                self._add_thinking_step(f"Querying financial database: '{tool_input[:50]}...'")
            elif tool_name == "CCRSQL":
                self._add_thinking_step(f"Analyzing credit risk data: '{tool_input[:50]}...'")
            elif tool_name == "FinancialNewsSearch":
                self._add_thinking_step(f"Searching for financial news: '{tool_input[:50]}...'")
            elif tool_name == "EarningsCallSummary":
                self._add_thinking_step(f"Analyzing earnings call transcripts: '{tool_input[:50]}...'")
            else:
                self._add_thinking_step(f"Executing {tool_name}: '{tool_input[:50]}...'")
            
            tool_function = self.tools_map.get(tool_name)
            if not tool_function:
                logger.warning(f"[Executor] Step {step_num}: Unknown tool '{tool_name}' found in plan.")
                self._add_thinking_step(f"Error: Unknown tool '{tool_name}' specified in plan...")
                results[f"Error_Step{step_num}_{tool_name}"] = f"Unknown tool '{tool_name}' specified in plan step {step_num}."
                continue # Skip to next step

            try:
                # Prepare arguments using introspection
                kwargs = {"query": tool_input} # Default
                # Adjust primary input key if needed (e.g., DirectAnswer)
                # if tool_name == "DirectAnswer": kwargs = {"instruction": tool_input}

                sig = inspect.signature(tool_function)
                tool_params = sig.parameters
                
                if "llm" in tool_params: kwargs["llm"] = self.llm
                if "db_path" in tool_params:
                    db_key = "ccr" # Default assumption
                    if tool_name == "FinancialSQL": db_key = "financial"
                    kwargs["db_path"] = self.db_paths.get(db_key)
                
                # For emergency stop
                try:
                    logger.info(f"[Executor] Step {step_num}: Calling tool '{tool_name}' with input: '{tool_input[:100]}...'")
                    # Actually execute the tool function with appropriate kwargs
                    tool_result = tool_function(**kwargs)
                    logger.info(f"[Executor] Step {step_num}: Tool '{tool_name}' executed successfully.")
                    
                    # Add result thinking step
                    if isinstance(tool_result, dict):
                        if tool_result.get("error"):
                            self._add_thinking_step(f"Tool execution failed: {tool_result.get('error')[:50]}...")
                        elif "sql_result" in tool_result:
                            result_preview = str(tool_result["sql_result"])[:30].replace("\n", " ")
                            self._add_thinking_step(f"Database returned results: '{result_preview}...'")
                        else:
                            self._add_thinking_step(f"Tool execution completed successfully...")
                    else:
                        self._add_thinking_step(f"Tool returned result: '{str(tool_result)[:30]}...'")
                    
                    # Create a unique key for this tool call
                    if tool_name not in tool_usage_counters:
                        tool_usage_counters[tool_name] = 1
                    else:
                        tool_usage_counters[tool_name] += 1
                    unique_key = f"{tool_name}_{tool_usage_counters[tool_name]}"
                    
                    # Store with unique key
                    results[unique_key] = tool_result
                    
                except KeyboardInterrupt:
                    logger.warning(f"[Executor] Step {step_num}: Tool execution interrupted by user.")
                    self._add_thinking_step("Tool execution interrupted by user...")
                    results[f"Error_Step{step_num}_{tool_name}"] = "Tool execution interrupted by user."
                    break # Exit the loop early
                    
            except Exception as e:
                logger.error(f"[Executor] Step {step_num}: Error executing tool '{tool_name}': {e}", exc_info=True)
                self._add_thinking_step(f"Error during tool execution: {str(e)[:50]}...")
                results[f"Error_Step{step_num}_{tool_name}"] = f"Error executing tool: {str(e)}"
                continue # Try to continue with other steps
        
        logger.info(f"[Executor] Plan execution completed with {len(results)} results.")
        return results

    def _format_sql_results(self, results_str: str, max_rows=10) -> str:
        """Format SQL results in a more readable way.
        
        Args:
            results_str: String representation of SQL results, typically in the form "[('val1', val2), ...]"
            max_rows: Maximum number of rows to include in formatted output
            
        Returns:
            Formatted string representation of the results
        """
        if not results_str or not isinstance(results_str, str):
            return "No results found."
            
        try:
            # Parse the results string (assuming it's like "[('col1', val1), ('col2', val2)]")
            data = eval(results_str)
            
            if not data:
                return "Query executed successfully but returned no data."
                
            # Handle empty result set
            if isinstance(data, list) and len(data) == 0:
                return "Query returned an empty result set."
                
            # Count rows and apply limit if needed
            row_count = len(data)
            if row_count > max_rows:
                formatted = f"Showing first {max_rows} of {row_count} rows:\n"
                data = data[:max_rows]
            else:
                formatted = f"Results ({row_count} rows):\n"
                
            # Format as a simple table
            if isinstance(data, list) and all(isinstance(row, tuple) for row in data):
                # For single row with a single value (scalar result)
                if len(data) == 1 and len(data[0]) == 1:
                    value = data[0][0]
                    return f"Result: {value}"
                    
                # For multiple rows or columns
                for i, row in enumerate(data):
                    row_formatted = ", ".join([str(col) for col in row])
                    formatted += f"Row {i+1}: {row_formatted}\n"
                    
            else:
                # Fallback for unexpected formats
                formatted += str(data)
                
            return formatted.strip()
            
        except Exception as e:
            logger.warning(f"Error formatting SQL results: {e}")
            return results_str  # Return original if parsing fails

    def _synthesize_answer(self, query: str, execution_results: Dict[str, Any]) -> str:
        """Generates a final answer based on the query and execution results."""
        logger.info("[Synthesizer] Synthesizing final answer...")

        # Format the results for the prompt
        result_context = ""
        if not execution_results:
             result_context = "No tool was executed or planned."
        elif "error" in execution_results and len(execution_results) == 1: # Check if the only key is 'error'
             result_context = f"Error during plan parsing or initial execution: {execution_results['error']}"
        else:
            formatted_results = []
            for tool_name, result_data in execution_results.items():
                # Extract base tool name (removing the unique identifier)
                base_tool_name = tool_name.split("_")[0] if "_" in tool_name and not tool_name.startswith("Error_Step") else tool_name
                if tool_name.startswith("Error_Step"):
                    formatted_results.append(f"Error during step {tool_name}: {result_data}")
                elif isinstance(result_data, dict):
                    # Nicely format known dict structures (like SQL)
                    if "sql_query" in result_data:
                        sql_result = result_data.get('sql_result', 'N/A')
                        # Use the new formatter for SQL results if available
                        if sql_result != 'N/A':
                            formatted_sql_result = self._format_sql_results(sql_result)
                        else:
                            formatted_sql_result = sql_result
                            
                        formatted_results.append(f"Tool: {base_tool_name}\\nSQL Query: {result_data.get('sql_query', 'N/A')}\\nResult: {formatted_sql_result}\\nError: {result_data.get('error', 'None')}")
                    elif "error" in result_data: # Tool execution error
                        formatted_results.append(f"Tool: {base_tool_name}\\nError: {result_data['error']}")
                    else: # Generic dict
                        formatted_results.append(f"Tool: {base_tool_name}\\nResult: {json.dumps(result_data, indent=2)}")
                else: # Other data types
                    formatted_results.append(f"Tool: {base_tool_name}\\nResult: {str(result_data)}")
            result_context = "\\n\\n".join(formatted_results)

        logger.debug(f"[Synthesizer] Context for synthesis prompt:\\n{result_context}")

        system_prompt_content = """You are an assistant that synthesizes answers based *only* on the provided context from tool executions. Do not add external knowledge or information not present in the results. Combine information from multiple tool results if necessary to provide a comprehensive answer. If the results indicate errors, are empty, or don't seem relevant to the query, state that clearly. If conversation history is provided, use it for context while staying focused on the current query."""

        # Add conversation history to the prompt if available
        conversation_context = self._format_conversation_history()
        if conversation_context:
            system_prompt_content = system_prompt_content + "\n\n" + conversation_context

        # Add conversation history to the prompt if available
        conversation_context = self._format_conversation_history()
        if conversation_context:
            system_prompt_content = system_prompt_content + "\n\n" + conversation_context
        
        human_prompt_content = f"""Original User Query: "{query}"

Tool Execution Results Context:
--- START CONTEXT ---
{result_context}
--- END CONTEXT ---

Based *only* on the provided Tool Execution Results Context, formulate a concise and accurate answer to the Original User Query."""

        try:
            messages = [ 
                SystemMessage(content=system_prompt_content),
                HumanMessage(content=human_prompt_content) 
            ]
            response = self.llm.invoke(messages)
            final_answer = response.content.strip()
            logger.info(f"[Synthesizer] Synthesized answer: {final_answer[:500]}...")
            return final_answer
        except Exception as e:
            logger.error(f"[Synthesizer] Error during answer synthesis: {e}", exc_info=True)
            return f"Error synthesizing answer: {str(e)}"

    def run(self, query: str) -> str:
        """Runs the Guardrail -> Plan -> [Confirm] -> Execute -> Synthesize flow."""
        logger.info(f'--- Running query: "{query}" ---')
        
        # Clear previous thinking steps
        self.thinking_steps = []
        
        # --- 0. Guardrail Check ---
        logger.info("--- Step 0: Guardrail Check ---")
        self._add_thinking_step("Validating query against safety and capability guardrails...")
        guardrail_result = self._guardrail_check(query)
        
        if not guardrail_result["pass"]:
            # Query rejected by guardrail
            logger.info(f"Query rejected by guardrail: {guardrail_result['message']}")
            self._add_thinking_step(f"Query rejected: {guardrail_result['message'][:50]}...")
            
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\nI'm unable to process this query: {guardrail_result['message']}"
        
        # Update query if it was modified by the guardrail
        if guardrail_result["query"] != query:
            logger.info(f"Query modified by guardrail: '{query}' -> '{guardrail_result['query']}'")
            self._add_thinking_step(f"Clarifying query to: '{guardrail_result['query']}'")
            query = guardrail_result["query"]
        
        # --- Check for follow-up questions ---
        contextual_query = query
        is_followup = False
        followup_indicators = ["what about", "tell me more", "and what", "how about", "what is", "can you explain"]
        
        if self.memory and any(query.lower().startswith(indicator) for indicator in followup_indicators):
            # It's likely a follow-up question, add context from the most recent interaction
            prev_query, prev_response = self.memory[-1]
            contextual_query = f"{query} (Context from previous query: '{prev_query}')"
            logger.info(f"Follow-up detected. Enhanced query: {contextual_query}")
            self._add_thinking_step(f"Recognizing follow-up question related to previous query...")
            is_followup = True
        
        # --- 1. Generate Plan --- 
        logger.info("--- Step 1: Generating Plan ---")
        self._add_thinking_step("Planning which tools are needed to answer your question...")
        plan = self._generate_plan(contextual_query)
        logger.info(f"Generated Plan:\n{plan}")
        
        if plan.startswith("Error:"):
            self._add_thinking_step("Error occurred during planning phase...")
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\nPlanning failed: {plan}"

        # --- Handle "No tool needed" case ---
        if "No tool needed" in plan:
            logger.info("Plan indicates no tool needed. Attempting direct LLM response.")
            self._add_thinking_step("No specialized tools needed, answering from general knowledge...")
            try:
                 # Add context from memory for direct LLM response
                 system_content = "You are a helpful assistant answering based on general knowledge as no specific tools were deemed necessary."
                 
                 # Add memory context if available
                 if self.memory:
                     memory_context = "\n".join([f"Previous query: {q}\nYour response: {r}\n" 
                                               for q, r in self.memory[-3:]])  # Use last 3 interactions
                     system_content += f"\n\nRecent conversation history:\n{memory_context}"
                 
                 direct_messages = [
                     SystemMessage(content=system_content),
                     HumanMessage(content=query),
                 ]
                 response = self.llm.invoke(direct_messages)
                 final_answer = response.content.strip()
                 logger.info(f"Direct LLM Response: {final_answer[:500]}...")
                 self._add_thinking_step("Synthesizing answer from general knowledge...")
                 
                 # Store in memory
                 self.memory.append((query, final_answer))
                 if len(self.memory) > 5:  # Keep only the 5 most recent interactions
                     self.memory.pop(0)
                     
                 # Format thinking steps
                 thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
                 return f"{thinking_output}\n\n{final_answer}"
            except Exception as e:
                logger.error(f"Error during direct LLM invocation: {e}", exc_info=True)
                self._add_thinking_step("Error occurred while generating direct response...")
                # Format thinking steps
                thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
                return f"{thinking_output}\n\nSorry, an error occurred while trying to answer directly: {str(e)}"

        # --- Add thinking steps based on which tools are in the plan ---
        # Parse the plan to identify tools that will be used
        if "FinancialSQL" in plan:
            self._add_thinking_step("Preparing to search financial database for relevant data...")
        if "CCRSQL" in plan:
            self._add_thinking_step("Preparing to query counterparty credit risk database...")
        if "FinancialNewsSearch" in plan:
            self._add_thinking_step("Planning to search for recent financial news and market information...")
        if "EarningsCallSummary" in plan:
            self._add_thinking_step("Will analyze earnings call transcripts for relevant insights...")

        # --- 2. Confirm Plan (User Input) - IMPROVED UX ---
        logger.info("--- Step 2: Confirming Plan ---")
        self._add_thinking_step("Awaiting confirmation of proposed execution plan...")
        print(f"\nProposed Plan:\n{plan}")
        confirmation = input("Proceed with this plan? [Y/n]: ").strip().lower()
        
        # Default to yes if user just presses Enter or types y/yes
        if confirmation == "" or confirmation.startswith('y'):
            logger.info("Plan confirmed by user.")
            self._add_thinking_step("Plan confirmed, proceeding with execution...")
        else:
            logger.info("Plan rejected by user.")
            self._add_thinking_step("Plan rejected by user, halting execution...")
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\nPlan execution cancelled by user."

        # --- 3. Execute Plan --- 
        logger.info(f"--- Step 3: Executing Confirmed Plan ---")
        self._add_thinking_step("Executing tools according to plan...")
        try:
            # Pass the raw plan text directly to _execute_plan
            execution_results = self._execute_plan(plan) 
            logger.info(f"Execution Results: {str(execution_results)[:500]}...")
            
            # Add thinking steps about results
            for tool_name, result in execution_results.items():
                if tool_name.startswith("Error"):
                    self._add_thinking_step(f"Error occurred during {tool_name} execution...")
                elif tool_name == "FinancialSQL":
                    self._add_thinking_step("Retrieved financial data from database...")
                elif tool_name == "CCRSQL":
                    self._add_thinking_step("Retrieved credit risk exposure data...")
                elif tool_name == "FinancialNewsSearch":
                    self._add_thinking_step("Found relevant financial news articles...")
                elif tool_name == "EarningsCallSummary":
                    self._add_thinking_step("Extracted insights from earnings call transcripts...")
        except Exception as e:
            logger.error(f"Error during plan execution orchestration: {e}", exc_info=True)
            self._add_thinking_step("Unexpected error occurred during tool execution...")
            # Synthesize based on the error
            execution_results = {"error": f"An unexpected error occurred during plan execution: {str(e)}"}

        # --- 4. Synthesize Answer --- 
        logger.info("--- Step 4: Synthesizing Answer ---")
        self._add_thinking_step("Synthesizing comprehensive answer from all gathered information...")
        try:
            # Pass the dictionary of results
            final_answer = self._synthesize_answer(query, execution_results) 
            logger.info(f"--- Final Answer ---:\n{final_answer}")
            
            # Store in memory
            self.memory.append((query, final_answer))
            if len(self.memory) > 5:  # Keep only the 5 most recent interactions
                self.memory.pop(0)
            
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\n{final_answer}"
        except Exception as e:
            logger.error(f"Error during answer synthesis orchestration: {e}", exc_info=True)
            self._add_thinking_step("Error occurred during answer synthesis...")
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\nSorry, an error occurred while synthesizing the final answer: {str(e)}"

# Example of direct usage (optional)
if __name__ == '__main__':
    try:
        agent = BasicAgent()
        # Test 1: Single Tool (CCR)
        # test_query = "What is the total exposure to JP Morgan?"
        # Test 2: General Knowledge / No Tool
        # test_query = "What is the capital of France?"
        # Test 3: Multi-Tool (Financial SQL + News)
        test_query = "What was Apple's revenue in 2020 and what is their latest stock price?"
        
        print(f"\n--- Testing query: {test_query} ---")
        response = agent.run(test_query)
        print(f"\n--- Agent Response ---\n{response}")
        
    except Exception as main_e:
        print(f"An error occurred during the agent run: {main_e}")
        logger.error("Error in main execution block", exc_info=True) 
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
import time
import textwrap

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
from tools.control_analysis_tool import run_control_analyzer_agent
from tools.sec_filings_tool import run_sec_filings_analysis

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
                "ControlAnalysis": run_control_analyzer_agent,
                "SECFilingsAnalysis": run_sec_filings_analysis,
            }
            logger.info(f"Tools map initialized with: {list(self.tools_map.keys())}")
            
            # Add conversation memory
            self.memory: List[Tuple[str, str]] = []  # List of (query, response) tuples
            logger.info("Conversation memory initialized.")
            
            # Initialize thinking steps collection
            self.thinking_steps: List[str] = []
            logger.info("Thinking steps tracking initialized.")

            # Initialize persona
            self._initialize_persona()
            logger.info("Persona initialized successfully.")

        except Exception as e:
            logger.error(f"Agent Initialization Failed: {e}", exc_info=True)
            raise 

        logger.info("BasicAgent initialized successfully.")

    def _initialize_persona(self) -> None:
        """Initialize the agent's persona using the persona prompt and display greeting."""
        try:
            # Load persona prompt
            prompt_dir = os.path.join(os.path.dirname(__file__), 'prompts')
            persona_file = os.path.join(prompt_dir, 'persona_init.txt')
            
            if not os.path.exists(persona_file):
                logger.error(f"Persona file not found at {persona_file}")
                raise FileNotFoundError(f"Persona file not found at {persona_file}")
            
            with open(persona_file, 'r') as f:
                persona_prompt = f.read()
            
            # Initialize with persona and generate greeting
            system_prompt = f"""You are the BMO Enterprise Risk Assistant. Using the following persona definition, create a professional and welcoming greeting for the user. The greeting should:

1. Introduce yourself as the BMO Enterprise Risk Assistant
2. Acknowledge your audience (BMO Enterprise Risk employees)
3. Provide a clear, structured overview of your capabilities, including:
   - Available tools and their purposes
   - Data sources and their scope
   - Types of analysis you can perform
4. End with a brief instruction on how to begin (i.e., "Please feel free to ask questions about...")

Format the response in a clean, professional way using markdown for structure.
Keep the tone professional but approachable.

PERSONA DEFINITION:
{persona_prompt}"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content="Generate a professional greeting and capabilities introduction.")
            ]
            
            response = self.llm.invoke(messages)
            greeting = response.content.strip()
            
            logger.info("Persona initialized with capabilities and limitations")
            self._add_thinking_step("Initialized as BMO Enterprise Risk Assistant with verified capabilities")
            
            # Store initialization in memory
            self.memory.append(("INITIALIZATION", greeting))
            
            # Display the greeting
            print("\n=== BMO Enterprise Risk Assistant ===\n")
            print(greeting)
            print("\n=====================================\n")
            
        except Exception as e:
            logger.error(f"Failed to initialize persona: {e}", exc_info=True)
            raise

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

IMPORTANT: If the query contains context from previous conversations (indicated by "Context:" or similar markers), treat it as a follow-up question and be more lenient with specificity requirements. Use the provided context to understand the full meaning of the query.

For EACH query, FIRST determine if it should be:
- PASSED: The query is safe, appropriate, within scope and specific enough (or has sufficient context)
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

Remember:
- Follow-up questions with context should generally pass if they're safe and appropriate
- Use the context to evaluate specificity rather than rejecting unclear follow-ups
- Only reject if there are safety/appropriateness concerns or if the query is completely outside scope"""
        
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
            "*   CCRSQL: Queries a SQL database (`ccr_reporting.db`) containing customer care reporting (CCR) data. Use only for questions specifically about CCR metrics, reports, or related internal data. Input is a natural language question about CCR data.\n"
            "*   ControlAnalysis: Analyzes operational controls in a banking/financial context using the 5Ws framework (Who, What, When, Where, Why), identifies control design gaps, and generates test scripts. Use for analyzing control descriptions, suggesting improvements, or creating test procedures. Input is a control description or a specific analysis request.\n"
            "*   SECFilingsAnalysis: Analyzes SEC filings (10-K reports, MD&A) for Microsoft, MicroStrategy, and Bank of Montreal stored locally. Use for extracting specific information, financial data, risk factors, and business insights from official company filings. Input is a question about a specific company's SEC filing, and should include the company name (e.g., 'Microsoft', 'MicroStrategy', 'BMO')."
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
        
        results = {}
        steps = plan.split('\n')
        total_steps = len([s for s in steps if s.strip()])
        
        print("\nExecution Progress:")
        print("------------------")
        
        for step_num, step in enumerate(steps, 1):
            if not step.strip():
                continue
            
            print(f"\nStep {step_num}/{total_steps}: {step}")
            print("Status: Starting...")
            
            try:
                # Parse tool name and parameters
                tool_match = re.search(r'(\w+)\((.*)\)', step)
                if not tool_match:
                    logger.warning(f"[Executor] Step {step_num}: Could not parse tool call from: {step}")
                    self._add_thinking_step(f"Could not understand tool call in step {step_num}")
                    results[f"Error_Step{step_num}"] = "Invalid tool call format"
                    print("Status: Failed - Invalid tool format")
                    
                    # Ask user what to do
                    action = input("\nHow would you like to proceed?\n1. Skip this step\n2. Retry with modified command\n3. Abort execution\nYour choice: ")
                    if action == "1":
                        continue
                    elif action == "2":
                        modified_step = input("Enter modified command: ")
                        tool_match = re.search(r'(\w+)\((.*)\)', modified_step)
                        if not tool_match:
                            print("Still invalid format. Skipping step.")
                            continue
                    else:
                        print("Aborting execution.")
                        return results
                    
                tool_name = tool_match.group(1)
                tool_args_str = tool_match.group(2)
                
                # Validate tool exists
                if tool_name not in self.tools_map:
                    logger.warning(f"[Executor] Step {step_num}: Unknown tool: {tool_name}")
                    self._add_thinking_step(f"Unknown tool '{tool_name}' in step {step_num}")
                    results[f"Error_Step{step_num}"] = f"Unknown tool: {tool_name}"
                    print(f"Status: Failed - Unknown tool '{tool_name}'")
                    continue
                
                print(f"Status: Executing {tool_name}...")
                
                try:
                    # Parse arguments
                    tool_args = eval(f"dict({tool_args_str})")
                    
                    # Execute tool
                    start_time = time.time()
                    result = self.tools_map[tool_name](**tool_args)
                    execution_time = time.time() - start_time
                    
                    # Store result
                    results[f"Step{step_num}_{tool_name}"] = result
                    self._add_thinking_step(f"Completed {tool_name} in step {step_num}")
                    
                    # Show intermediate result
                    print(f"Status: Completed in {execution_time:.2f}s")
                    print("\nIntermediate Result:")
                    print("-----------------")
                    if isinstance(result, str):
                        print(textwrap.shorten(result, width=100))
                    else:
                        print(f"Result type: {type(result)}")
                    print("-----------------")
                    
                    # Ask if user wants to see full result
                    if input("\nWould you like to see the full result? (y/n): ").lower().startswith('y'):
                        print("\nFull Result:")
                        print(result)
                    
                except KeyboardInterrupt:
                    logger.warning(f"[Executor] Step {step_num}: Tool execution interrupted by user.")
                    self._add_thinking_step("Tool execution interrupted by user...")
                    results[f"Error_Step{step_num}_{tool_name}"] = "Tool execution interrupted by user."
                    print("\nStatus: Interrupted by user")
                    
                    # Ask user what to do
                    action = input("\nHow would you like to proceed?\n1. Skip to next step\n2. Retry this step\n3. Abort execution\nYour choice: ")
                    if action == "1":
                        continue
                    elif action == "2":
                        step_num -= 1  # Retry current step
                        continue
                    else:
                        print("Aborting execution.")
                        break
                    
            except Exception as e:
                logger.error(f"[Executor] Step {step_num}: Error executing tool '{tool_name}': {e}", exc_info=True)
                self._add_thinking_step(f"Error during tool execution: {str(e)[:50]}...")
                results[f"Error_Step{step_num}_{tool_name}"] = f"Error executing tool: {str(e)}"
                print(f"\nStatus: Failed - {str(e)}")
                
                # Ask user what to do
                action = input("\nHow would you like to proceed?\n1. Skip to next step\n2. Retry this step\n3. Abort execution\nYour choice: ")
                if action == "1":
                    continue
                elif action == "2":
                    step_num -= 1  # Retry current step
                    continue
                else:
                    print("Aborting execution.")
                    break
        
        print("\nExecution completed!")
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

    def _detect_followup_llm(self, query: str) -> Tuple[bool, str]:
        """Use LLM to detect if a query is a follow-up question and enhance it with context if needed."""
        if not self.memory:
            return False, query

        # Get recent conversation history
        recent_context = self.memory[-2:] if len(self.memory) > 1 else self.memory[-1:]
        context_str = "\n".join([f"Previous Query: {q}\nResponse: {r}\n" for q, r in recent_context])

        system_prompt = """You are an expert at analyzing conversation context and detecting follow-up questions.
Your task is to:
1. Determine if the current query is a follow-up to previous conversation
2. If it is a follow-up, enhance it with necessary context
3. If it's not a follow-up, leave it unchanged

A query is a follow-up if it:
- References information from previous messages
- Uses pronouns (it, they, that, etc.) that refer to previous content
- Asks for clarification or more details about previous topics
- Compares with or builds upon previous information
- Would be unclear without the context of previous messages

Respond in JSON format:
{
    "is_followup": true/false,
    "enhanced_query": "original or enhanced query with context",
    "explanation": "brief explanation of why this is or isn't a follow-up"
}"""

        human_prompt = f"""Current Query: "{query}"

Recent Conversation Context:
{context_str}

Determine if this is a follow-up question and enhance it with context if needed."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            response = self.llm.invoke(messages)
            result = json.loads(response.content.strip())

            is_followup = result.get("is_followup", False)
            enhanced_query = result.get("enhanced_query", query)
            explanation = result.get("explanation", "")

            if is_followup:
                logger.info(f"[Follow-up Detector] Follow-up detected: {explanation}")
                self._add_thinking_step(f"Detected follow-up question: {explanation[:100]}...")
            
            return is_followup, enhanced_query

        except Exception as e:
            logger.error(f"[Follow-up Detector] Error during LLM follow-up detection: {e}", exc_info=True)
            return False, query

    def run(self, query: str) -> str:
        """Runs the Guardrail -> Plan -> [Confirm] -> Execute -> Synthesize flow."""
        logger.info(f'--- Running query: "{query}" ---')
        
        # Clear previous thinking steps
        self.thinking_steps = []
        
        # --- Check for follow-up questions using LLM ---
        is_followup, contextual_query = self._detect_followup_llm(query)
        
        # --- 0. Guardrail Check ---
        logger.info("--- Step 0: Guardrail Check ---")
        self._add_thinking_step("Validating query against safety and capability guardrails...")
        guardrail_result = self._guardrail_check(contextual_query if is_followup else query)
        
        if not guardrail_result["pass"]:
            # Query rejected by guardrail
            logger.info(f"Query rejected by guardrail: {guardrail_result['message']}")
            self._add_thinking_step(f"Query rejected: {guardrail_result['message'][:50]}...")
            
            # Format thinking steps
            thinking_output = "Thinking...\n" + "\n".join([f"- {step}" for step in self.thinking_steps])
            return f"{thinking_output}\n\nI'm unable to process this query: {guardrail_result['message']}"
        
        # Update query if it was modified by the guardrail
        if guardrail_result["query"] != (contextual_query if is_followup else query):
            logger.info(f"Query modified by guardrail: '{query}' -> '{guardrail_result['query']}'")
            self._add_thinking_step(f"Clarifying query to: '{guardrail_result['query']}'")
            query = guardrail_result["query"]
        
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
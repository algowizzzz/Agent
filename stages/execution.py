# Logic for the Execution stage (tool handling/manual execution)
import logging
import re
from typing import List, Dict, Callable, Any, Tuple

# Need PromptTemplate for the LLM step formatter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

# Keep regex only for parsing the LLM's formatted output
FORMATTER_OUTPUT_REGEX = re.compile(r"^([a-zA-Z0-9_]+):\s*(.*)$")

def execute_plan(plan_text: str, tools_map: Dict[str, Callable], llm: Any, db_paths: Dict[str, str], api_key: str) -> Tuple[str, bool]:
    """
    Executes a plan step-by-step by using LLM to parse each step and identify the intended tool and input,
    then invoking the corresponding tool function.

    Args:
        plan_text: The approved plan string with numbered steps.
        tools_map: A dictionary mapping tool names to their callable functions.
        llm: The language model instance (used for parsing steps and for tool execution).
        db_paths: Dictionary containing paths for databases (e.g., {"financial": "path/to/fin.db"}).
        api_key: API key (needed for various tools).

    Returns:
        A tuple: (formatted_results_string, success_flag)
        - formatted_results_string: A string summarizing results/errors of each step.
        - success_flag: True if all steps completed without critical errors, False otherwise.
    """
    logger.info("[Execution] Starting plan execution...")
    results_summary = []
    overall_success = True
    
    # Use lowercase keys for case-insensitive matching
    tools_map_lower = {k.lower(): v for k, v in tools_map.items()}
    
    # Set up the LLM formatter chain
    formatter_template = (
        "You are a step processor that identifies the tool and input from a plan step.\n"
        "Given step: '''{step_description}'''\n"
        "Available tools: {tool_names}\n\n"
        "Extract EXACTLY ONE tool and its input, structured as 'ToolName: Input for the tool'\n"
        "RESPOND WITH ONLY THIS FORMAT, no explanations or other text. Just 'ToolName: Input'.\n"
        "The ToolName MUST be one of the available tools listed above."
    )
    formatter_prompt = PromptTemplate.from_template(formatter_template)
    output_parser = StrOutputParser()
    formatter_chain = formatter_prompt | llm | output_parser

    # Parse the plan into individual steps - correctly split on actual newlines
    # The issue was using '\\n' (literal backslash + n) instead of '\n' (actual newline)
    steps = []
    for line in plan_text.strip().split('\n'):
        line = line.strip()
        if line and line[0].isdigit():  # Only keep lines that start with a digit (step numbers)
            steps.append(line)
    
    logger.info(f"[Execution] Parsed {len(steps)} steps from plan: {steps}")
    
    step_num = 1
    for step_desc in steps:
        if not step_desc:
            continue
        
        logger.info(f"[Execution] Processing Step {step_num}: {step_desc}")
        step_result_str = f"Step {step_num} ({step_desc[:50]}...): "
        step_success = False
        tool_name = None
        tool_input = None
        tool_func = None

        try:
            # --- Use LLM to identify Tool and Input ---
            valid_tool_names = list(tools_map.keys())
            
            try:
                # Process the step with LLM
                formatted_step = formatter_chain.invoke({
                    "step_description": step_desc,
                    "tool_names": valid_tool_names
                })
                logger.info(f"[Execution] LLM formatted step: '{formatted_step}'")
                
                # Extract the tool name and input from LLM response
                match = FORMATTER_OUTPUT_REGEX.match(formatted_step.strip())
                if match:
                    tool_name = match.group(1).strip()
                    tool_input = match.group(2).strip()
                    
                    # Lookup the tool function (case-insensitive)
                    tool_func = tools_map_lower.get(tool_name.lower())
                    if not tool_func:
                        logger.warning(f"[Execution] LLM identified tool '{tool_name}' but it's not registered. Skipping.")
                        step_result_str += f"Skipped (Unregistered tool '{tool_name}')"
                        # step_success remains False
                    else:
                        logger.info(f"[Execution] Successfully identified tool '{tool_name}' with input: '{tool_input[:50]}...'")
                        
                        # --- Execute Tool ---
                        logger.info(f"[Execution] Calling tool: {tool_name} with input: {tool_input[:100]}...")
                        
                        # Pass necessary args based on tool signature
                        if tool_name in ["FinancialSQL", "CCRSQL"]:
                            db_key = "financial" if tool_name == "FinancialSQL" else "ccr"
                            result = tool_func(query=tool_input, llm=llm, db_path=db_paths[db_key])
                            # Result is expected dict {"sql_query": ..., "sql_result": ..., "error": ...}
                            if result.get("error"):
                                step_result_str += f"ERROR: {result['error']}"
                                step_success = False
                            else:
                                step_result_str += f"OK. SQL: `{result.get('sql_query','N/A')}` Result: {str(result.get('sql_result', 'No result'))[:500]}"
                                step_success = True
                        elif tool_name == "FinancialNewsSearch":
                            result = tool_func(query=tool_input) # Assumes this tool only needs query
                            if isinstance(result, str) and result.startswith("Error:"):
                                step_result_str += result # Result is error string
                                step_success = False
                            else:
                                # Handle potential list/dict results gracefully for summary
                                result_str = str(result) 
                                step_result_str += f"OK. Result: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"
                                step_success = True
                        elif tool_name == "EarningsCallSummary":
                            # Assuming this tool needs query, llm, api_key
                            result = tool_func(query=tool_input, llm=llm, api_key=api_key)
                            if isinstance(result, str) and result.startswith("Error:"):
                                step_result_str += result # Result is error string
                                step_success = False
                            else:
                                result_str = str(result) 
                                step_result_str += f"OK. Result: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"
                                step_success = True
                        elif tool_name == "DirectAnswer":
                            # This is our special bypassing tool - just return the input as the result
                            # The actual response content will be generated in the reasoning/final stages
                            result = tool_func(query=tool_input)  # Will return "DIRECT_RESPONSE_REQUESTED: {query}"
                            step_result_str += "OK. Direct LLM response requested."
                            step_success = True
                        else:
                            # Fallback for any other registered tool (assuming it takes 'query')
                            try:
                                logger.warning(f"Using default signature for unknown tool '{tool_name}'")
                                result = tool_func(query=tool_input)
                                result_str = str(result) 
                                step_result_str += f"OK (Default Exec). Result: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"
                                step_success = True
                            except Exception as tool_err:
                                logger.error(f"Error executing tool '{tool_name}': {tool_err}", exc_info=True)
                                step_result_str += f"ERROR executing tool '{tool_name}': {tool_err}"
                                step_success = False
                else:
                    logger.error(f"[Execution] LLM output doesn't match expected format: '{formatted_step}'")
                    step_result_str += "ERROR: LLM output unstructured (doesn't match 'ToolName: Input')"
            
            except Exception as format_err:
                logger.error(f"[Execution] Error processing step with LLM: {format_err}", exc_info=True)
                step_result_str += f"ERROR: LLM processing failed - {type(format_err).__name__}: {format_err}"
                    
        except Exception as e:
            logger.error(f"[Execution] Unexpected error executing step {step_num}: {e}", exc_info=True)
            step_result_str += f"ERROR: Unexpected execution error - {type(e).__name__}: {e}"

        # Update result summary and flow control
        results_summary.append(step_result_str)
        if not step_success:
            overall_success = False
            logger.error(f"[Execution] Step {step_num} failed. Stopping execution.")
            # Stop on first failure - could be changed to continue for partial results
            break
        
        step_num += 1

    formatted_results = "\\n".join(results_summary)
    logger.info("[Execution] Plan execution finished.")
    return formatted_results, overall_success 
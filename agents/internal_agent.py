# Orchestration logic for the internal agent will go here. 
import logging
import os
from typing import Tuple, List, Dict, Callable, Any
import re

# Langchain components
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import BasePromptTemplate, PromptTemplate
from langchain.agents import Tool
from langchain_anthropic import ChatAnthropic

# Project stages and tools
from stages import greeting, guardrails, planning, execution, reasoning, final_output
from tools import financial_sql_tool, ccr_sql_tool, financial_news_tool, earnings_call_tool

# Utility for loading prompts
# from langchain.prompts import load_prompt # Removed - will load manually

logger = logging.getLogger(__name__)

MAX_REPLAN_ATTEMPTS = 2 # Set a limit for re-planning

# --- Tool Registration --- 
def register_tools(llm: BaseChatModel, db_paths: Dict[str, str], api_key: str) -> Tuple[List[Tool], Dict[str, Callable]]:
    """Initializes and registers all available tools."""
    # Map tool names to their core execution functions
    # The functions expect specific arguments (llm, db_path, api_key etc.)
    tool_functions_map = {
        "FinancialSQL": lambda query, llm=None, db_path=None: financial_sql_tool.run_financial_sql(query, llm, db_path or db_paths["financial"]),
        "CCRSQL": lambda query, llm=None, db_path=None: ccr_sql_tool.run_ccr_sql(query, llm, db_path or db_paths["ccr"]),
        "FinancialNewsSearch": lambda query, **kwargs: financial_news_tool.run_financial_news_search(query),
        "EarningsCallSummary": lambda query, llm=None, api_key=None, **kwargs: earnings_call_tool.run_transcript_agent(query, llm, api_key or api_key),
    }
    
    # Add the special DirectAnswer tool
    def run_direct_answer(query: str, **kwargs) -> str:
        # This is a pseudo-tool that just returns the input
        # The actual response will be generated in final_output stage
        return f"DIRECT_RESPONSE_REQUESTED: {query}"
    
    # Add to existing tools
    tool_functions_map["DirectAnswer"] = run_direct_answer

    # Create LangChain Tool objects for the planning stage
    # Descriptions are crucial for the planner LLM
    tools_list = [
        Tool(
            name="FinancialSQL", 
            func=tool_functions_map["FinancialSQL"], # Use lambda wrapper
            description="Query the internal financial database with SQL. Use for financial metrics, e.g. revenue, profit for specific historical periods (2016-2020). Input should be a natural language question about the specific data needed."
        ),
        Tool(
            name="CCRSQL", 
            func=tool_functions_map["CCRSQL"], # Use lambda wrapper
            description="Query the CCR database for customer credit risk records. Use for credit/risk info, exposures, limits, ratings. Input should be a natural language question about specific CCR data."
        ),
        Tool(
            name="FinancialNewsSearch", 
            func=tool_functions_map["FinancialNewsSearch"], # Use lambda wrapper
            description="Search recent financial news articles or current market info using keywords or company name. Use for finding recent news or information not in historical databases."
        ),
        Tool(
            name="EarningsCallSummary", 
            func=tool_functions_map["EarningsCallSummary"], # Use lambda wrapper
            description="Retrieve and summarize earnings call transcripts (historical, ~2016-2020) for a given company to understand qualitative performance, strategy, and management commentary. Input should be a natural language query specifying the company and desired information."
        ),
        Tool(
            name="DirectAnswer",
            func=tool_functions_map["DirectAnswer"],
            description="Use ONLY when no other tools are needed and the LLM can answer directly without external data. For general knowledge questions, writing emails, explaining concepts, etc. Input should be a clear instruction describing what the LLM should respond with."
        )
    ]
    logger.info(f"Registered {len(tools_list)} tools.")
    return tools_list, tool_functions_map

# --- Plan Confirmation (already implemented) ---
# (confirm_plan_with_user function remains here)
def confirm_plan_with_user(plan_text: str) -> Tuple[bool, str]:
    """
    Displays the execution plan to the user and asks for confirmation.
    Handles user feedback for potential re-planning.

    Args:
        plan_text: The generated plan string.

    Returns:
        A tuple: (approved: bool, feedback_or_plan: str)
        - (True, plan_text) if the user approves.
        - (False, user_feedback) if the user rejects and provides feedback.
        - (False, "CANCELLED") if the user cancels.
    """
    # Add basic check for error in plan
    if plan_text.startswith("Error:"):
        print(f"\nPlan Generation Failed:\n{plan_text}")
        logger.error(f"[Confirmation] Plan generation failed, cannot confirm: {plan_text}")
        return False, "CANCELLED" # Treat plan error as cancellation
        
    print("\nProposed Plan:")
    print("--------------")
    print(plan_text)
    print("--------------")

    while True:
        confirm = input("Execute this plan? (yes/no/cancel): ").strip().lower()
        if confirm in ("yes", "y"):
            logger.info("[Confirmation] Plan approved by user.")
            return True, plan_text
        elif confirm == "no" or confirm == "n":
            logger.info("[Confirmation] Plan rejected by user.")
            feedback = input("Please provide feedback for re-planning, or type 'cancel' to abort: ").strip()
            if feedback.lower() == 'cancel':
                logger.info("[Confirmation] User cancelled after rejecting plan.")
                return False, "CANCELLED"
            else:
                logger.info(f"[Confirmation] User provided feedback: {feedback}")
                return False, feedback # Return feedback for re-planning
        elif confirm == "cancel":
             logger.info("[Confirmation] User cancelled confirmation.")
             return False, "CANCELLED"
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'cancel'.")

# --- Helper Function to Load Prompt from TXT --- 
def _load_prompt_from_txt(file_path: str) -> BasePromptTemplate:
    """Loads a prompt template from a .txt file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            template_str = f.read()
        # Basic check for placeholders
        input_variables = re.findall(r'{(\w+)}', template_str)
        return PromptTemplate(template=template_str, input_variables=input_variables)
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error loading prompt file {file_path}: {e}")
        raise

# --- Main Orchestration Function ---
def run_agent_session():
    """Runs the main interactive loop for the agent.
       Initializes components and orchestrates the stages.
    """
    logger.info("Initializing agent session...")

    # --- Initialization --- 
    try:
        # Load API Keys (ensure .env is loaded by main.py)
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables.")
        
        # Initialize LLM
        # TODO: Make model name configurable
        model_name = "claude-3-5-sonnet-20240620"
        llm = ChatAnthropic(model=model_name, temperature=0, anthropic_api_key=anthropic_api_key)
        # Attempt to log model name if available, otherwise log generic message
        try:
            # Check if 'model' attribute exists and log it
            actual_model_name = getattr(llm, 'model', model_name) # Use assigned name as fallback
            logger.info(f"LLM Initialized: {actual_model_name}")
        except AttributeError:
            logger.info("LLM Initialized (model name attribute not found).")

        # Load Prompts using helper function
        prompt_dir = os.path.join(os.path.dirname(__file__), '..', 'prompts')
        guardrails_prompt = _load_prompt_from_txt(os.path.join(prompt_dir, 'guardrails_prompt.txt'))
        planning_prompt = _load_prompt_from_txt(os.path.join(prompt_dir, 'planning_prompt.txt'))
        reasoning_prompt = _load_prompt_from_txt(os.path.join(prompt_dir, 'reasoning_prompt.txt'))
        final_output_prompt = _load_prompt_from_txt(os.path.join(prompt_dir, 'final_output_prompt.txt'))
        logger.info("Prompts loaded.")

        # Define DB Paths (make this more robust later if needed)
        # Assumes db files are in project_root/scripts/data/
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        db_paths = {
            "financial": os.path.join(project_root, "scripts", "data", "financial_data.db"),
            "ccr": os.path.join(project_root, "scripts", "data", "ccr_reporting.db")
        }
        # Basic check if DB files exist
        if not os.path.exists(db_paths["financial"]):
            logger.warning(f"Financial DB not found at {db_paths['financial']}")
        if not os.path.exists(db_paths["ccr"]):
             logger.warning(f"CCR DB not found at {db_paths['ccr']}")

        # Register Tools
        tools_list, tools_map = register_tools(llm, db_paths, anthropic_api_key)

    except Exception as e:
        logger.error(f"Agent Initialization Failed: {e}", exc_info=True)
        print(f"\nFATAL ERROR: Could not initialize agent components. Please check logs and environment setup. Error: {e}")
        return # Exit if initialization fails

    # --- Interaction Loop --- 
    greeting.greet_user()
    while True:
        try:
            user_query = input("\n> ").strip()
            if not user_query:
                continue
            if user_query.lower() in ("exit", "quit"):
                print("Goodbye!")
                break

            logger.info(f"Received user query: {user_query}")
            original_query = user_query # Keep original for later stages
            current_query_context = original_query # For re-planning

            # 1. Guardrails Stage
            if not guardrails.validate_query(original_query, llm, guardrails_prompt):
                print("I apologize, but I cannot proceed with that request based on safety guidelines.")
                continue

            # 2. Planning & Confirmation Loop
            plan_approved = False
            confirmed_plan = ""
            replan_attempts = 0
            while not plan_approved and replan_attempts < MAX_REPLAN_ATTEMPTS:
                # Generate Plan
                # Pass input_variables explicitly if needed by the template
                current_plan = planning.generate_plan(current_query_context, tools_list, llm, planning_prompt)
                
                # Confirm Plan
                approved, feedback_or_plan = confirm_plan_with_user(current_plan)
                
                if approved:
                    plan_approved = True
                    confirmed_plan = feedback_or_plan
                elif feedback_or_plan == "CANCELLED":
                    logger.info("User cancelled the query during planning.")
                    break # Break planning loop, will go to next iteration of main loop
                else:
                    # Re-plan based on feedback
                    replan_attempts += 1
                    logger.info(f"Re-planning attempt {replan_attempts}/{MAX_REPLAN_ATTEMPTS} based on feedback.")
                    # Modify context for the next planning attempt
                    current_query_context = f"Original Query: {original_query}\nUser Feedback on previous plan: {feedback_or_plan}\nPlease generate a revised plan based on this feedback."
            
            if not plan_approved:
                if feedback_or_plan != "CANCELLED": # Avoid double message if cancelled
                     print(f"Sorry, I couldn't generate a plan you approved after {replan_attempts} attempts. Please try rephrasing your query.")
                continue # Go to next iteration of main loop

            # 3. Execution Stage
            # Pass original_query to execution context if needed by naive parser
            # TODO: Refine how query context is passed if parser improves
            execution_summary, success = execution.execute_plan(confirmed_plan, tools_map, llm, db_paths, anthropic_api_key)
            print("\n--- Execution Summary --- ")
            print(execution_summary)
            print("-------------------------")

            if not success:
                print("\nExecution failed. Please review the summary above. Cannot proceed to reasoning.")
                continue

            # 4. Reasoning Stage
            reasoning_text = reasoning.reason_on_results(original_query, execution_summary, llm, reasoning_prompt)
            # Optional: Print reasoning for debug
            # print("\n--- Reasoning --- ")
            # print(reasoning_text)
            # print("-----------------")
            
            # Check if reasoning itself reported an error
            if reasoning_text.startswith("Error:"):
                 print(f"\nAn error occurred during reasoning: {reasoning_text}")
                 continue

            # 5. Final Output Stage
            final_answer = final_output.generate_final_answer(
                original_query, 
                reasoning_text, 
                llm, 
                final_output_prompt,
                execution_summary  # Pass the execution summary to generate steps summary
            )

            print("\nFinal Result:")
            print("-------------")
            print(final_answer)
            print("-------------")

        except KeyboardInterrupt:
            print("\nOperation cancelled by user. Goodbye!")
            break
        except Exception as e:
            logger.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            print(f"\nAn unexpected error occurred: {e}. Please check logs.")
            # Optionally break or continue after an error
            # continue 

    logger.info("Agent session ended.")

# --- Placeholder for the main orchestration function ---
# def run_agent_session():
#     pass 
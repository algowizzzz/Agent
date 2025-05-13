# Logic for the Planning stage (LLMChain for plan)
import logging
from typing import List

from langchain.chains import LLMChain
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import BasePromptTemplate
from langchain.agents import Tool # Use Langchain Tool for type hint

logger = logging.getLogger(__name__)

def generate_plan(query: str, tools: List[Tool], llm: BaseChatModel, prompt: BasePromptTemplate) -> str:
    """
    Generates a step-by-step plan to answer the user's query using available tools.

    Args:
        query: The user's input query.
        tools: A list of available LangChain Tool objects.
        llm: The language model instance.
        prompt: The prompt template for the planning stage.

    Returns:
        A string containing the numbered execution plan, or an error message string.
    """
    logger.info(f"[Planning] Generating plan for query: {query[:100]}...")
    plan = "Error: Failed to generate execution plan."

    try:
        # Format tool descriptions for the prompt
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])
        
        planning_chain = LLMChain(llm=llm, prompt=prompt, verbose=True) # Keep verbose for debugging
        
        # Use invoke
        response = planning_chain.invoke({
            "query": query,
            "tool_descriptions": tool_descriptions
        })

        # Extract plan text
        if isinstance(response, dict) and 'text' in response:
            plan_text = response['text'].strip()
            # Basic check: ensure it looks like a plan (e.g., starts with '1.')
            if plan_text and (plan_text.startswith("1.") or plan_text.startswith("Plan:")):
                plan = plan_text
                logger.info(f"[Planning] Generated plan:\n{plan}")
            else:
                logger.warning(f"[Planning] LLM did not return a valid formatted plan: {plan_text[:200]}...")
                plan = f"Error: Planning failed. LLM returned invalid format: {plan_text[:200]}"
        elif isinstance(response, str):
             plan_text = response.strip()
             if plan_text and (plan_text.startswith("1.") or plan_text.startswith("Plan:")):
                 plan = plan_text
                 logger.info(f"[Planning] Generated plan:\n{plan}")
             else:
                 logger.warning(f"[Planning] LLM did not return a valid formatted plan: {plan_text[:200]}...")
                 plan = f"Error: Planning failed. LLM returned invalid format: {plan_text[:200]}"
        else:
            logger.error(f"[Planning] Unexpected response type from LLMChain: {type(response)}")
            plan = "Error: Planning failed due to unexpected LLM response format."

    except Exception as e:
        logger.error(f"[Planning] Error during plan generation LLM call: {e}", exc_info=True)
        plan = f"Error: Failed to generate plan. Details: {type(e).__name__}"

    return plan 
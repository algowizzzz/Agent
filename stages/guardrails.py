# Logic for the Guardrails stage (request validation)
import logging
from typing import Optional

from langchain.chains import LLMChain
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import BasePromptTemplate

logger = logging.getLogger(__name__)

def validate_query(query: str, llm: BaseChatModel, prompt: BasePromptTemplate) -> bool:
    """
    Validates the user query against safety/policy guidelines using an LLM chain.

    Args:
        query: The user's input query.
        llm: The language model instance.
        prompt: The prompt template for the guardrails check.

    Returns:
        True if the query is allowed, False otherwise.
    """
    logger.info(f"[Guardrails] Validating query: {query[:100]}...")
    allowed = False # Default to not allowed
    try:
        guardrails_chain = LLMChain(llm=llm, prompt=prompt, verbose=True) # Keep verbose for debugging
        # Use invoke for better consistency and potential future features
        response = guardrails_chain.invoke({"query": query})
        
        # Extract the text result - response structure might vary slightly
        result_text = ""
        if isinstance(response, dict) and 'text' in response:
            result_text = response['text'].strip().upper()
        elif isinstance(response, str):
            result_text = response.strip().upper()
            
        logger.info(f"[Guardrails] LLM Validation response: '{result_text}'")

        if result_text.startswith("ALLOW"):
            allowed = True
        elif result_text.startswith("BLOCK"):
            allowed = False
            logger.warning(f"[Guardrails] Query blocked by policy: {query}")
        else:
            # Unexpected response from LLM
            logger.warning(f"[Guardrails] Unexpected response from LLM: '{result_text}'. Defaulting to block.")
            allowed = False

    except Exception as e:
        logger.error(f"[Guardrails] Error during validation LLM call: {e}", exc_info=True)
        allowed = False # Default to block on error

    logger.info(f"[Guardrails] Validation result: Allowed = {allowed}")
    return allowed 
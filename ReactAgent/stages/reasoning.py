# Logic for the Reasoning stage (LLMChain for analysis) 
import logging
from typing import Dict

from langchain.chains import LLMChain
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import BasePromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

def reason_on_results(query: str, execution_results: str, llm: BaseChatModel, prompt: BasePromptTemplate) -> str:
    """
    Analyzes the results from the execution stage to form a coherent understanding.
    Special handling for DirectAnswer requests.

    Args:
        query: The original user query.
        execution_results: A formatted string summarizing the outputs from the Execution stage.
        llm: The language model instance.
        prompt: The prompt template for the reasoning stage.

    Returns:
        A string containing the LLM's reasoning, or an error message string.
    """
    logger.info(f"[Reasoning] Starting analysis for query: {query[:100]}...")
    reasoning = "Error: Failed to perform reasoning on execution results."

    try:
        # Check if this was a direct response request
        if "DIRECT_RESPONSE_REQUESTED" in execution_results:
            logger.info("[Reasoning] Detected DirectAnswer request. Preparing direct response...")
            
            # Extract the instruction from execution results
            # Format will be: "...OK. Direct LLM response requested." in the execution results
            # The actual instruction is in the tool_input part
            
            # Extract the instruction from the execution step
            # Simple extraction - get what's after the 'DirectAnswer:'
            try:
                # First try to find DirectAnswer: in the original query
                parts = execution_results.split("DirectAnswer:", 1)
                if len(parts) > 1:
                    # Get the instruction part, usually up to the next quote or end of line
                    instruction = parts[1].split("'", 1)[0].split("...", 1)[0].strip()
                else:
                    # Fallback to using the original query
                    instruction = query
                
                # Create a special direct response prompt
                direct_template = (
                    "You need to respond directly to this request without using tools or external data:\n\n"
                    "Request: {instruction}\n\n"
                    "Provide a comprehensive, helpful response based on your knowledge."
                )
                direct_prompt = PromptTemplate.from_template(direct_template)
                direct_chain = direct_prompt | llm | StrOutputParser()
                
                direct_response = direct_chain.invoke({"instruction": instruction})
                reasoning = f"DIRECT_RESPONSE:\n{direct_response}"
                logger.info(f"[Reasoning] Generated direct response for: {instruction[:100]}...")
                return reasoning
            except Exception as extract_err:
                logger.error(f"[Reasoning] Error extracting instruction from DirectAnswer results: {extract_err}", exc_info=True)
                reasoning = f"Error: Failed to process DirectAnswer request. Details: {extract_err}"
                return reasoning
        
        # Regular reasoning for tool-based responses
        reasoning_chain = LLMChain(llm=llm, prompt=prompt, verbose=True) # Keep verbose for debugging
        
        # Use invoke
        response = reasoning_chain.invoke({
            "query": query,
            "steps_and_results": execution_results
        })

        # Extract reasoning text
        if isinstance(response, dict) and 'text' in response:
            reasoning_text = response['text'].strip()
            if reasoning_text:
                reasoning = reasoning_text
                logger.info(f"[Reasoning] Analysis complete:\n{reasoning[:500]}...")
            else:
                 logger.warning("[Reasoning] LLM returned empty reasoning text.")
                 reasoning = "Error: Reasoning failed. LLM returned empty text."
        elif isinstance(response, str):
             reasoning_text = response.strip()
             if reasoning_text:
                 reasoning = reasoning_text
                 logger.info(f"[Reasoning] Analysis complete:\n{reasoning[:500]}...")
             else:
                 logger.warning("[Reasoning] LLM returned empty reasoning text.")
                 reasoning = "Error: Reasoning failed. LLM returned empty text."
        else:
            logger.error(f"[Reasoning] Unexpected response type from LLMChain: {type(response)}")
            reasoning = "Error: Reasoning failed due to unexpected LLM response format."

    except Exception as e:
        logger.error(f"[Reasoning] Error during reasoning LLM call: {e}", exc_info=True)
        reasoning = f"Error: Failed to perform reasoning. Details: {type(e).__name__}"

    return reasoning 
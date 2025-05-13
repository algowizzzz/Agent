import json
import os
from pathlib import Path
from typing import Dict, Any
import re
import logging

logger = logging.getLogger(__name__)

def load_tool_prompts_config():
    """
    Load the tool prompts configuration from a JSON file.
    
    Returns:
        dict: The tool prompts configuration dictionary
    """
    # Get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    
    # Path to the tool prompts config file
    config_path = script_dir / "tool_prompts_config.json"
    
    # Check if the file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Tool prompts configuration file not found at {config_path}")
    
    # Load the configuration
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing tool prompts configuration: {e}")

def get_department_tool_config() -> Dict[str, Any]:
    """Get the department tool configuration"""
    config = load_tool_prompts_config()
    return config.get("department_tool", {})

def get_category_tool_config() -> Dict[str, Any]:
    """Get the category tool configuration"""
    config = load_tool_prompts_config()
    return config.get("category_tool", {})

def get_document_tool_config() -> Dict[str, Any]:
    """Get the document tool configuration"""
    config = load_tool_prompts_config()
    return config.get("document_tool", {})

def format_department_prompt(formatted_summary, query, category_summaries=""):
    """
    Format the department tool prompt using the template from the config.
    
    Args:
        formatted_summary (str): The formatted department summary
        query (str): The user query
        category_summaries (str, optional): Formatted summaries of available categories

    Returns:
        str: The formatted prompt ready to send to the LLM
    """
    # Get the department tool configuration
    dept_config = get_department_tool_config()
    
    # Get the prompt template from the config
    prompt_template = dept_config.get("prompt_template", "")
    
    # Replace the placeholders with the actual values
    prompt = prompt_template.replace("{formatted_summary}", formatted_summary)
    prompt = prompt.replace("{query}", query)
    prompt = prompt.replace("{category_summaries}", category_summaries)
    
    return prompt

def format_category_prompt(formatted_summary: str, query: str, category_id: str) -> str:
    """
    Format the category tool prompt with the given parameters.
    Requests plain text Thought/Answer output.
    """
    # Plain text prompt template
    prompt_template = """You are analyzing a category summary to answer a user's query.

Category Summary for {category_id}:
{formatted_summary}

User Query: {query}

Your task:
1. Analyze the Category Summary to see if it contains information to answer the User Query.
2. Explain your reasoning step-by-step.
3. Provide a concise answer based ONLY on the Category Summary.
4. If the summary does not contain enough information, you can infer BUT state that clearly.

Format your response as follows (PLAIN TEXT, NO JSON):
Thought: [Explain your reasoning step-by-step here]
Answer: [Provide your concise answer based ONLY on the summary, or state if infering or deducing]
"""

    return prompt_template.format(
        formatted_summary=formatted_summary,
        query=query,
        category_id=category_id 
    )

def format_document_prompt(query: str, documents: str) -> str:
    """
    Format the document tool prompt with the given parameters.
    Very simplified plain text version.
    
    Args:
        query (str): The user query (e.g., 'Summarize performance', 'What was revenue?')
        documents (str): Formatted document content (can be multiple documents concatenated)
        
    Returns:
        str: The formatted prompt ready to send to the LLM
    """
    # Very light prompt template
    prompt_template = """You are a helpful assistant analyzing earnings call transcripts.

User Query: {query}

Transcript(s):
{documents}

Based ONLY on the provided Transcript(s) text, provide a concise answer to the User Query.
If the transcripts don't contain the answer, simply state that the information is not available in the provided text.
Do not add any explanation or conversational filler unless the query specifically asks for it.

Answer:
"""
    
    prompt = prompt_template.format(query=query, documents=documents)
    
    return prompt

# Add these utility functions for handling other config types if needed
def get_summary_config():
    """
    Load the summary config if available
    
    Returns:
        dict: The summary configuration dictionary
    """
    # Try to load the summary config from the current directory or parent directory
    for config_path in [
        Path.cwd() / "summary_prompts_config.json",
        Path.cwd().parent / "summary_prompts_config.json"
    ]:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If there's an error, continue to the next potential location
                continue
    
    # If no config is found, return an empty dict
    return {}

def sanitize_json_response(response: str) -> str:
    """Extracts a JSON object string from a potentially larger string (e.g., markdown code block).
       Handles standard JSON escape sequences via json.loads.
    Args:
        response (str): The raw string response from the LLM.
    Returns:
        str: The extracted JSON string.
    Raises:
        ValueError: If a valid JSON object string cannot be extracted or parsed.
    """
    logger.debug(f"Attempting to sanitize JSON input (first 100 chars): {repr(response[:100])}")

    # Find the first '{' and the last '}'
    start_brace = response.find('{')
    end_brace = response.rfind('}')

    if start_brace == -1 or end_brace == -1 or end_brace < start_brace:
        logger.error(f"Could not find valid JSON start/end braces in response: {response[:200]}...")
        raise ValueError("Could not extract JSON object from response string.")

    # Extract the potential JSON substring
    json_str = response[start_brace : end_brace + 1]
    logger.debug(f"Extracted potential JSON string: {repr(json_str[:100])}...")

    # Attempt to parse the extracted string to validate it
    try:
        parsed = json.loads(json_str)
        # Optional: re-serialize to ensure consistent formatting, though json_str should be fine
        # return json.dumps(parsed)
        logger.info("Successfully validated extracted JSON string.")
        return json_str
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extracted JSON string: {e}. String: {json_str[:200]}...")
        raise ValueError(f"Extracted string is not valid JSON: {e}. String: {json_str[:200]}...")
    except Exception as e_other:
        logger.error(f"Unexpected error during JSON validation: {e_other}")
        raise # Re-raise unexpected errors

# Category tool configuration
CATEGORY_TOOL_CONFIG = {
    "model": "claude-3-haiku-20240307",
    "temperature": 0,
    "max_tokens": 1000,
    "prompt_template": """Analyze the provided category summary for {category_id} and answer the query.

{summary}

Question: {query}

Think through this step by step:
1. Review the available information for {category_id}
2. Identify relevant details for the query
3. Determine if you can provide a confident answer
4. Format your response carefully

Your response MUST be a valid JSON object with these fields:
- thought: Your reasoning process
- answer: Your detailed answer or null if insufficient information
- document_ids: Array of relevant document IDs or empty array

Format your response EXACTLY like this, with commas between fields:
{
  "thought": "...",
  "answer": "...",
  "document_ids": []
}"""
}

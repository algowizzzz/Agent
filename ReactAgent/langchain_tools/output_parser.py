"""
Custom output parser for the hierarchical agent.
Handles ReAct style output with Thought, Action, Action Input sections.
Includes fix-up logic for common LLM formatting errors.
"""

import logging
import re
from typing import Union

from langchain_core.agents import AgentAction, AgentFinish
from langchain.agents.output_parsers.react_single_input import ReActSingleInputOutputParser
from langchain_core.exceptions import OutputParserException

logger = logging.getLogger(__name__)

# Regex patterns to extract sections
# Updated regex to be more robust to variations in spacing and capitalization
# and handle multi-line inputs
THOUGHT_PATTERN = re.compile(
    r"^\s*Thought:\s*(.*?)(?:\n\s*Action:|$)|"  # thought can span lines
    r"^\s*thought:\s*(.*?)(?:\n\s*action:|$)",  # lowercase
    re.DOTALL | re.IGNORECASE | re.MULTILINE
)
ACTION_PATTERN = re.compile(
    r"^\s*Action:\s*(\w+.*?)(?:\n\s*Action Input:|$)|"  # action name might have spaces
    r"^\s*action:\s*(\w+.*?)(?:\n\s*action input:|$)",  # lowercase
    re.DOTALL | re.IGNORECASE | re.MULTILINE
)
ACTION_INPUT_PATTERN = re.compile(
    r"^\s*Action Input:\s*(.*?)(?:\n\s*Observation:|$)|"  # input can span lines
    r"^\s*action input:\s*(.*?)(?:\n\s*observation:|$)",  # lowercase
    re.DOTALL | re.IGNORECASE | re.MULTILINE
)
FINAL_ANSWER_PATTERN = re.compile(
    r"^\s*Final Answer:\s*(.*)|"
    r"^\s*final answer:\s*(.*)",
    re.DOTALL | re.IGNORECASE | re.MULTILINE
)

class EnhancedAgentOutputParser(ReActSingleInputOutputParser):
    """Parses ReAct-style LLM output with enhanced robustness and fix-up logic."""

    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        """Parse the LLM output text."""
        logger.debug(f"Parsing LLM Output:\n-------\n{text}\n-------")
        includes_answer = "Final Answer:" in text or "final answer:" in text
        includes_action = "Action:" in text or "action:" in text

        if includes_answer:
            match = FINAL_ANSWER_PATTERN.search(text)
            if match:
                # Extract content from either capturing group
                answer = match.group(1) or match.group(2)
                if answer is not None:
                     return AgentFinish({"output": answer.strip()}, text)
                else:
                     # Handle case where pattern matches but group is empty
                     logger.warning("Final Answer pattern matched, but no content found.")
                     # Fall through to fix-up logic or raise error
            else:
                # Handle case where keyword exists but regex fails
                logger.warning("'Final Answer:' found, but regex pattern failed to match.")
                # Fall through to fix-up logic or raise error

        if not includes_action:
             # If no action and no Final Answer, likely needs fix-up or is an error
             logger.warning("LLM output contains neither 'Action:' nor 'Final Answer:'. Attempting fix-up.")
             return self._fix_malformed_output(text, original_text=text)

        # Attempt to parse standard Action/Action Input
        thought_match = THOUGHT_PATTERN.search(text)
        action_match = ACTION_PATTERN.search(text)
        action_input_match = ACTION_INPUT_PATTERN.search(text)

        if action_match and action_input_match:
            action = action_match.group(1) or action_match.group(2)
            action_input = action_input_match.group(1) or action_input_match.group(2)
            thought = (thought_match.group(1) or thought_match.group(2) or "").strip()
            tool = action.strip()
            tool_input = action_input.strip(" \"\n") # Clean whitespace, quotes, newlines
            log = f"Thought: {thought}\nAction: {tool}\nAction Input: {tool_input}"

            logger.debug(f"Parsed Action: tool='{tool}', input='{tool_input}', log='{thought}'")
            return AgentAction(tool, tool_input, log)
        else:
            # If Action: exists but Action Input: doesn't, or regex fails
            logger.warning("LLM output includes 'Action:' but failed standard parsing. Attempting fix-up.")
            return self._fix_malformed_output(text, original_text=text)

    def _fix_malformed_output(self, text: str, original_text: str) -> Union[AgentAction, AgentFinish]:
        """Attempts to fix common LLM output formatting errors."""
        logger.info(f"Attempting to fix malformed output: {text[:200]}...")

        # Scenario 1: Missing 'Action Input:' but Action is present
        action_match_fix = ACTION_PATTERN.search(text)
        if action_match_fix and "Action Input:" not in text and "action input:" not in text:
             action_name = (action_match_fix.group(1) or action_match_fix.group(2)).strip()
             # Assume input is the rest of the string after Action: line
             input_start_index = action_match_fix.end()
             potential_input = text[input_start_index:].strip()
             # Remove Observation: if it exists immediately after
             potential_input = re.sub(r"^\s*Observation:.*", "", potential_input, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE).strip()

             if potential_input:
                 logger.warning(f"Fix-up: Found Action '{action_name}', assuming rest is input: '{potential_input[:100]}...'")
                 thought = (THOUGHT_PATTERN.search(text).group(1) or THOUGHT_PATTERN.search(text).group(2) or "").strip()
                 log = f"Thought: {thought}\nAction: {action_name}\nAction Input: {potential_input} (FIXED)"
                 return AgentAction(action_name, potential_input, log)

        # Scenario 2: Action provided without Action Input: label
        # E.g. Action: category_tool(query="...", category="...")
        action_call_match = re.search(r"^\s*Action:\s*(\w+)\((.*)\)\s*$", text, re.IGNORECASE | re.MULTILINE)
        if action_call_match:
            tool_name = action_call_match.group(1).strip()
            tool_input = action_call_match.group(2).strip()
            logger.warning(f"Fix-up: Found direct tool call format. Tool: '{tool_name}', Input: '{tool_input}'")
            thought = (THOUGHT_PATTERN.search(text).group(1) or THOUGHT_PATTERN.search(text).group(2) or "").strip()
            log = f"Thought: {thought}\nAction: {tool_name}\nAction Input: {tool_input} (FIXED - Direct Call)"
            return AgentAction(tool_name, tool_input, log)

        # Scenario 3: Only thought is present (treat as finish? or error?)
        thought_only_match = THOUGHT_PATTERN.search(text)
        if thought_only_match and not ACTION_PATTERN.search(text) and not FINAL_ANSWER_PATTERN.search(text):
            thought = (thought_only_match.group(1) or thought_only_match.group(2)).strip()
            # Depending on the agent design, this could be an error or a final thought
            # For ReAct, a thought alone isn't a valid step. Raise error.
            logger.warning("Fix-up Attempt: Found only a Thought. This is not a valid ReAct step.")
            raise OutputParserException(f"Invalid ReAct step: Only Thought found. Text: `{original_text}`")

        # If no fix-up rule applies, raise the original error
        logger.error(f"Failed to parse LLM output even after fix-up attempts: {original_text}")
        raise OutputParserException(f"Could not parse LLM output: `{original_text}`")

    @property
    def _type(self) -> str:
        return "enhanced_react_single_input"

# Remove or comment out the old parser if it exists
# class HierarchicalAgentOutputParser(AgentOutputParser):
#     ... 
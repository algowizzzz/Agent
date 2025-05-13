#!/usr/bin/env python3
"""
Control Analysis Tool - Analyzes operational control descriptions in financial/banking contexts

This tool performs 5W analysis, gap identification, and test plan generation for controls.
"""

import logging
import os
import json
from typing import Optional, Dict, Any, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

def run_control_analyzer_agent(
    query: str,
    llm: Optional[BaseChatModel] = None,
    api_key: Optional[str] = None
) -> str:
    """
    Main function to analyze operational control descriptions.
    
    Args:
        query: The control description or query to analyze
        llm: Optional LangChain language model (if not provided, will create one)
        api_key: Optional API key for creating LLM (if not provided, uses env var)
        
    Returns:
        String with the control analysis results
    """
    logger.info(f"[Control Analysis Agent] Processing query: {query}")
    
    # Create LLM if not provided
    if llm is None:
        try:
            from langchain_anthropic import ChatAnthropic
            
            if api_key is None:
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if not api_key:
                    raise ValueError("No API key provided and ANTHROPIC_API_KEY not in environment")
            
            llm = ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=0, anthropic_api_key=api_key)
            logger.info("[Control Analysis Agent] Created new LLM instance")
        except Exception as e:
            error_msg = f"[Control Analysis Agent] Failed to create LLM: {str(e)}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    # Determine what type of analysis is requested
    analysis_type = _determine_analysis_type(query)
    
    try:
        # Perform the requested analysis
        if "5w" in analysis_type:
            result = _perform_5ws_analysis(query, llm)
            logger.info("[Control Analysis Agent] Completed 5Ws analysis")
        elif "gap" in analysis_type or "improvement" in analysis_type:
            result = _suggest_control_improvements(query, llm)
            logger.info("[Control Analysis Agent] Completed gap analysis")
        elif "test" in analysis_type:
            result = _create_control_test_script(query, llm)
            logger.info("[Control Analysis Agent] Created test script")
        else:
            # Default to full analysis
            logger.info("[Control Analysis Agent] Performing full analysis")
            
            # Extract the control description
            control_description = _extract_control_description(query)
            
            # Perform all analyses
            analysis_5w = _perform_5ws_analysis(control_description, llm)
            gaps = _suggest_control_improvements(control_description, llm)
            test_script = _create_control_test_script(control_description, llm)
            
            # Combine the results
            result = f"""## CONTROL ANALYSIS REPORT

### Control Description:
{control_description}

### 5Ws Analysis:
{analysis_5w}

### Design Gaps and Improvement Opportunities:
{gaps}

### Test Script:
{test_script}
"""
        
        return result
        
    except Exception as e:
        error_msg = f"[Control Analysis Agent] Error during analysis: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"

def _determine_analysis_type(query: str) -> str:
    """
    Determine what type of analysis is being requested in the query.
    
    Args:
        query: The user query
        
    Returns:
        String indicating the analysis type: "5w", "gap", "test", or "full"
    """
    query_lower = query.lower()
    
    if "5w" in query_lower or "who what when where why" in query_lower:
        return "5w"
    elif "gap" in query_lower or "improve" in query_lower or "enhancement" in query_lower:
        return "gap"
    elif "test" in query_lower or "script" in query_lower or "procedure" in query_lower:
        return "test"
    else:
        return "full"

def _extract_control_description(query: str) -> str:
    """
    Extract the control description from the query.
    
    Args:
        query: The user query containing the control description
        
    Returns:
        The extracted control description
    """
    # Simple extraction based on common patterns
    if ":" in query:
        parts = query.split(":", 1)
        if len(parts) > 1:
            return parts[1].strip()
    
    if "analyze" in query.lower() or "analyse" in query.lower():
        # Try to find text after "analyze"/"analyse"
        pattern = r'analy[sz]e\s+(.+)'
        import re
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    # Default to returning the full query if no pattern matches
    return query.strip()

def _perform_5ws_analysis(control_description: str, llm: BaseChatModel) -> str:
    """
    Analyze a control description using the 5Ws framework.
    
    Args:
        control_description: The control description to analyze
        llm: LangChain language model
        
    Returns:
        5Ws analysis as a string
    """
    logger.info(f"[Control Analysis] Performing 5Ws analysis on: {control_description[:50]}...")
    
    system_prompt = """You are a control design expert specialized in operational risk controls for financial institutions.
    
Analyze the given control description using the 5Ws framework:

1. WHO: Identify who performs the control (role/title, not a specific person)
2. WHAT: Explain what specific action is performed
3. WHEN: Determine the timing and frequency of the control execution
4. WHERE: Identify where the control is performed (system, location, etc.)
5. WHY: Explain the purpose/objective of the control

For each W, provide:
- The specific element from the control description
- Your analysis
- An assessment (Clear, Implied, or Missing)

Format your response as a detailed analysis for each of the 5Ws.
"""

    human_prompt = f"Analyze this control description using the 5Ws framework:\n\n{control_description}"
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"[Control Analysis] Error in 5Ws analysis: {str(e)}")
        return f"Error performing 5Ws analysis: {str(e)}"

def _suggest_control_improvements(control_description: str, llm: BaseChatModel) -> str:
    """
    Analyze a control description and suggest improvements.
    
    Args:
        control_description: The control description to analyze
        llm: LangChain language model
        
    Returns:
        Control improvement suggestions as a string
    """
    logger.info(f"[Control Analysis] Suggesting improvements for: {control_description[:50]}...")
    
    system_prompt = """You are a control design expert specialized in operational risk controls for financial institutions.
    
Analyze the given control description for design gaps and suggest improvements:

1. Identify any missing 5W elements (Who, What, When, Where, Why)
2. Assess control frequency and whether it's appropriate for the risk
3. Evaluate if the control is preventive, detective, or corrective
4. Determine if the control is manual, automated, or hybrid
5. Check for clarity in responsibility and accountability
6. Assess if evidence/documentation requirements are clear
7. Evaluate exception handling procedures

For each identified gap, provide:
1. The specific gap/issue
2. Why it's problematic
3. A concrete suggestion to improve the control
"""

    human_prompt = f"Analyze this control description for design gaps and suggest improvements:\n\n{control_description}"
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"[Control Analysis] Error in improvement suggestions: {str(e)}")
        return f"Error generating improvement suggestions: {str(e)}"

def _create_control_test_script(control_description: str, llm: BaseChatModel) -> str:
    """
    Create a test script for evaluating the control.
    
    Args:
        control_description: The control description to analyze
        llm: LangChain language model
        
    Returns:
        Test script as a string
    """
    logger.info(f"[Control Analysis] Creating test script for: {control_description[:50]}...")
    
    system_prompt = """You are a control testing expert specialized in operational risk controls for financial institutions.
    
Create a comprehensive test script for evaluating the given control. The test script should include:

1. Test Objective: Clear statement of what the test aims to verify
2. Pre-requisites: Required access, documents, or tools needed
3. Test Steps: Detailed, numbered steps for testing the control
4. Sample Selection: How to select samples for testing
5. Evidence Collection: Specific evidence to collect during testing
6. Evaluation Criteria: How to determine if the control is operating effectively
7. Potential Issues: Common problems that might be encountered
8. Remediation Guidance: What to recommend if the control fails testing

Format your response as a structured test script suitable for control testing professionals.
"""

    human_prompt = f"Create a test script for this control:\n\n{control_description}"
    
    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logger.error(f"[Control Analysis] Error in test script creation: {str(e)}")
        return f"Error creating test script: {str(e)}" 
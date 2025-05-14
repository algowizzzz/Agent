#!/usr/bin/env python3
"""
Control Analysis Tool - A sub-agent with specialized tools for analyzing operational controls
using the 5Ws framework, generating test scripts, and evaluating control effectiveness.

This module provides four main tools wrapped in a sub-agent architecture:
1. Control 5Ws Analysis - Analyzes controls using the Who, What, When, Where, Why framework
2. Operational Effectiveness Script Generator - Creates test scripts for operational controls
3. Design Effectiveness Evaluator - Assesses control design against best practices
4. Control Fetcher - Retrieves control information from a central JSON repository

The sub-agent can execute multiple tools in sequence based on user requests,
with a special "full analysis" mode that executes all three analysis tools.
"""

import logging
import os
import json
import re
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
import time
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_CONTROLS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "data", "controls.json"
)

# --- Control Analysis Sub-Agent Implementation ---
def run_control_analyzer_agent(
    query: str, 
    llm: Optional[BaseChatModel] = None,
    api_key: Optional[str] = None,
    controls_path: Optional[str] = None
) -> str:
    """
    Main entry point for the control analysis sub-agent.
    Routes the query to the appropriate specialized tool or executes multiple tools in sequence.
    
    Args:
        query: The user's query about control analysis
        llm: Optional language model to use
        api_key: Optional API key for creating LLM
        controls_path: Optional path to the controls.json file
        
    Returns:
        String with the analysis results
    """
    logger.info(f"[Control Analysis] Processing query: {query}")
    
    try:
        # Create LLM if not provided
        if llm is None:
            try:
                if api_key is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        return "Error: API key not provided and not found in environment"
                
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", 
                    temperature=0.1,
                    anthropic_api_key=api_key
                )
                logger.info("[Control Analysis] Created new LLM instance")
            except Exception as e:
                error_msg = f"[Control Analysis] Failed to create LLM: {str(e)}"
                logger.error(error_msg)
                return f"Error: {error_msg}"
        
        # Load controls data first for all operations
        controls_data = load_controls_data(controls_path)
        if isinstance(controls_data, str):  # Error message
            return controls_data
            
        # Parse the orchestration request to determine:
        # 1. Does it involve retrieving control info?
        # 2. Does it involve analysis?
        # 3. Which controls (specific ID or all)?
        # 4. Which analysis types (5W, OE, DE)?
        orchestration_prompt = f"""Determine how to process this query about controls:

USER QUERY: {query}

The PRC library contains these controls:
{json.dumps(controls_data, indent=2)}

Please analyze this query and provide your recommendations in the following JSON format:

{{
  "control_info": {{
    "needed": true/false, // Does the query ask about listing/finding controls?
    "specific_id": "CTRL-001" or null, // If a specific control ID is mentioned
    "list_all": true/false // Does the query ask for all controls?
  }},
  "analysis": {{
    "needed": true/false, // Does the query ask for analysis?
    "types": ["5WS", "OE", "DE"], // Which analysis types are requested?
    "target": "SPECIFIED_CONTROL" or "ALL_CONTROLS" or "DESCRIPTION_IN_QUERY" // What to analyze
  }},
  "explanation": "Brief explanation of this orchestration plan"
}}

Examples:
1. "Tell me about control CTRL-001" → Only control_info needed, specific_id
2. "Do a 5W analysis of this control: [description]" → Only analysis needed, DESCRIPTION_IN_QUERY
3. "List all controls and do a 5W analysis on each" → Both needed, list_all=true, target=ALL_CONTROLS
"""

        # Get orchestration plan
        orchestration_response = llm.invoke(orchestration_prompt)
        orchestration_text = orchestration_response.content.strip()
        
        # Extract JSON with better error handling
        orch_plan = None
        try:
            # Try different methods to extract JSON
            if "```json" in orchestration_text:
                orch_json = orchestration_text.split("```json")[1].split("```")[0].strip()
            elif "```" in orchestration_text:
                orch_json = orchestration_text.split("```")[1].strip()
            else:
                # Try to find JSON object by looking for first { and last }
                start_idx = orchestration_text.find('{')
                end_idx = orchestration_text.rfind('}')
                if start_idx >= 0 and end_idx > start_idx:
                    orch_json = orchestration_text[start_idx:end_idx+1]
                else:
                    orch_json = orchestration_text
            
            # Remove any comments in JSON before parsing
            orch_json = re.sub(r'//.*?[\r\n]', '\n', orch_json)
            orch_json = re.sub(r'/\*.*?\*/', '', orch_json, flags=re.DOTALL)
            
            # Parse the cleaned JSON
            orch_plan = json.loads(orch_json)
            logger.info(f"[Control Analysis] Orchestration plan: {orch_plan}")
        except Exception as e:
            logger.warning(f"[Control Analysis] Failed to parse orchestration plan: {str(e)}")
            orch_plan = None
            
        if orch_plan is None:
            logger.warning("[Control Analysis] Using simple mode for control analysis")
            return simple_control_analysis(query, controls_data, llm, api_key)
        
        # Start building the response
        results = []
        
        # Step 1: Handle control info retrieval if needed
        if orch_plan.get("control_info", {}).get("needed", False):
            specific_id = orch_plan.get("control_info", {}).get("specific_id")
            list_all = orch_plan.get("control_info", {}).get("list_all", False)
            
            if specific_id:
                # Find specific control
                control = None
                for c in controls_data:
                    if c.get("id") == specific_id:
                        control = c
                        break
                        
                if control:
                    results.append(("CONTROL DETAILS", format_control_details(control)))
                else:
                    results.append(("CONTROL LOOKUP", f"Control {specific_id} does not exist in the PRC library."))
            
            elif list_all:
                # List all controls
                if controls_data:
                    controls_list = ""
                    for c in controls_data:
                        controls_list += f"ID: {c.get('id', 'Unknown')}\n"
                        controls_list += f"Name: {c.get('name', 'Unnamed')}\n"
                        controls_list += f"Type: {c.get('type', 'Not specified')}\n"
                        controls_list += f"Category: {c.get('category', 'Not specified')}\n"
                        controls_list += f"Owner: {c.get('owner', 'Not specified')}\n"
                        controls_list += f"Status: {c.get('status', 'Not specified')}\n\n"
                    results.append(("CONTROLS IN PRC LIBRARY", controls_list))
                else:
                    results.append(("CONTROLS IN PRC LIBRARY", "No controls found in the PRC library."))
        
        # Step 2: Handle analysis if needed
        if orch_plan.get("analysis", {}).get("needed", False):
            analysis_types = orch_plan.get("analysis", {}).get("types", ["5WS"])
            analysis_target = orch_plan.get("analysis", {}).get("target", "DESCRIPTION_IN_QUERY")
            
            # Determine what to analyze
            if analysis_target == "SPECIFIED_CONTROL":
                specific_id = orch_plan.get("control_info", {}).get("specific_id")
                if specific_id:
                    # Find the control to analyze
                    control = None
                    for c in controls_data:
                        if c.get("id") == specific_id:
                            control = c
                            break
                            
                    if control:
                        # Use control description from the found control
                        control_to_analyze = control.get("description", "")
                        if not control_to_analyze:
                            control_to_analyze = f"Control {specific_id}: {control.get('name', '')}"
                    else:
                        results.append(("ANALYSIS ERROR", f"Control {specific_id} not found in PRC library."))
                        control_to_analyze = None
                else:
                    control_to_analyze = None
                    results.append(("ANALYSIS ERROR", "No control ID specified for analysis."))
            
            elif analysis_target == "ALL_CONTROLS":
                # Will analyze each control in sequence
                for control in controls_data:
                    control_id = control.get("id", "Unknown")
                    control_desc = control.get("description", "") or control.get("name", "Unnamed control")
                    
                    results.append((f"ANALYZING CONTROL {control_id}", f"Name: {control.get('name', 'Unnamed')}"))
                    
                    for analysis_type in analysis_types:
                        if analysis_type == "5WS":
                            result = analyze_control_5ws(control_desc, control, llm, api_key)
                            if result.get("error"):
                                results.append((f"5Ws ANALYSIS ERROR - {control_id}", result["error"]))
                            else:
                                formatted_result = format_5ws_analysis(result.get("analysis", {}))
                                results.append((f"5Ws ANALYSIS - {control_id}", formatted_result))
                        
                        elif analysis_type == "OE":
                            result = generate_operational_effectiveness_script(control_desc, control, llm, api_key)
                            if result.get("error"):
                                results.append((f"OE SCRIPT ERROR - {control_id}", result["error"]))
                            else:
                                formatted_result = format_test_script(result.get("test_script", {}))
                                results.append((f"OE SCRIPT - {control_id}", formatted_result))
                        
                        elif analysis_type == "DE":
                            result = evaluate_design_effectiveness(control_desc, control, llm, api_key)
                            if result.get("error"):
                                results.append((f"DE EVALUATION ERROR - {control_id}", result["error"]))
                            else:
                                formatted_result = format_design_evaluation(result.get("assessment", {}))
                                results.append((f"DE EVALUATION - {control_id}", formatted_result))
                
                # Skip the individual control analysis since we've done it for all
                control_to_analyze = None
            
            else:  # DESCRIPTION_IN_QUERY
                # Use the query itself as the control description
                control_to_analyze = query
            
            # Perform analysis on the determined control if needed
            if control_to_analyze:
                for analysis_type in analysis_types:
                    if analysis_type == "5WS":
                        result = analyze_control_5ws(control_to_analyze, None, llm, api_key)
                        if result.get("error"):
                            results.append(("5Ws ANALYSIS ERROR", result["error"]))
                        else:
                            formatted_result = format_5ws_analysis(result.get("analysis", {}))
                            results.append(("5Ws ANALYSIS", formatted_result))
                    
                    elif analysis_type == "OE":
                        result = generate_operational_effectiveness_script(control_to_analyze, None, llm, api_key)
                        if result.get("error"):
                            results.append(("OE SCRIPT ERROR", result["error"]))
                        else:
                            formatted_result = format_test_script(result.get("test_script", {}))
                            results.append(("OPERATIONAL EFFECTIVENESS TEST SCRIPT", formatted_result))
                    
                    elif analysis_type == "DE":
                        result = evaluate_design_effectiveness(control_to_analyze, None, llm, api_key)
                        if result.get("error"):
                            results.append(("DE EVALUATION ERROR", result["error"]))
                        else:
                            formatted_result = format_design_evaluation(result.get("assessment", {}))
                            results.append(("DESIGN EFFECTIVENESS EVALUATION", formatted_result))
        
        # Combine results
        if not results:
            return "Error: No operation was performed. Please specify what kind of control analysis you need."
            
        combined_result = ""
        for title, content in results:
            combined_result += f"## {title}\n\n{content}\n\n"
            
        return combined_result.strip()
            
    except Exception as e:
        logger.error(f"[Control Analysis] Error during analysis: {str(e)}")
        return f"Error: Control analysis failed: {str(e)}" 

def load_controls_data(controls_path: Optional[str] = None) -> Union[List[Dict[str, Any]], str]:
    """Load controls data from JSON file."""
    # Use default path if not provided
    if controls_path is None:
        controls_path = DEFAULT_CONTROLS_PATH
    
    try:
        # Check if file exists
        if not os.path.exists(controls_path):
            return f"Error: Controls file not found at {controls_path}"
        
        # Read and parse JSON file
        with open(controls_path, 'r') as f:
            controls_data = json.load(f)
            
        # Extract controls array
        controls = controls_data.get("controls", [])
        
        if not controls:
            return "No controls found in the controls file."
            
        return controls
            
    except json.JSONDecodeError:
        return f"Error: Invalid JSON format in controls file at {controls_path}"
    except Exception as e:
        logger.error(f"[Control Analysis] Error loading controls data: {str(e)}")
        return f"Error loading control data: {str(e)}"

def simple_control_analysis(query: str, controls_data: List[Dict[str, Any]], llm: BaseChatModel, api_key: Optional[str] = None) -> str:
    """Simplified control analysis when orchestration fails."""
    
    try:
        # Check if the query is asking for a list of controls
        if any(keyword in query.lower() for keyword in ["list", "show", "get", "all"]):
            if any(keyword in query.lower() for keyword in ["controls", "control"]):
                # Return a list of all controls
                if not controls_data:
                    return "No controls found in the library."
                    
                controls_list = "# Available Controls\n\n"
                for control in controls_data:
                    controls_list += f"- **{control.get('id', 'Unknown')}**: {control.get('name', 'Unnamed control')}\n"
                
                return controls_list
        
        # Check if it's asking about a specific control ID
        match = re.search(r'CTRL-\d{3}', query)
        if match:
            control_id = match.group(0)
            # Find the specific control
            control = None
            for c in controls_data:
                if c.get("id") == control_id:
                    control = c
                    break
                    
            if control:
                return format_control_details(control)
            else:
                return f"Control {control_id} not found in the library."
        
        # Default: assume it's asking for a 5W analysis of a control described in the query
        logger.info("[Control Analysis] Performing 5Ws analysis in simple mode")
        result = analyze_control_5ws(query, None, llm, api_key)
        
        if result.get("error"):
            return f"Error during 5Ws analysis: {result['error']}"
            
        return format_5ws_analysis(result.get("analysis", {}))
        
    except Exception as e:
        logger.error(f"[Control Analysis] Error in simple mode: {str(e)}")
        return f"Error during control analysis: {str(e)}"

def analyze_control_5ws(control_description: str, control_data: Optional[Dict[str, Any]], 
                      llm: Optional[BaseChatModel], api_key: Optional[str]) -> Dict[str, Any]:
    """
    Performs 5W analysis (Who, What, When, Where, Why) on the provided control description.
    
    Args:
        control_description: Description of the control to analyze
        control_data: Optional control metadata
        llm: Language model instance to use
        api_key: API key for creating a new LLM if not provided
        
    Returns:
        Dictionary with the analysis results or error
    """
    try:
        # Create LLM if not provided
        if llm is None:
            try:
                if api_key is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        return {"error": "API key not provided and not found in environment"}
                
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", 
                    temperature=0.1,
                    anthropic_api_key=api_key
                )
            except Exception as e:
                error_msg = f"Failed to create LLM: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg}
        
        # Prepare prompt
        prompt = f"""You are an expert in control analysis using the 5Ws framework. 
Please analyze the following control description:

CONTROL: {control_description}

Apply the 5Ws framework systematically:
1. WHO: Which roles/people are involved in executing or supervising this control?
2. WHAT: What specific actions are performed as part of this control?
3. WHEN: When is this control performed (frequency, timing, triggers)?
4. WHERE: Where is this control applied (systems, locations, environments)?
5. WHY: Why is this control important (risks addressed, objectives protected)?

For each W, provide:
- Analysis: Detailed findings based on the control description
- Gap: Identify any missing information or potential weaknesses
- Improvement: Recommend how to address each gap

Format your analysis as a detailed structured JSON:
{{
  "who": {{
    "analysis": "string",
    "gap": "string",
    "improvement": "string"
  }},
  "what": {{
    "analysis": "string", 
    "gap": "string",
    "improvement": "string"
  }},
  "when": {{
    "analysis": "string",
    "gap": "string",
    "improvement": "string"
  }},
  "where": {{
    "analysis": "string",
    "gap": "string",
    "improvement": "string"
  }},
  "why": {{
    "analysis": "string",
    "gap": "string",
    "improvement": "string"
  }}
}}

Provide a complete, thorough analysis for each of the 5Ws. For elements not explicitly mentioned in the control description, identify this as a gap and suggest an appropriate improvement.
"""
        
        # Get response
        response = llm.invoke(prompt)
        
        # Extract JSON
        result_text = response.content.strip()
        
        # Try different methods to extract JSON
        if "```json" in result_text:
            json_str = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            json_str = result_text.split("```")[1].strip()
        else:
            # Try to find JSON object by looking for first { and last }
            start_idx = result_text.find('{')
            end_idx = result_text.rfind('}')
            if start_idx >= 0 and end_idx > start_idx:
                json_str = result_text[start_idx:end_idx+1]
            else:
                json_str = result_text
        
        # Parse the JSON
        analysis = json.loads(json_str)
        
        return {"analysis": analysis}
        
    except json.JSONDecodeError as e:
        logger.error(f"[Control Analysis] Error parsing 5Ws analysis JSON: {str(e)}")
        return {"error": f"Error parsing 5Ws analysis: {str(e)}"}
    except Exception as e:
        logger.error(f"[Control Analysis] Error during 5Ws analysis: {str(e)}")
        return {"error": f"Error during 5Ws analysis: {str(e)}"}

def format_control_details(control_data: Dict[str, Any]) -> str:
    """Format control details into a readable string."""
    if not control_data:
        return "No control data provided."
    
    # Basic details
    formatted = f"# Control: {control_data.get('id', 'Unknown ID')}\n\n"
    formatted += f"**Name**: {control_data.get('name', 'Unnamed control')}\n"
    formatted += f"**Type**: {control_data.get('type', 'Not specified')}\n"
    formatted += f"**Category**: {control_data.get('category', 'Not specified')}\n"
    formatted += f"**Owner**: {control_data.get('owner', 'Not specified')}\n"
    formatted += f"**Status**: {control_data.get('status', 'Not specified')}\n\n"
    
    # Description
    if control_data.get('description'):
        formatted += f"## Description\n\n{control_data.get('description')}\n\n"
    
    # Objectives
    if control_data.get('objectives'):
        formatted += f"## Objectives\n\n"
        objectives = control_data.get('objectives')
        if isinstance(objectives, list):
            for obj in objectives:
                formatted += f"- {obj}\n"
        else:
            formatted += str(objectives)
        formatted += "\n\n"
    
    # Risks addressed
    if control_data.get('risks'):
        formatted += f"## Risks Addressed\n\n"
        risks = control_data.get('risks')
        if isinstance(risks, list):
            for risk in risks:
                formatted += f"- {risk}\n"
        else:
            formatted += str(risks)
        formatted += "\n\n"
    
    return formatted.strip()

def format_5ws_analysis(analysis: Dict[str, Any]) -> str:
    """Format 5Ws analysis results into a readable string."""
    if not analysis:
        return "No analysis results provided."
    
    formatted = "## 5Ws ANALYSIS\n\n"
    
    for w in ["who", "what", "when", "where", "why"]:
        w_data = analysis.get(w, {})
        formatted += f"### {w.upper()}\n"
        
        if w_data.get('analysis'):
            formatted += f"Analysis: {w_data.get('analysis')}\n"
        
        if w_data.get('gap'):
            formatted += f"Gap: {w_data.get('gap')}\n"
            
        if w_data.get('improvement'):
            formatted += f"Improvement: {w_data.get('improvement')}\n"
            
        formatted += "\n"
    
    return formatted.strip()

def format_test_script(test_script: Dict[str, Any]) -> str:
    """Format operational effectiveness test script into a readable string."""
    if not test_script:
        return "No test script provided."
    
    formatted = ""
    
    if test_script.get('setup'):
        formatted += f"### Test Setup\n{test_script.get('setup')}\n\n"
        
    if test_script.get('steps'):
        formatted += f"### Test Steps\n"
        steps = test_script.get('steps')
        if isinstance(steps, list):
            for i, step in enumerate(steps, 1):
                formatted += f"{i}. {step}\n"
        else:
            formatted += str(steps)
        formatted += "\n\n"
        
    if test_script.get('success_criteria'):
        formatted += f"### Success Criteria\n{test_script.get('success_criteria')}\n\n"
        
    if test_script.get('evidence'):
        formatted += f"### Evidence to Collect\n{test_script.get('evidence')}\n\n"
    
    return formatted.strip()

def format_design_evaluation(assessment: Dict[str, Any]) -> str:
    """Format design effectiveness evaluation into a readable string."""
    if not assessment:
        return "No design evaluation provided."
    
    formatted = ""
    
    if assessment.get('strengths'):
        formatted += f"### Design Strengths\n"
        strengths = assessment.get('strengths')
        if isinstance(strengths, list):
            for strength in strengths:
                formatted += f"- {strength}\n"
        else:
            formatted += str(strengths)
        formatted += "\n\n"
        
    if assessment.get('weaknesses'):
        formatted += f"### Design Weaknesses\n"
        weaknesses = assessment.get('weaknesses')
        if isinstance(weaknesses, list):
            for weakness in weaknesses:
                formatted += f"- {weakness}\n"
        else:
            formatted += str(weaknesses)
        formatted += "\n\n"
        
    if assessment.get('recommendations'):
        formatted += f"### Recommendations\n"
        recommendations = assessment.get('recommendations')
        if isinstance(recommendations, list):
            for rec in recommendations:
                formatted += f"- {rec}\n"
        else:
            formatted += str(recommendations)
        formatted += "\n\n"
        
    if assessment.get('rating'):
        formatted += f"### Overall Rating\n{assessment.get('rating')}\n\n"
    
    return formatted.strip()

def generate_operational_effectiveness_script(control_description: str, control_data: Optional[Dict[str, Any]],
                                           llm: Optional[BaseChatModel], api_key: Optional[str]) -> Dict[str, Any]:
    """Generate a test script for evaluating operational effectiveness of a control"""
    logger.info(f"[Control Analysis] Generating operational effectiveness test script")
    
    try:
        # Create LLM if not provided
        if llm is None:
            try:
                if api_key is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        return {"error": "API key not provided and not found in environment", "test_script": None}
                
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", 
                    temperature=0.1,
                    anthropic_api_key=api_key
                )
                logger.info("[Control Analysis] Created new LLM instance for test script generation")
            except Exception as e:
                error_msg = f"[Control Analysis] Failed to create LLM for test script generation: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg, "test_script": None}
        
        # Construct the prompt for test script generation
        prompt = f"""Generate a comprehensive operational effectiveness test script for the following control:

CONTROL DESCRIPTION:
{control_description}

Your test script should follow auditing best practices and be structured to thoroughly test if the control is operating as designed.
Provide your test script in the following JSON format:

{{
  "setup": "Brief description of test preparation and requirements",
  "steps": [
    "Step 1: Detailed description of first test step",
    "Step 2: Detailed description of second test step",
    "Step 3: Detailed description of third test step"
  ],
  "success_criteria": "Description of what constitutes successful control operation",
  "evidence": "Description of evidence to collect during testing"
}}

Ensure the test script:
1. Is comprehensive and covers all aspects of the control
2. Includes specific, detailed steps that can be followed by an auditor
3. Has clear success criteria
4. Specifies what evidence should be collected"""

        # Get the LLM response
        response = llm.invoke(prompt)
        
        # Extract the JSON response
        if hasattr(response, 'content'):
            raw_content = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()
        else:
            raw_content = str(response).strip()
            
        # Extract JSON part
        if "```json" in raw_content:
            json_str = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            json_str = raw_content.split("```")[1].strip()
        else:
            # Try to find JSON object by looking for first { and last }
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}')
            if start_idx >= 0 and end_idx > start_idx:
                json_str = raw_content[start_idx:end_idx+1]
            else:
                json_str = raw_content
            
        try:
            test_script = json.loads(json_str)
            return {"error": None, "test_script": test_script}
        except json.JSONDecodeError:
            error_msg = f"Error parsing LLM response: Invalid JSON format"
            logger.error(error_msg)
            return {"error": error_msg, "test_script": None}
            
    except Exception as e:
        error_msg = f"Error generating test script: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "test_script": None}

def evaluate_design_effectiveness(control_description: str, control_data: Optional[Dict[str, Any]],
                               llm: Optional[BaseChatModel], api_key: Optional[str]) -> Dict[str, Any]:
    """Evaluate the design effectiveness of a control"""
    logger.info(f"[Control Analysis] Evaluating design effectiveness")
    
    try:
        # Create LLM if not provided
        if llm is None:
            try:
                if api_key is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        return {"error": "API key not provided and not found in environment", "assessment": None}
                
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", 
                    temperature=0.1,
                    anthropic_api_key=api_key
                )
                logger.info("[Control Analysis] Created new LLM instance for design evaluation")
            except Exception as e:
                error_msg = f"[Control Analysis] Failed to create LLM for design evaluation: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg, "assessment": None}
        
        # Construct the prompt for design effectiveness evaluation
        prompt = f"""Evaluate the design effectiveness of the following control:

CONTROL DESCRIPTION:
{control_description}

Assess the design of this control and provide your evaluation in the following JSON format:

{{
  "strengths": [
    "Strength 1",
    "Strength 2",
    "Strength 3"
  ],
  "weaknesses": [
    "Weakness 1",
    "Weakness 2"
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    "Recommendation 3"
  ],
  "rating": "A brief overall rating of the control's design effectiveness"
}}

Ensure your evaluation is:
1. Objective and based on control design best practices
2. Specific to this particular control
3. Actionable with clear recommendations for improvement"""

        # Get the LLM response
        response = llm.invoke(prompt)
        
        # Extract the JSON response
        if hasattr(response, 'content'):
            raw_content = response.content.strip() if isinstance(response.content, str) else str(response.content).strip()
        else:
            raw_content = str(response).strip()
            
        # Extract JSON part
        if "```json" in raw_content:
            json_str = raw_content.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_content:
            json_str = raw_content.split("```")[1].strip()
        else:
            # Try to find JSON object by looking for first { and last }
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}')
            if start_idx >= 0 and end_idx > start_idx:
                json_str = raw_content[start_idx:end_idx+1]
            else:
                json_str = raw_content
            
        try:
            # Clean up any comments in the JSON
            json_str = re.sub(r'//.*?\n', '\n', json_str)
            assessment = json.loads(json_str)
            return {"error": None, "assessment": assessment}
        except json.JSONDecodeError:
            error_msg = f"Error parsing LLM response: Invalid JSON format"
            logger.error(error_msg)
            return {"error": error_msg, "assessment": None}
            
    except Exception as e:
        error_msg = f"Error evaluating design effectiveness: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "assessment": None}

class ControlNotFoundException(Exception):
    """Raised when a requested control is not found."""
    pass 
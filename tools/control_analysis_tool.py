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
    
    # Create a prompt to understand what the user wants
    prompt = f"""Analyze this user query about controls and help determine how to respond:

USER QUERY: {query}

Available controls:
{json.dumps(controls_data, indent=2)}

What is the user asking for? Select ONE of these options:
1. Information about existing controls or listing controls
2. Analyzing a control using 5Ws framework
3. Generating a test script for operational effectiveness
4. Evaluating design effectiveness
5. Multiple analyses on a specific control
6. Something else (specify)

Return your answer as a single number (1-6).
"""
    response = llm.invoke(prompt)
    option = response.content.strip()
    
    # Try to extract just the number
    option_num = ''.join(char for char in option if char.isdigit())
    if option_num:
        option = option_num[0] if option_num else "6"
    
    if option == "1":
        # Show control info
        return fetch_controls_info(query, llm, None)
    elif option == "2":
        # Do 5Ws analysis
        result = analyze_control_5ws(query, None, llm, api_key)
        if result.get("error"):
            return f"Error in 5Ws analysis: {result['error']}"
        else:
            return f"## 5Ws ANALYSIS\n\n{format_5ws_analysis(result.get('analysis', {}))}"
    elif option == "3":
        # Generate test script
        result = generate_operational_effectiveness_script(query, None, llm, api_key)
        if result.get("error"):
            return f"Error generating test script: {result['error']}"
        else:
            return f"## OPERATIONAL EFFECTIVENESS TEST SCRIPT\n\n{format_test_script(result.get('test_script', {}))}"
    elif option == "4":
        # Evaluate design
        result = evaluate_design_effectiveness(query, None, llm, api_key)
        if result.get("error"):
            return f"Error evaluating design: {result['error']}"
        else:
            return f"## DESIGN EFFECTIVENESS EVALUATION\n\n{format_design_evaluation(result.get('assessment', {}))}"
    elif option == "5":
        # Do all analyses
        result_5ws = analyze_control_5ws(query, None, llm, api_key)
        result_oe = generate_operational_effectiveness_script(query, None, llm, api_key)
        result_de = evaluate_design_effectiveness(query, None, llm, api_key)
        
        combined = "## 5Ws ANALYSIS\n\n"
        combined += format_5ws_analysis(result_5ws.get("analysis", {})) if not result_5ws.get("error") else f"Error: {result_5ws.get('error')}"
        combined += "\n\n## OPERATIONAL EFFECTIVENESS TEST SCRIPT\n\n"
        combined += format_test_script(result_oe.get("test_script", {})) if not result_oe.get("error") else f"Error: {result_oe.get('error')}"
        combined += "\n\n## DESIGN EFFECTIVENESS EVALUATION\n\n"
        combined += format_design_evaluation(result_de.get("assessment", {})) if not result_de.get("error") else f"Error: {result_de.get('error')}"
        
        return combined
    else:
        # Just use fetch_controls_info as a fallback
        return fetch_controls_info(query, llm, None)

def fetch_control(control_id: str, controls_path: Optional[str] = None) -> Dict[str, Any]:
    """Fetch a specific control by ID.
    
    Args:
        control_id: The ID of the control to fetch
        controls_path: Optional path to the controls.json file
        
    Returns:
        Dict containing control details
        
    Raises:
        ControlNotFoundException: If control with specified ID is not found
    """
    logger.info(f"[Control Analysis] Fetching control with ID: {control_id}")
    
    # Use default path if not provided
    if controls_path is None:
        controls_path = DEFAULT_CONTROLS_PATH
    
    try:
        # Check if file exists
        if not os.path.exists(controls_path):
            raise ControlNotFoundException(f"Controls file not found at {controls_path}")
        
        # Read and parse JSON file
        with open(controls_path, 'r') as f:
            controls_data = json.load(f)
            
        # Extract controls array
        controls = controls_data.get("controls", [])
        
        # Find control with matching ID
        for control in controls:
            if control.get("id") == control_id:
                logger.info(f"[Control Analysis] Found control: {control.get('name', 'Unnamed')}")
                return control
                
        # If we get here, control was not found
        raise ControlNotFoundException(f"Control with ID {control_id} not found in controls file")
        
    except json.JSONDecodeError:
        raise ControlNotFoundException(f"Invalid JSON format in controls file at {controls_path}")
    except Exception as e:
        if isinstance(e, ControlNotFoundException):
            raise
        raise ControlNotFoundException(f"Error fetching control: {str(e)}")

def fetch_controls_info(query: str, llm: BaseChatModel, controls_path: Optional[str] = None) -> str:
    """
    Loads all controls and has the LLM answer questions about them.
    
    Args:
        query: The user's query about controls
        llm: LLM to use for answering
        controls_path: Optional path to the controls.json file
        
    Returns:
        String with the answer about controls
    """
    logger.info(f"[Control Analysis] Processing controls info query: {query}")
    
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
        
        # Format the controls data for the prompt
        controls_info = json.dumps(controls, indent=2)
        
        # Create a prompt for the LLM to answer questions about the controls
        prompt = f"""You are helping answer questions about control information from a controls repository.
Here is the available control data:

{controls_info}

User question: {query}

Please answer the question accurately based on the control data provided above. Be conversational and helpful.

You can answer questions about any aspect of the controls including:
- IDs and names of controls
- Descriptions
- Types (Preventative, Detective, etc.)
- Categories
- Owners
- Status
- Comparisons between controls
- Filtering controls by any attribute
- Counting controls meeting certain criteria
- Listing all controls or specific controls
- Finding controls with specific characteristics

If the user asks for controls of a certain type, with a specific owner, or meeting any other criteria, provide all matching controls.
If the answer can be presented in a structured way, do so to improve readability.
"""
        
        # Get LLM response
        response = llm.invoke(prompt)
        
        if hasattr(response, 'content'):
            return response.content.strip()
        else:
            return str(response).strip()
            
    except json.JSONDecodeError:
        return f"Error: Invalid JSON format in controls file at {controls_path}"
    except Exception as e:
        logger.error(f"[Control Analysis] Error fetching controls info: {str(e)}")
        return f"Error retrieving control information: {str(e)}"

def analyze_control_5ws(control_description: str, control_data: Optional[Dict[str, Any]], 
                      llm: Optional[BaseChatModel], api_key: Optional[str]) -> Dict[str, Any]:
    """Analyze a control description using the 5Ws framework"""
    logger.info(f"[Control Analysis] Running 5Ws analysis on control description")
    
    try:
        # Create LLM if not provided
        if llm is None:
            try:
                if api_key is None:
                    api_key = os.getenv("ANTHROPIC_API_KEY")
                    if not api_key:
                        return {"error": "API key not provided and not found in environment", "analysis": None}
                
                llm = ChatAnthropic(
                    model="claude-3-5-sonnet-20240620", 
                    temperature=0.1,
                    anthropic_api_key=api_key
                )
                logger.info("[Control Analysis] Created new LLM instance for 5Ws analysis")
            except Exception as e:
                error_msg = f"[Control Analysis] Failed to create LLM for 5Ws analysis: {str(e)}"
                logger.error(error_msg)
                return {"error": error_msg, "analysis": None}
        
        # Construct the prompt for 5Ws analysis
        prompt = f"""Analyze the following control description using the 5Ws framework (Who, What, When, Where, Why).
For each dimension, identify any gaps or missing information and suggest improvements.

CONTROL DESCRIPTION:
{control_description}

Provide your analysis in the following JSON format:
{{
  "who": {{
    "analysis": "Your analysis of who is responsible...",
    "gap": "Identified gap in the who aspect, or null if none",
    "improvement": "Suggested improvement for the who aspect, or null if none"
  }},
  "what": {{
    "analysis": "Your analysis of what the control does...",
    "gap": "Identified gap in the what aspect, or null if none",
    "improvement": "Suggested improvement for the what aspect, or null if none"
  }},
  "when": {{
    "analysis": "Your analysis of when the control is executed...",
    "gap": "Identified gap in the when aspect, or null if none",
    "improvement": "Suggested improvement for the when aspect, or null if none"
  }},
  "where": {{
    "analysis": "Your analysis of where the control operates...",
    "gap": "Identified gap in the where aspect, or null if none", 
    "improvement": "Suggested improvement for the where aspect, or null if none"
  }},
  "why": {{
    "analysis": "Your analysis of why the control exists...",
    "gap": "Identified gap in the why aspect, or null if none",
    "improvement": "Suggested improvement for the why aspect, or null if none"
  }},
  "overall_assessment": "Summary assessment of the control's overall effectiveness and completeness",
  "priority_improvements": ["List of 1-3 highest priority improvements"]
}}

Ensure all gaps and improvements are specific, actionable, and directly related to the control description."""

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
            json_str = raw_content
            
        try:
            analysis = json.loads(json_str)
            return {"error": None, "analysis": analysis}
        except json.JSONDecodeError:
            error_msg = f"Error parsing LLM response: Invalid JSON format"
            logger.error(error_msg)
            return {"error": error_msg, "analysis": None}
            
    except Exception as e:
        error_msg = f"Error during 5Ws analysis: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg, "analysis": None}

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
  "test_objective": "Clear statement of what the test aims to verify",
  "scope": "Scope of the test, including timeframe and systems covered",
  "sampling_approach": "Description of sampling methodology and rationale",
  "prerequisites": ["List of required items, access, or documents needed before testing"],
        "test_steps": [
    {{
      "step_number": 1,
      "description": "Detailed description of what to do in this step",
      "expected_result": "What should be observed if the control is operating effectively"
    }},
    ...additional steps...
  ],
  "evidence_collection": ["Types of evidence that should be collected during testing"],
  "evaluation_criteria": ["Specific criteria to determine if the control is operating effectively"],
  "potential_exceptions": ["Common exceptions or issues that might be identified"],
  "reporting_guidance": "How to report and document findings"
}}

Ensure the test script:
1. Is comprehensive and covers all aspects of the control
2. Includes specific, detailed steps that can be followed by an auditor
3. Has clear expected results for each step
4. Is practical and realistic to implement"""

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

Assess the design of this control across these key dimensions:
- Control objective: Is the objective clear and appropriate?
- Control type: Is this the right type of control (preventive, detective, corrective)?
- Coverage: Does it address all relevant risks?
- Precision: Is it specific and targeted?
- Frequency: Is it performed at the right intervals?
- Responsibility: Is ownership clearly assigned?
- Automation: Is the right level of automation applied?
- Documentation: Is the control well-documented?
- Management review: Is there proper oversight?

Provide your evaluation in the following JSON format:

{{
  "control_objective": {{
    "assessment": "Assessment of the control objective",
    "score": 4, // Score from 1-5 where 5 is best
    "recommendation": "Recommendation to improve if needed"
  }},
  "control_type": {{
    "assessment": "Assessment of control type appropriateness",
    "score": 3,
    "recommendation": "Recommendation to improve if needed"
  }},
  "coverage": {{
    "assessment": "Assessment of risk coverage",
    "score": 4,
    "recommendation": "Recommendation to improve if needed"
  }},
  "precision": {{
    "assessment": "Assessment of control precision",
    "score": 3,
    "recommendation": "Recommendation to improve if needed"
  }},
  "frequency": {{
    "assessment": "Assessment of control frequency",
    "score": 4,
    "recommendation": "Recommendation to improve if needed"
  }},
  "responsibility": {{
    "assessment": "Assessment of responsibility assignment",
    "score": 5,
    "recommendation": "Recommendation to improve if needed"
  }},
  "automation": {{
    "assessment": "Assessment of automation level",
    "score": 2,
    "recommendation": "Recommendation to improve if needed"
  }},
  "documentation": {{
    "assessment": "Assessment of documentation quality",
    "score": 3,
    "recommendation": "Recommendation to improve if needed"
  }},
  "management_review": {{
    "assessment": "Assessment of management review",
    "score": 4,
    "recommendation": "Recommendation to improve if needed"
  }},
  "overall_design": {{
    "assessment": "Overall assessment of design effectiveness",
    "score": 3,
    "recommendation": "Overall recommendation"
  }},
  "summary": {{
            "average_score": 3.5,
    "strengths": ["Key strength 1", "Key strength 2", "Key strength 3"],
    "weaknesses": ["Key weakness 1", "Key weakness 2"],
    "priority_improvements": ["Priority improvement 1", "Priority improvement 2"]
  }}
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

def generate_executive_summary(control_description: str, analysis_5ws: Optional[Dict], 
                            test_script: Optional[Dict], design_assessment: Optional[Dict],
                            llm: Optional[BaseChatModel], api_key: Optional[str]) -> str:
    """Generate an executive summary of all analyses"""
    # Placeholder implementation - will be replaced with actual implementation
    return """
    This control was evaluated across three dimensions: 5Ws framework analysis, operational effectiveness testing, and design effectiveness.
    
    Key findings:
    - The control shows strengths in clearly defined responsibilities and automation
    - Improvement areas include documentation and frequency of execution
    - The overall design is rated 3.5/5, indicating moderate effectiveness
    - Priority recommendations focus on enhancing documentation and clarifying execution procedures
    """

def format_control_details(control_data: Dict[str, Any]) -> str:
    """Format control details for output"""
    if not control_data:
        return "Control details not available."
        
    result = ""
    result += f"ID: {control_data.get('id', 'Unknown')}\n"
    result += f"Name: {control_data.get('name', 'Unknown')}\n"
    
    if desc := control_data.get('description'):
        result += f"Description: {desc}\n"
    
    if owner := control_data.get('owner'):
        result += f"Owner: {owner}\n"
    
    if ctrl_type := control_data.get('type'):
        result += f"Type: {ctrl_type}\n"
    
    if category := control_data.get('category'):
        result += f"Category: {category}\n"
    
    if freq := control_data.get('frequency'):
        result += f"Frequency: {freq}\n"
    
    if status := control_data.get('status'):
        result += f"Status: {status}\n"
    
    if risk := control_data.get('risk_category'):
        result += f"Risk Category: {risk}\n"
        
    # Add any other attributes that might be present
    for key, value in control_data.items():
        if key not in ['id', 'name', 'description', 'owner', 'type', 'category', 'frequency', 'status', 'risk_category']:
            if isinstance(value, (str, int, float, bool)):
                result += f"{key.title()}: {value}\n"
    
    return result

def format_5ws_analysis(analysis: Dict[str, Any]) -> str:
    """Format 5Ws analysis for output"""
    # Placeholder implementation - will be replaced with actual implementation
    result = ""
    
    # Add each dimension
    for dimension in ["who", "what", "when", "where", "why"]:
        dim_data = analysis.get(dimension, {})
        result += f"### {dimension.upper()}\n"
        result += f"Analysis: {dim_data.get('analysis', 'Not analyzed')}\n"
        
        if gap := dim_data.get('gap'):
            result += f"Gap: {gap}\n"
            
        if improvement := dim_data.get('improvement'):
            result += f"Improvement: {improvement}\n"
            
        result += "\n"
    
    # Add overall assessment
    result += f"### OVERALL ASSESSMENT\n{analysis.get('overall_assessment', 'No overall assessment provided.')}\n\n"
    
    # Add priority improvements
    result += "### PRIORITY IMPROVEMENTS\n"
    for improvement in analysis.get("priority_improvements", []):
        result += f"- {improvement}\n"
        
    return result

def format_test_script(test_script: Dict[str, Any]) -> str:
    """Format test script for output"""
    # Placeholder implementation - will be replaced with actual implementation
    result = f"Test Objective: {test_script.get('test_objective', 'Not specified')}\n\n"
    result += f"Scope: {test_script.get('scope', 'Not specified')}\n\n"
    result += f"Sampling Approach: {test_script.get('sampling_approach', 'Not specified')}\n\n"
    
    # Prerequisites
    result += "### PREREQUISITES\n"
    for prereq in test_script.get("prerequisites", []):
        result += f"- {prereq}\n"
    result += "\n"
    
    # Test steps
    result += "### TEST STEPS\n"
    for step in test_script.get("test_steps", []):
        result += f"{step.get('step_number', '?')}. {step.get('description', 'No description')}\n"
        result += f"   Expected Result: {step.get('expected_result', 'Not specified')}\n\n"
    
    return result

def format_design_evaluation(assessment: Dict[str, Any]) -> str:
    """Format design evaluation for output"""
    # Placeholder implementation - will be replaced with actual implementation
    result = ""
    
    # Add dimension assessments
    dimensions = [
        "control_objective", "control_type", "coverage", "precision", 
        "frequency", "responsibility", "automation", "documentation", 
        "management_review", "overall_design"
    ]
    
    for dimension in dimensions:
        if dimension in assessment:
            dim_data = assessment.get(dimension, {})
            result += f"### {dimension.upper().replace('_', ' ')}\n"
            result += f"Assessment: {dim_data.get('assessment', 'Not assessed')}\n"
            result += f"Score: {dim_data.get('score', 'N/A')}/5\n"
            
            if recommendation := dim_data.get('recommendation'):
                result += f"Recommendation: {recommendation}\n"
                
            result += "\n"
    
    # Add summary if it exists
    if "summary" in assessment:
        summary = assessment["summary"]
        result += "### SUMMARY\n"
        result += f"Average Score: {summary.get('average_score', 'Not calculated')}/5\n\n"
        
        if "strengths" in summary:
            result += "Strengths:\n"
            for strength in summary["strengths"]:
                result += f"- {strength}\n"
            result += "\n"
            
        if "weaknesses" in summary:
            result += "Weaknesses:\n"
            for weakness in summary["weaknesses"]:
                result += f"- {weakness}\n"
            result += "\n"
            
        if "priority_improvements" in summary:
            result += "Priority Improvements:\n"
            for improvement in summary["priority_improvements"]:
                result += f"- {improvement}\n"
    
    return result

class ControlNotFoundException(Exception):
    """Custom exception for when a control isn't found"""
    pass

# This file will be completed with the full implementation of all tools 
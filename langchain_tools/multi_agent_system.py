"""
Multi-Agent Collaboration System for hierarchical information retrieval.
Implements a team of specialized agents working together to analyze information.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from langchain_anthropic import ChatAnthropic
from langchain.tools import Tool

from . import agent_config
from . import config as tool_config
from .tool1_department import get_tool as get_department_tool
from .tool2_category import get_tool as get_category_tool
from .tool3_document import get_tool as get_document_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SharedState:
    """Shared state/scratchpad for agent collaboration."""
    # Original query
    query: str
    # Current category being analyzed
    current_category: Optional[str] = None
    # Current document IDs being analyzed
    current_doc_ids: List[str] = None
    # Collected evidence
    evidence: List[str] = None
    # Analysis results from each agent
    department_analysis: Dict[str, Any] = None
    category_analysis: Dict[str, Any] = None
    document_analysis: Dict[str, Any] = None
    # Final synthesized answer
    final_answer: str = ""
    # Agent messages for coordination
    messages: List[Dict[str, str]] = None
    
    def __post_init__(self):
        """Initialize optional fields."""
        if self.current_doc_ids is None:
            self.current_doc_ids = []
        if self.evidence is None:
            self.evidence = []
        if self.messages is None:
            self.messages = []
    
    def add_message(self, agent_name: str, message: str):
        """Add a message to the collaboration log."""
        self.messages.append({
            "agent": agent_name,
            "message": message
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return asdict(self)

class BaseAgent:
    """Base class for specialized agents."""
    
    def __init__(self, name: str, llm: ChatAnthropic):
        self.name = name
        self.llm = llm
    
    def analyze(self, state: SharedState) -> SharedState:
        """Run agent's analysis on shared state."""
        raise NotImplementedError
    
    def _log_progress(self, message: str, state: SharedState):
        """Log progress and add to shared state."""
        logger.debug(f"{self.name}: {message}")
        state.add_message(self.name, message)

class DepartmentAgent(BaseAgent):
    """Agent specialized in department-level analysis."""
    
    def __init__(self, llm: ChatAnthropic, tool: Tool):
        super().__init__("DepartmentAgent", llm)
        self.tool = tool
    
    def analyze(self, state: SharedState) -> SharedState:
        """Analyze at department level and identify relevant categories."""
        try:
            self._log_progress("Starting department analysis", state)
            
            # Use department tool
            result = self.tool.func(state.query)
            
            # Log the raw result for debugging
            logger.debug(f"Department tool raw result: {result}")
            
            # Update state
            state.department_analysis = result
            state.current_category = result.get("category")
            
            self._log_progress(
                f"Completed analysis. Identified category: {state.current_category}",
                state
            )
            
            return state
        except Exception as e:
            logger.error(f"Error in department analysis: {e}")
            self._log_progress(f"Error: {str(e)}", state)
            return state

class CategoryAgent(BaseAgent):
    """Agent specialized in category-level analysis."""
    
    def __init__(self, llm: ChatAnthropic, tool: Tool):
        super().__init__("CategoryAgent", llm)
        self.tool = tool
    
    def analyze(self, state: SharedState) -> SharedState:
        """Analyze at category level and identify relevant documents."""
        try:
            if not state.current_category:
                self._log_progress("No category identified. Skipping analysis.", state)
                return state
            
            self._log_progress(f"Starting analysis for category: {state.current_category}", state)
            
            # Extract the category ID from current_category
            # Split by common separators and take the first valid ticker
            categories = state.current_category.split(',')
            category_id = categories[0].strip()
            
            # Log the category ID being used
            logger.debug(f"Using category ID: {category_id} for analysis")
            
            # Use category tool with proper category ID
            result = self.tool.func(state.query, category_id)
            
            # Log the raw result for debugging
            logger.debug(f"Category tool raw result: {result}")
            
            # Update state
            state.category_analysis = result
            state.current_doc_ids = result.get("document_ids", [])
            
            self._log_progress(
                f"Completed analysis. Found {len(state.current_doc_ids)} relevant documents with IDs: {state.current_doc_ids}",
                state
            )
            
            return state
        except Exception as e:
            logger.error(f"Error in category analysis: {e}")
            self._log_progress(f"Error: {str(e)}", state)
            return state

class DocumentAgent(BaseAgent):
    """Agent specialized in document-level analysis."""
    
    def __init__(self, llm: ChatAnthropic, tool: Tool):
        super().__init__("DocumentAgent", llm)
        self.tool = tool
    
    def analyze(self, state: SharedState) -> SharedState:
        """Analyze specific documents to find evidence."""
        try:
            if not state.current_doc_ids:
                self._log_progress("No documents identified. Skipping analysis.", state)
                return state
            
            self._log_progress(f"Starting analysis of {len(state.current_doc_ids)} documents", state)
            logger.debug(f"Analyzing documents with IDs: {state.current_doc_ids}")
            
            # Use document tool with proper document IDs
            result = self.tool.func(state.query, doc_ids=state.current_doc_ids)
            
            # Log the raw result for debugging
            logger.debug(f"Document tool raw result: {result}")
            
            # Update state
            state.document_analysis = result
            if isinstance(result, dict):
                state.evidence = result.get("evidence", [])
            
            self._log_progress(
                f"Completed analysis. Found {len(state.evidence)} pieces of evidence",
                state
            )
            
            return state
        except Exception as e:
            logger.error(f"Error in document analysis: {e}")
            self._log_progress(f"Error: {str(e)}", state)
            return state

class SynthesisAgent(BaseAgent):
    """Agent specialized in synthesizing results from other agents."""
    
    def __init__(self, llm: ChatAnthropic):
        super().__init__("SynthesisAgent", llm)
    
    def analyze(self, state: SharedState) -> SharedState:
        """Synthesize results from all analysis levels."""
        try:
            self._log_progress("Starting synthesis of all analysis results", state)
            
            # Create synthesis prompt
            prompt = self._create_synthesis_prompt(state)
            
            # Generate synthesis using LLM
            response = self.llm.invoke(prompt)
            
            # Update state
            state.final_answer = response.content
            
            self._log_progress("Completed synthesis", state)
            
            return state
        except Exception as e:
            logger.error(f"Error in synthesis: {e}")
            self._log_progress(f"Error: {str(e)}", state)
            return state
    
    def _create_synthesis_prompt(self, state: SharedState) -> str:
        """Create a prompt for synthesizing results."""
        return f"""Synthesize the following analysis results into a clear, comprehensive answer.

Query: {state.query}

Department Level Analysis:
{json.dumps(state.department_analysis, indent=2) if state.department_analysis else "No department analysis available"}

Category Level Analysis:
{json.dumps(state.category_analysis, indent=2) if state.category_analysis else "No category analysis available"}

Document Level Analysis:
{json.dumps(state.document_analysis, indent=2) if state.document_analysis else "No document analysis available"}

Evidence:
{json.dumps(state.evidence, indent=2) if state.evidence else "No evidence collected"}

Agent Collaboration Log:
{json.dumps(state.messages, indent=2)}

Based on all available information and the collaboration between agents, provide a clear, factual answer that synthesizes all findings.
"""

class MultiAgentSystem:
    """
    Coordinates multiple specialized agents working together on
    hierarchical information retrieval tasks.
    """
    
    def __init__(self, api_key: str, debug: bool = False):
        """Initialize the multi-agent system."""
        self.api_key = api_key
        self.debug = debug
        
        # Set up logging
        if debug:
            logger.setLevel(logging.DEBUG)
        
        # Initialize LLM
        self.llm = ChatAnthropic(
            api_key=api_key,
            model="claude-3-haiku-20240307"
        )
        
        # Initialize tools
        tools = self._initialize_tools()
        
        # Initialize specialized agents
        self.agents = [
            DepartmentAgent(self.llm, tools[0]),
            CategoryAgent(self.llm, tools[1]),
            DocumentAgent(self.llm, tools[2]),
            SynthesisAgent(self.llm)
        ]
    
    def _initialize_tools(self) -> List[Tool]:
        """Initialize the tool chain."""
        # Get tool instances
        department_tool = get_department_tool(self.api_key, self.debug)
        category_tool = get_category_tool(self.api_key)
        document_tool = get_document_tool(self.api_key)
        
        # Get tool descriptions
        descriptions = agent_config.get_tool_descriptions()
        
        # Create LangChain tool objects
        return [
            Tool(
                name="department_tool",
                func=department_tool,
                description=descriptions["department_tool"]
            ),
            Tool(
                name="category_tool",
                func=category_tool,
                description=descriptions["category_tool"]
            ),
            Tool(
                name="document_tool",
                func=document_tool,
                description=descriptions["document_tool"]
            )
        ]
    
    def query(self, query: str) -> Dict[str, Any]:
        """Run a query through the multi-agent system."""
        try:
            # Initialize shared state
            state = SharedState(query=query)
            
            # Run each agent in sequence
            for agent in self.agents:
                state = agent.analyze(state)
            
            # Format response
            return {
                "status": "success",
                "result": state.final_answer,
                "evidence": state.evidence,
                "collaboration_log": state.messages
            }
            
        except Exception as e:
            logger.error(f"Error running query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "evidence": [],
                "collaboration_log": []
            } 
"""
Structured logging for the Hierarchical Retrieval Agent.
"""

import logging
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Use the root logger configuration from the main entry point (e.g., agent.py)
logger = logging.getLogger(__name__) 

class AgentLogger:
    """Provides structured logging for agent activities."""

    def __init__(self, agent_id: str, initial_query: Optional[str] = None):
        """Initialize logger with agent ID and potentially a conversation ID."""
        self.agent_id = agent_id
        self.conversation_id = str(uuid.uuid4()) # New conversation ID for each agent instance
        self.initial_query = initial_query
        logger.info(f"Initialized AgentLogger for agent {agent_id}, conversation {self.conversation_id}")

    def start_query(self, query: str):
        """Log the start of a new query execution."""
        self.initial_query = query # Update query if a new one starts
        self.conversation_id = str(uuid.uuid4()) # Start a new conversation ID for a new query
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "event_type": "query_start",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "query": query,
        }
        logger.info(json.dumps(log_entry))

    def log_tool_call(self, tool_name: str, input_data: Dict, state_snapshot: Optional[Dict] = None):
        """Log the initiation of a tool call."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "event_type": "tool_call_start",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "tool_name": tool_name,
            "input": input_data,
            "state_snapshot_before": state_snapshot or {}
        }
        logger.info(json.dumps(log_entry))

    def log_tool_result(self, tool_name: str, output_data: Dict, state_snapshot: Optional[Dict] = None):
        """Log the result received from a tool call."""
        # Determine log level based on success/error in metadata
        success = output_data.get("metadata", {}).get("success", True)
        error_info = output_data.get("metadata", {}).get("error")
        level = "ERROR" if error_info or not success else "INFO"
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event_type": "tool_call_end",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "tool_name": tool_name,
            "output": output_data, # Contains answer, confidence, metadata etc.
            "state_snapshot_after": state_snapshot or {}
        }
        logger.log(logging.getLevelName(level), json.dumps(log_entry))

    def log_state_change(self, description: str, state_snapshot: Dict):
        """Log significant state changes."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "DEBUG", # State changes might be verbose, use DEBUG
            "event_type": "state_update",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "description": description,
            "state_snapshot": state_snapshot
        }
        logger.debug(json.dumps(log_entry))
        
    def log_agent_action(self, agent_action: Any):
        """Logs the action decided by the agent (AgentAction or AgentFinish)."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "DEBUG",
            "event_type": "agent_action",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "action_details": str(agent_action) # Convert action object to string for logging
        }
        logger.debug(json.dumps(log_entry))

    def end_query(self, final_response: Dict, state_snapshot: Dict):
        """Log the end of a query execution."""
        level = "ERROR" if final_response.get("status") == "error" else "INFO"
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "event_type": "query_end",
            "agent_id": self.agent_id,
            "conversation_id": self.conversation_id,
            "final_response": final_response,
            "final_state": state_snapshot
        }
        logger.log(logging.getLevelName(level), json.dumps(log_entry)) 
"""
Manages the state of the Hierarchical Retrieval Agent during query execution.
"""

import logging
from typing import Dict, Any, Set, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Data class to hold the agent's state during a single query execution."""
    pending_doc_ids: Set[str] = field(default_factory=set)
    processed_doc_ids: Set[str] = field(default_factory=set)
    current_confidence: float = 0.0
    evidence_collected: List[Dict] = field(default_factory=list)  # Store evidence dicts from document tool
    tool_sequence: List[str] = field(default_factory=list)      # Track names of tools used in order
    category_id: Optional[str] = None                           # Last identified category
    last_query: Optional[str] = None                            # Store the initial user query
    last_error: Optional[str] = None                            # Store the last error message

    def update_from_tool_result(self, tool_name: str, result: Dict) -> None:
        """Updates the state based on the output of a tool."""
        logger.debug(f"Updating state from {tool_name} result.")
        if not isinstance(result, dict):
            logger.warning(f"Tool {tool_name} result is not a dict: {result}")
            self.last_error = f"Tool {tool_name} returned non-dict result."
            return
            
        # Update confidence (take the max confidence seen so far? or last? Let's take max for now)
        new_confidence = result.get('confidence', self.current_confidence)
        if isinstance(new_confidence, (int, float)):
             self.current_confidence = max(self.current_confidence, float(new_confidence))
        
        # Add relevant doc IDs from category tool
        if tool_name == 'category_tool' and 'relevant_doc_ids' in result:
            new_ids = set(result['relevant_doc_ids'])
            self.pending_doc_ids.update(new_ids - self.processed_doc_ids) # Add only new, unprocessed IDs
            logger.info(f"Added {len(new_ids - self.processed_doc_ids)} new pending doc IDs: {list(new_ids - self.processed_doc_ids)}")

        # Update category from department tool
        if tool_name == 'department_tool' and 'category' in result:
             self.category_id = result['category']
             logger.info(f"Updated category_id to: {self.category_id}")

        # Add evidence from document tool
        if tool_name == 'document_tool' and 'evidence' in result:
            if isinstance(result['evidence'], list):
                self.evidence_collected.extend(result['evidence'])
                logger.info(f"Added {len(result['evidence'])} pieces of evidence. Total: {len(self.evidence_collected)}")
            # Mark doc IDs as processed
            processed = result.get('analyzed_doc_ids', [])
            if isinstance(processed, list):
                 self.processed_doc_ids.update(processed)
                 self.pending_doc_ids.difference_update(processed)
                 logger.info(f"Marked {len(processed)} doc IDs as processed: {processed}")
                 logger.info(f"Remaining pending doc IDs: {list(self.pending_doc_ids)}")

        # Log tool usage
        if tool_name not in self.tool_sequence:
            self.tool_sequence.append(tool_name)
            
        # Log errors from metadata if present
        if result.get("metadata", {}).get("error"):
            self.last_error = result["metadata"]["error"]
            logger.warning(f"Error captured from tool {tool_name}: {self.last_error}")

    def validate_state(self) -> Tuple[bool, List[str]]:
        """Validates the current state fields."""
        errors = []
        if not (0 <= self.current_confidence <= 10):
            errors.append(f"Invalid confidence score: {self.current_confidence}")
        if not isinstance(self.pending_doc_ids, set):
            errors.append("pending_doc_ids must be a set")
        if not isinstance(self.processed_doc_ids, set):
             errors.append("processed_doc_ids must be a set")
        if not isinstance(self.evidence_collected, list):
            errors.append("evidence_collected must be a list")
        if not isinstance(self.tool_sequence, list):
            errors.append("tool_sequence must be a list")
            
        # Check for overlap between pending and processed IDs
        overlap = self.pending_doc_ids.intersection(self.processed_doc_ids)
        if overlap:
            errors.append(f"Overlap detected between pending and processed doc IDs: {list(overlap)}")
            
        return len(errors) == 0, errors

    def reset(self) -> None:
        """Resets the state to default values for a new query."""
        self.pending_doc_ids = set()
        self.processed_doc_ids = set()
        self.current_confidence = 0.0
        self.evidence_collected = []
        self.tool_sequence = []
        self.category_id = None
        # Keep last_query if needed for context, or reset it too?
        # self.last_query = None # Decide if query context should persist across resets
        self.last_error = None
        logger.info("Agent state reset.") 
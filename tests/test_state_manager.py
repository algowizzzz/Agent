"""
Unit tests for the AgentState class.
"""

import pytest
from langchain_tools.state_manager import AgentState

def test_state_initialization():
    """Test default initial state values."""
    state = AgentState()
    assert state.pending_doc_ids == set()
    assert state.processed_doc_ids == set()
    assert state.current_confidence == 0.0
    assert state.evidence_collected == []
    assert state.tool_sequence == []
    assert state.category_id is None
    assert state.last_query is None
    assert state.last_error is None

def test_state_reset():
    """Test resetting the state."""
    state = AgentState()
    # Modify state
    state.pending_doc_ids = {'doc1'}
    state.processed_doc_ids = {'doc0'}
    state.current_confidence = 5.0
    state.evidence_collected = [{"text": "evidence1"}]
    state.tool_sequence = ['department_tool']
    state.category_id = 'AMZN'
    state.last_query = "test query"
    state.last_error = "some error"

    state.reset()

    # Verify reset values (last_query might be intentionally kept, check impl)
    assert state.pending_doc_ids == set()
    assert state.processed_doc_ids == set()
    assert state.current_confidence == 0.0
    assert state.evidence_collected == []
    assert state.tool_sequence == []
    assert state.category_id is None
    # assert state.last_query is None # Depending on desired reset behavior
    assert state.last_error is None

def test_update_from_department_tool():
    """Test state update from department tool result."""
    state = AgentState()
    result = {
        "thought": "Analyzed department.",
        "answer": "General tech trends...",
        "category": "MSFT",
        "confidence": 3.0,
        "metadata": {"success": True}
    }
    state.update_from_tool_result('department_tool', result)

    assert state.category_id == 'MSFT'
    assert state.current_confidence == 3.0
    assert 'department_tool' in state.tool_sequence

def test_update_from_category_tool():
    """Test state update from category tool result."""
    state = AgentState()
    state.processed_doc_ids = {'doc_old'} # Pre-existing processed doc
    result = {
        "thought": "Analyzed category MSFT.",
        "answer": "Specifics about MSFT...",
        "relevant_doc_ids": ['doc1', 'doc2', 'doc_old'],
        "confidence": 6.5,
        "metadata": {"success": True}
    }
    state.update_from_tool_result('category_tool', result)

    assert state.pending_doc_ids == {'doc1', 'doc2'} # doc_old should not be added
    assert state.current_confidence == 6.5
    assert 'category_tool' in state.tool_sequence

def test_update_from_document_tool():
    """Test state update from document tool result."""
    state = AgentState()
    state.pending_doc_ids = {'doc1', 'doc2', 'doc3'}
    result = {
        "thought": "Analyzed documents.",
        "answer": "Final answer based on docs.",
        "evidence": ["quote1 from doc1", "quote2 from doc2"],
        "confidence": 9.0,
        "analyzed_doc_ids": ['doc1', 'doc2'], # Docs processed in this call
        "metadata": {"success": True}
    }
    state.update_from_tool_result('document_tool', result)

    assert state.evidence_collected == ["quote1 from doc1", "quote2 from doc2"]
    assert state.processed_doc_ids == {'doc1', 'doc2'}
    assert state.pending_doc_ids == {'doc3'} # doc1, doc2 removed
    assert state.current_confidence == 9.0
    assert 'document_tool' in state.tool_sequence

def test_state_validation_valid():
    """Test validation for a valid state."""
    state = AgentState()
    state.pending_doc_ids = {'doc3'}
    state.processed_doc_ids = {'doc1', 'doc2'}
    state.current_confidence = 8.0
    is_valid, errors = state.validate_state()
    assert is_valid is True
    assert errors == []

def test_state_validation_invalid_confidence():
    """Test validation for invalid confidence."""
    state = AgentState()
    state.current_confidence = 11.0
    is_valid, errors = state.validate_state()
    assert is_valid is False
    assert "Invalid confidence score: 11.0" in errors

def test_state_validation_overlap():
    """Test validation for overlap in pending/processed docs."""
    state = AgentState()
    state.pending_doc_ids = {'doc1', 'doc2'}
    state.processed_doc_ids = {'doc2', 'doc3'}
    is_valid, errors = state.validate_state()
    assert is_valid is False
    assert "Overlap detected between pending and processed doc IDs: ['doc2']" in errors # Order in set string representation might vary

def test_update_with_error_metadata():
    """Test that errors from tool metadata update the state."""
    state = AgentState()
    result = {
        "thought": "Something went wrong.",
        "answer": "Error occurred.",
        "confidence": 0,
        "metadata": {
            "success": False,
            "error": "Database connection failed"
        }
    }
    state.update_from_tool_result('category_tool', result)
    assert state.last_error == "Database connection failed"

def test_confidence_update_logic():
    """Test that confidence updates correctly (takes max)."""
    state = AgentState()
    state.update_from_tool_result('department_tool', {"confidence": 3.0, "metadata": {"success": True}})
    assert state.current_confidence == 3.0
    state.update_from_tool_result('category_tool', {"confidence": 7.0, "metadata": {"success": True}})
    assert state.current_confidence == 7.0
    # Lower confidence shouldn't decrease max
    state.update_from_tool_result('document_tool', {"confidence": 5.0, "metadata": {"success": True}})
    assert state.current_confidence == 7.0 
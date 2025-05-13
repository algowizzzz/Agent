"""
Unit tests for the ToolChainOrchestrator class.
"""

import pytest
from unittest.mock import MagicMock, Mock

# Modules to test
from langchain_tools.orchestrator import ToolChainOrchestrator
from langchain_tools.state_manager import AgentState

# Mock Tools - simple functions returning expected structure
def mock_dept_tool(*args, **kwargs):
    return {
        "thought": "Dept thought", "answer": "Dept answer",
        "category": "AMZN", "confidence": 3.0,
        "metadata": {"success": True, "tool_name": "department_tool"}
    }

def mock_cat_tool(*args, **kwargs):
    return {
        "thought": "Cat thought", "answer": "Cat answer",
        "relevant_doc_ids": ['d1', 'd2'], "confidence": 6.0,
        "metadata": {"success": True, "tool_name": "category_tool"}
    }

def mock_doc_tool(*args, **kwargs):
    # Simulate processing one doc ID from input
    doc_ids = kwargs.get('doc_ids', [])
    processed_id = doc_ids[0] if doc_ids else None
    return {
        "thought": "Doc thought", "answer": "Doc answer",
        "evidence": [f"Evidence from {processed_id}"], "confidence": 9.0,
        "analyzed_doc_ids": [processed_id] if processed_id else [],
        "metadata": {"success": True, "tool_name": "document_tool"}
    }

@pytest.fixture
def orchestrator_fixture():
    """Provides an orchestrator instance with mock tools and state."""
    mock_state = AgentState()
    mock_tools = {
        "department_tool": MagicMock(side_effect=mock_dept_tool),
        "category_tool": MagicMock(side_effect=mock_cat_tool),
        "document_tool": MagicMock(side_effect=mock_doc_tool)
    }
    orchestrator = ToolChainOrchestrator(tools=mock_tools, state=mock_state)
    return orchestrator, mock_state, mock_tools

def test_orchestrator_initialization(orchestrator_fixture):
    """Test orchestrator initializes correctly."""
    orchestrator, state, tools = orchestrator_fixture
    assert orchestrator.state is state
    assert list(orchestrator.tools.keys()) == ['department_tool', 'category_tool', 'document_tool']
    assert orchestrator.required_sequence == ['department_tool', 'category_tool', 'document_tool']

def test_get_expected_next_tool_sequence(orchestrator_fixture):
    """Test getting the next expected tool during the sequence."""
    orchestrator, state, _ = orchestrator_fixture
    assert orchestrator._get_expected_next_tool() == 'department_tool'
    state.tool_sequence.append('department_tool')
    assert orchestrator._get_expected_next_tool() == 'category_tool'
    state.tool_sequence.append('category_tool')
    assert orchestrator._get_expected_next_tool() == 'document_tool'
    state.tool_sequence.append('document_tool')
    assert orchestrator._get_expected_next_tool() is None # Sequence complete

def test_get_expected_next_tool_with_pending_docs(orchestrator_fixture):
    """Test that document_tool is expected if sequence is done but docs pending."""
    orchestrator, state, _ = orchestrator_fixture
    state.tool_sequence = ['department_tool', 'category_tool', 'document_tool']
    state.pending_doc_ids = {'d3'}
    assert orchestrator._get_expected_next_tool() == 'document_tool'

def test_validate_tool_call_correct_sequence(orchestrator_fixture):
    """Test validation succeeds for tools called in the correct sequence."""
    orchestrator, state, _ = orchestrator_fixture
    is_valid, msg = orchestrator.validate_tool_call('department_tool')
    assert is_valid is True
    assert msg is None

    state.tool_sequence.append('department_tool')
    is_valid, msg = orchestrator.validate_tool_call('category_tool')
    assert is_valid is True
    assert msg is None

    state.tool_sequence.append('category_tool')
    is_valid, msg = orchestrator.validate_tool_call('document_tool')
    assert is_valid is True
    assert msg is None

def test_validate_tool_call_out_of_sequence(orchestrator_fixture):
    """Test validation fails for tools called out of sequence."""
    orchestrator, state, _ = orchestrator_fixture
    is_valid, msg = orchestrator.validate_tool_call('category_tool')
    assert is_valid is False
    assert msg == "Tool 'category_tool' called out of sequence. Expected 'department_tool'."

    state.tool_sequence.append('department_tool')
    is_valid, msg = orchestrator.validate_tool_call('document_tool')
    assert is_valid is False
    assert msg == "Tool 'document_tool' called out of sequence. Expected 'category_tool'."

def test_validate_tool_call_pending_docs(orchestrator_fixture):
    """Test validation fails if non-document tool called when docs are pending."""
    orchestrator, state, _ = orchestrator_fixture
    state.pending_doc_ids = {'d1'}
    state.tool_sequence = ['department_tool', 'category_tool'] # Sequence not finished yet

    is_valid, msg = orchestrator.validate_tool_call('category_tool')
    assert is_valid is False
    assert msg == "Pending documents must be processed first using 'document_tool'."

    # Document tool itself should be valid
    is_valid, msg = orchestrator.validate_tool_call('document_tool')
    assert is_valid is True 
    assert msg is None
    
def test_validate_tool_call_unknown_tool(orchestrator_fixture):
    """Test validation fails for an unknown tool name."""
    orchestrator, _, _ = orchestrator_fixture
    is_valid, msg = orchestrator.validate_tool_call('unknown_tool')
    assert is_valid is False
    assert msg == "Tool 'unknown_tool' not found."

def test_execute_tool_success(orchestrator_fixture):
    """Test successful execution of a tool updates state."""
    orchestrator, state, mock_tools = orchestrator_fixture
    
    # Execute department tool
    result = orchestrator.execute_tool('department_tool', "test query")
    
    mock_tools['department_tool'].assert_called_once_with(query="test query")
    assert result['category'] == 'AMZN'
    assert state.category_id == 'AMZN'
    assert 'department_tool' in state.tool_sequence
    assert state.current_confidence == 3.0

def test_execute_tool_invalid_sequence(orchestrator_fixture):
    """Test executing a tool out of sequence returns an error dict."""
    orchestrator, _, mock_tools = orchestrator_fixture
    result = orchestrator.execute_tool('category_tool', "test query")
    
    mock_tools['category_tool'].assert_not_called()
    assert result['status'] == 'error' # Check updated structure if needed
    assert result['metadata']['success'] is False
    assert "called out of sequence" in result['metadata']['error']

def test_execute_tool_internal_error(orchestrator_fixture):
    """Test handling of an exception raised by the tool function."""
    orchestrator, state, mock_tools = orchestrator_fixture
    
    # Configure department tool mock to raise an error
    mock_tools['department_tool'].side_effect = ValueError("Internal tool error")
    
    result = orchestrator.execute_tool('department_tool', "test query")
    
    mock_tools['department_tool'].assert_called_once_with(query="test query")
    assert result['metadata']['success'] is False
    assert result['metadata']['error'] == "Internal tool error"
    assert "ValueError: Internal tool error" in result['metadata']['traceback']
    assert state.last_error == "Internal tool error" # Check if state updates on error too 
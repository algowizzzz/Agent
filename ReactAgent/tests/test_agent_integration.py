"""
Integration tests for the HierarchicalRetrievalAgent.
These tests mock external dependencies like LLM calls.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Agent to test
from langchain_tools.agent import HierarchicalRetrievalAgent

# --- Mock LLM Responses --- 
# Define sample text outputs from the LLM for different steps
MOCK_LLM_RESPONSE_DEPT = """
Thought: The user is asking about Amazon's cloud revenue in Q2 2019. I need to identify the category.
Action: department_tool
Action Input: What was Amazon's cloud revenue in Q2 2019?
"""

MOCK_LLM_RESPONSE_CAT = """
Thought: The department tool identified AMZN. Now I need to check the category summary for Q2 2019 info and find relevant docs.
Action: category_tool
Action Input: What was Amazon's cloud revenue in Q2 2019?, category=AMZN
"""

MOCK_LLM_RESPONSE_DOC = """
Thought: The category tool found relevant documents ['doc_q2_2019']. I need to analyze this document for the specific revenue number.
Action: document_tool
Action Input: What was Amazon's cloud revenue in Q2 2019?, doc_ids=['doc_q2_2019']
"""

MOCK_LLM_RESPONSE_FINAL = """
Thought: I have analyzed the relevant document and found the Q2 2019 AWS revenue.
Final Answer: Amazon's AWS revenue in Q2 2019 was $8.4 billion.
"""

MOCK_LLM_RESPONSE_MALFORMED = """
Thought: Thinking about the query.
Action: category_tool query=revenue, category=AMZN 
""" # Missing Action Input: label

# --- Mock Tool Results --- 
# Define the structured dicts returned by the *mocked* tool functions
MOCK_DEPT_TOOL_RESULT = {
    "thought": "Dept thought", "answer": "Identified category.",
    "category": "AMZN", "confidence": 3.0,
    "metadata": {"success": True, "tool_name": "department_tool"}
}
MOCK_CAT_TOOL_RESULT = {
    "thought": "Cat thought", "answer": "Found relevant docs.",
    "relevant_doc_ids": ['doc_q2_2019'], "confidence": 6.0,
    "metadata": {"success": True, "tool_name": "category_tool"}
}
MOCK_DOC_TOOL_RESULT = {
    "thought": "Doc thought", "answer": "Revenue was $8.4B",
    "evidence": ["AWS revenue grew to $8.4 billion (Document: doc_q2_2019)"], "confidence": 9.5,
    "analyzed_doc_ids": ['doc_q2_2019'],
    "metadata": {"success": True, "tool_name": "document_tool"}
}

@pytest.fixture
def mock_env_api_key(monkeypatch):
    """Mock environment variable for API key."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_api_key")

@pytest.fixture
def mocked_agent(mock_env_api_key):
    """Provides an agent instance with mocked LLM and tools."""
    
    # Patch the LLM initialization and invocation
    with patch('langchain_tools.agent.ChatAnthropic') as MockChatAnthropic:
        mock_llm_instance = MagicMock()
        # Configure LLM to return different responses based on input/call count
        mock_llm_instance.invoke.side_effect = [
            MOCK_LLM_RESPONSE_DEPT,
            MOCK_LLM_RESPONSE_CAT,
            MOCK_LLM_RESPONSE_DOC,
            MOCK_LLM_RESPONSE_FINAL 
            # Add more responses for complex scenarios or error cases
        ]
        MockChatAnthropic.return_value = mock_llm_instance

        # Patch the tool factory functions to return mocks
        with (patch('langchain_tools.agent.create_department_tool') as mock_create_dept,
             patch('langchain_tools.agent.create_category_tool') as mock_create_cat,
             patch('langchain_tools.agent.create_document_tool') as mock_create_doc):
             
             # Configure the factory functions to return MagicMocks 
             # that return our predefined results when called.
             mock_dept = MagicMock(return_value=MOCK_DEPT_TOOL_RESULT)
             mock_cat = MagicMock(return_value=MOCK_CAT_TOOL_RESULT)
             mock_doc = MagicMock(return_value=MOCK_DOC_TOOL_RESULT)
             
             mock_create_dept.return_value = mock_dept
             mock_create_cat.return_value = mock_cat
             mock_create_doc.return_value = mock_doc

             # Initialize the agent - it will now use all the mocks
             agent = HierarchicalRetrievalAgent(api_key="mock_key", debug=True) # API key doesn't matter due to mock
             
             # Store mocks for assertion
             agent._test_mocks = {
                 'llm': mock_llm_instance,
                 'dept_tool': mock_dept,
                 'cat_tool': mock_cat,
                 'doc_tool': mock_doc
             }
             yield agent

# --- Test Cases --- 

def test_agent_happy_path(mocked_agent):
    """Test a successful query execution following the full tool chain."""
    agent = mocked_agent
    query = "What was Amazon's cloud revenue in Q2 2019?"
    
    result = agent.query(query)
    
    # Assert final result structure and content
    assert result['status'] == 'success'
    assert "$8.4 billion" in result['result']
    assert len(result['evidence']) == 1
    assert "Evidence from doc_q2_2019" in result['evidence'][0]
    assert result['confidence'] >= 9.0 # Should reflect document tool confidence
    assert result['tool_sequence'] == ['department_tool', 'category_tool', 'document_tool']
    assert result['category_identified'] == 'AMZN'

    # Assert LLM calls (adjust count based on actual AgentExecutor behavior)
    # Might be more than 4 if retries or internal loops happen
    assert agent._test_mocks['llm'].invoke.call_count >= 4 

    # Assert tool calls
    agent._test_mocks['dept_tool'].assert_called_once() 
    agent._test_mocks['cat_tool'].assert_called_once() 
    agent._test_mocks['doc_tool'].assert_called_once() 
    # Add more specific assertions on tool inputs if needed

# TODO: Add more integration tests:
# - Test case where category tool returns no relevant docs
# - Test case where department tool returns no category
# - Test case with parsing errors (using MOCK_LLM_RESPONSE_MALFORMED and verifying fix-up/error handling)
# - Test case where a tool raises an exception internally
# - Test case where max_iterations is reached
# - Test case involving multiple document calls if category tool returns multiple IDs 
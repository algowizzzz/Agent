# Hierarchical Retrieval Agent Refactoring Plan

**Project Goal:**

Refactor and enhance the `HierarchicalRetrievalAgent` system to improve reliability, traceability, state management, error handling, and overall robustness by implementing a more structured and validated approach to tool execution and state tracking.

**Scope:**

This update involves modifications or creation of the following components:

*   `langchain_tools/agent.py` (Main Agent Logic)
*   `langchain_tools/output_parser.py` (LLM Output Parsing)
*   `langchain_tools/tool_factory.py` (Tool Creation & Validation)
*   `langchain_tools/tool1_department.py` (Tool Implementation)
*   `langchain_tools/tool2_category.py` (Tool Implementation)
*   `langchain_tools/tool3_document.py` (Tool Implementation)
*   `langchain_tools/tool_prompts_config.json` (LLM Prompts)
*   **New Files:**
    *   `langchain_tools/state_manager.py` (Agent State)
    *   `langchain_tools/orchestrator.py` (Tool Sequence Control)
    *   `langchain_tools/logger.py` (Structured Logging)
    *   `langchain_tools/error_recovery.py` (Error Handling Logic - Optional, can integrate into agent/orchestrator initially)
*   `tests/` directory (Unit & Integration Tests)
*   Configuration Management (Environment Variables, potentially new config files)

**Phase 1: Foundational Components (Core Logic & State)**

1.  **Implement Agent State Manager:**
    *   **File:** Create `langchain_tools/state_manager.py`.
    *   **Task:** Implement the `AgentState` class exactly as defined in the technical specifications. Include all specified fields (`pending_doc_ids`, `processed_doc_ids`, `current_confidence`, `evidence_collected`, `tool_sequence`, `category_id`) and methods (`__init__`, `update_from_tool_result`, `validate_state`, `reset`).
    *   **Why:** Centralizes state, making it easier to manage, track, and debug agent execution across multiple tool calls.
2.  **Implement Enhanced Output Parser:**
    *   **File:** Modify `langchain_tools/output_parser.py`.
    *   **Task:** Implement the `EnhancedAgentOutputParser` class as specified. Focus on robust regex parsing for `Thought:`, `Action:`, `Action Input:` and implement the `_fix_malformed_output` logic to handle common LLM formatting errors. Ensure it correctly distinguishes between `AgentAction` and `AgentFinish`.
    *   **Why:** Addresses the critical "Invalid Format: Missing 'Action Input:'" errors by reliably parsing the LLM's intended action.
3.  **Implement Basic Logging:**
    *   **File:** Create `langchain_tools/logger.py`.
    *   **Task:** Implement the `AgentLogger` class as specified. Focus initially on the `log_tool_call` method structure.
    *   **Why:** Provides structured, context-rich logging essential for debugging the complex agent flow.

**Phase 2: Tool Chain Orchestration & Validation**

4.  **Implement Tool Chain Orchestrator:**
    *   **File:** Create `langchain_tools/orchestrator.py`.
    *   **Task:** Implement the `ToolChainOrchestrator` class as specified. Include the `required_sequence` and methods (`__init__`, `validate_next_tool`, `execute_tool`, `get_next_required_tool`). The `execute_tool` method should call the actual tool function.
    *   **Why:** Enforces the mandatory `department -> category -> document` tool sequence, preventing the agent from skipping steps or calling tools out of order.
5.  **Implement Tool Validation in Factory:**
    *   **File:** Modify `langchain_tools/tool_factory.py`.
    *   **Task:** Ensure the `create_tool_with_validation` wrapper and the `validate_department_response`, `validate_category_response`, `validate_document_response` functions are implemented exactly as per the latest edits. Confirm that `create_department_tool`, `create_category_tool`, `create_document_tool` correctly use this validation wrapper.
    *   **Why:** Guarantees that tool outputs conform to the expected structure before they are used by the agent or state manager, preventing errors caused by malformed tool responses.

**Phase 3: Tool & Prompt Alignment**

6.  **Update Tool Prompts:**
    *   **File:** Modify `langchain_tools/tool_prompts_config.json`.
    *   **Task:**
        *   Verify the `category_tool` prompt matches the latest version (requesting `thought`, `answer`, `relevant_doc_ids`, `confidence`, `requires_documents`).
        *   Update the `department_tool` prompt's example JSON to include `"confidence": <0-10 score>`.
        *   Update the `document_tool` prompt's JSON structure to explicitly request a `"thought": "<reasoning>"` field alongside `answer`, `evidence`, and `confidence`.
    *   **Why:** Ensures the LLM is explicitly asked to provide all necessary information fields (like confidence and thought process) required by the updated tool response structures and validation logic.
7.  **Update Tool Implementations:**
    *   **Files:** Modify `tool1_department.py`, `tool2_category.py`, `tool3_document.py`.
    *   **Task:**
        *   Carefully review each tool's main function (`department_summary_tool`, `category_summary_tool`, `document_analysis_tool`).
        *   Ensure they return dictionaries matching *exactly* the structure validated in `tool_factory.py` and requested by the updated prompts (including `thought`, `confidence`, `metadata`, etc.). Refer to the latest code edits for the correct return structures.
        *   Make sure default values are provided for optional fields if the LLM doesn't return them.
    *   **Why:** Aligns the actual tool code with the prompt instructions and the validation layer, ensuring data flows correctly.

**Phase 4: Agent Integration**

8.  **Integrate Components into Main Agent:**
    *   **File:** Modify `langchain_tools/agent.py`.
    *   **Task:**
        *   In `HierarchicalRetrievalAgent.__init__`:
            *   Instantiate `AgentState`, `ToolChainOrchestrator`, `EnhancedAgentOutputParser`, and `AgentLogger`. Store them as instance variables (e.g., `self.state`, `self.orchestrator`, `self.parser`, `self.logger`).
            *   Update the agent's `initialize_agent` call to use the new `EnhancedAgentOutputParser`.
            *   Ensure tools are initialized using the updated `tool_factory` functions (which now include validation).
        *   In `HierarchicalRetrievalAgent.query`:
            *   Replace direct calls to `self.agent.run()` or similar with logic driven by the `ToolChainOrchestrator`.
            *   Use the `AgentLogger` to log entry, exit, tool calls, and state changes.
            *   Use the `AgentState` instance to manage state across the query execution. Reset the state at the beginning or end of the query.
            *   Remove old, direct state management attributes if they conflict (e.g., `self.current_doc_ids`, `self.current_evidence` might now be managed within `self.state`).
        *   Refactor `_wrap_category_tool` and `_wrap_document_tool`: These might become simpler or be handled within the orchestrator/state manager logic, as state updates are now centralized. Review if these wrappers are still needed in their current form or if the logic should move to `AgentState.update_from_tool_result`. **Focus on ensuring state updates happen correctly via `AgentState` after each tool call.**
    *   **Why:** Connects all the new and updated components, replacing the old, error-prone logic with the new, structured system.

**Phase 5: Testing & Documentation**

9.  **Implement Unit & Integration Tests:**
    *   **Directory:** `tests/`
    *   **Task:**
        *   Write unit tests for `AgentState`, `ToolChainOrchestrator`, `EnhancedAgentOutputParser`, `AgentLogger`, and the validation functions in `tool_factory.py`.
        *   Write integration tests that simulate a full query through the `HierarchicalRetrievalAgent.query` method, verifying:
            *   Correct tool sequence execution.
            *   Proper state updates (`pending_doc_ids`, `confidence`, etc.).
            *   Correct handling of tool validation failures.
            *   Correct parsing of LLM outputs (including malformed ones).
            *   Accurate final answer generation based on collected evidence and confidence.
    *   **Why:** Ensures individual components work correctly and that the integrated system functions as expected under various conditions.
10. **Update Documentation & Configuration:**
    *   **Task:**
        *   Update any README files or inline documentation (docstrings) to reflect the changes.
        *   Create documentation for the new components (`state_manager.py`, `orchestrator.py`, etc.).
        *   Clearly document the required environment variables (`ANTHROPIC_API_KEY`, `MONGODB_URI`, etc.).
        *   Ensure configuration (like tool prompts in `tool_prompts_config.json`) is accurate.
    *   **Why:** Makes the system understandable, maintainable, and usable by others.

**Key Integration Points to Verify:**

*   `agent.py` correctly uses `AgentState` for all state reads/writes.
*   `agent.py` uses `ToolChainOrchestrator` to decide which tool to call next.
*   `agent.py` uses `EnhancedAgentOutputParser` to parse LLM responses.
*   `tool_factory.py` correctly wraps tools with validation.
*   Tool implementations (`toolX_*.py`) return data in the validated format.
*   Prompts (`tool_prompts_config.json`) request data in the validated format.
*   Logging (`logger.py`) captures the necessary context at each step.

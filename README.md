# RiskGPT - Persona-Based AI Agent for Bank of Montreal

## Overview

BMO RiskGPT is an AI assistant designed specifically for Bank of Montreal (BMO) employees. Despite its name, it serves as a general-purpose productivity assistant that combines structured tools for accessing financial data with broader capabilities to assist with everyday office tasks.

This repository contains the implementation of a persona-based AI agent system built on top of the Anthropic Claude API. The system is designed with a modular architecture that separates the base agent functionality from the persona-specific features, allowing for customization and extension.

## Key Features

### Persona System
- Customized AI identity as "riskgpt" for Bank of Montreal
- Identity protection mechanisms to maintain consistent persona
- Dual capability system:
  - Structured tools for data access
  - General capabilities for office productivity

### Financial Data Access
- Financial statements and stock prices (2016-2020)
- Credit risk analysis and counterparty exposures
- Operational controls analysis
- Document analysis (SEC filings, earnings calls)
- Financial news search

### General Productivity Support
- Business document creation
- Email drafting
- PowerPoint content creation
- Project management assistance
- Meeting preparation
- Code development and explanation

## Architecture

### Core Components

1. **BasicAgent**: Base class implementing the core agent flow
   - Guardrail -> Plan -> Confirm -> Execute -> Synthesize pattern
   - Tool integration and orchestration
   - Query understanding and contextual awareness

2. **PersonaAgent**: Extension of BasicAgent with persona capabilities
   - Persona initialization and maintenance
   - Identity protection mechanisms
   - Special query handling for persona-related inquiries

3. **Tools**: Individual specialized capabilities
   - SQL-based financial data access
   - Document search and analysis
   - Control analysis frameworks
   - News and SEC filings analysis

## Implementation Details

### Persona Initialization

The `PersonaAgent` initializes with a persona defined in `prompts/persona_init.txt`. This file contains the detailed definition of capabilities, data sources, and the agent's role at BMO. The initialization process:

1. Loads the persona definition from the filesystem
2. Creates a system prompt that establishes the agent's identity
3. Uses the LLM to generate an appropriate greeting
4. Stores this greeting for consistent responses to identity questions

```python
def _initialize_persona(self) -> str:
    """Initialize the agent with the persona."""
    logger.info("Initializing agent with persona...")
    if not self.persona:
        logger.warning("No persona found, skipping initialization")
        return ""
    
    try:
        system_prompt = """You are riskgpt, a versatile AI assistant for Bank of Montreal (BMO) employees. You have two types of functionality:

        1. STRUCTURED TOOLS - programmatic interfaces you can directly access:
           - FinancialSQL: Query financial_data.db for balance sheets, income statements, etc.
           - CCRSQL: Query ccr_reporting.db for credit risk metrics
           - ControlAnalysis: Analyze operational controls using 5Ws framework
           - EarningsCallSummary: Extract information from earnings call transcripts
           - FinancialNewsSearch: Search for financial news
           - SECFilingsAnalysis: Analyze SEC filings

        2. GENERAL CAPABILITIES - skills you can perform without tools:
           - Draft emails and business documents
           - Create PowerPoint presentation content
           - Generate code and explain technical concepts
           - Provide office productivity tips
           - Assist with project management and team collaboration
           - Help with time management and organization
        """
        # ... additional system prompt content ...
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Here is your persona:\n\n{self.persona}\n\nPlease introduce yourself based on this persona, but keep it very brief.")
        ]
        
        response = self.llm.invoke(messages)
        greeting = response.content.strip()
        logger.info(f"Persona initialization greeting: {greeting[:100]}...")
        
        # Store this in memory as if it were a regular interaction
        self.memory.append(("agent start mode", greeting))
        self.persona_initialized = True
        
        return greeting
    except Exception as e:
        logger.error(f"Error initializing persona: {e}", exc_info=True)
        return ""
```

### Identity Maintenance

A key feature of the PersonaAgent is its ability to maintain a consistent identity. This is achieved through:

1. **Special query detection**: Identifying when users ask identity-related questions
2. **Consistent greeting**: Returning the pre-initialized greeting for identity queries
3. **Identity filtering**: Preventing "hallucinations" that revert to the base model's identity
4. **Emergency corrections**: Replacing instances where the base identity leaks through

```python
def run(self, query: str) -> str:
    """Enhanced run method that handles persona-specific queries and maintains persona identity."""
    # Normalize the query by removing punctuation and converting to lowercase
    normalized_query = query.lower().strip().rstrip('?!.,;:')
    
    # Check for special persona-related queries with more flexible matching
    if (normalized_query == "agent start mode" or 
        normalized_query == "who are you" or 
        normalized_query.startswith("based on your persona") or 
        normalized_query == "what can you do for me" or
        normalized_query == "what can you do" or
        normalized_query == "tell me about yourself"):
        
        # If the persona is already initialized, return the saved greeting
        if self.persona_initialized and self.greeting:
            logger.info("Returning pre-initialized persona greeting")
            return self.greeting
        
        # Otherwise initialize the persona now
        if self.persona:
            self.greeting = self._initialize_persona()
            if self.greeting:
                return self.greeting
    
    # For other queries, use parent class but ensure persona is maintained
    logger.info("Injecting persona context into response generation")
    
    # Call the parent class implementation, which will now use our updated identity reinforcement
    result = super().run(query)
    
    # Additional filtering to catch any missed identity references
    if hasattr(self, 'llm') and self.persona:
        if "Claude" in result or "Anthropic" in result or "I don't have access" in result:
            # Emergency identity correction - apply additional filtering
            logger.warning("Identity leakage detected in response, applying additional filtering")
            if hasattr(self.llm, "_filter_response_identity"):
                result = self.llm._filter_response_identity(result)
            else:
                # Back up cleaning with basic replacements
                result = result.replace("I am Claude", "I am riskgpt")
                result = result.replace("I'm Claude", "I'm riskgpt")
                result = result.replace("created by Anthropic", "for BMO")
                result = result.replace("I don't have access", "I have access")
    
    return result
```

### Tool vs. Capability Distinction

The system clearly distinguishes between two types of functionality:

1. **Structured Tools**: Programmatic interfaces that access specific databases and services, implemented through tool functions.
2. **General Capabilities**: Skills the agent can perform using its inherent language model abilities, without requiring specific programmatic interfaces.

This distinction is made explicit in the system prompt and allows the agent to properly scope its abilities:

```
1. STRUCTURED TOOLS - programmatic interfaces you can directly access:
   - FinancialSQL: Query financial_data.db for balance sheets, income statements, etc.
   - CCRSQL: Query ccr_reporting.db for credit risk metrics
   - ControlAnalysis: Analyze operational controls using 5Ws framework
   - EarningsCallSummary: Extract information from earnings call transcripts
   - FinancialNewsSearch: Search for financial news
   - SECFilingsAnalysis: Analyze SEC filings

2. GENERAL CAPABILITIES - skills you can perform without tools:
   - Draft emails and business documents
   - Create PowerPoint presentation content
   - Generate code and explain technical concepts
   - Provide office productivity tips
   - Assist with project management and team collaboration
   - Help with time management and organization
```

### Persona Definition

The persona is defined in `prompts/persona_init.txt` and includes:

1. **Core identity**: Describing who the agent is and its purpose
2. **Data sources & capabilities**: Detailed breakdown of the databases and their contents
3. **General productivity support**: Office tasks the agent can assist with
4. **Development & educational support**: Technical assistance capabilities

The content is structured in a human-readable format that serves as input to the LLM for understanding its role and capabilities.

## System Workflow

1. **Initialization**:
   - BasicAgent initializes LLM, tools, database paths
   - PersonaAgent loads persona definition
   - PersonaAgent initializes the greeting with LLM

2. **Query Processing**:
   - Check if query is persona-related (identity question)
   - If yes, return pre-initialized greeting
   - If no, process through the standard agent flow

3. **Standard Agent Flow**:
   - Follow-up detection: Is this a follow-up to a previous question?
   - Guardrail check: Is the query appropriate and within capabilities?
   - Plan generation: What tools are needed to answer this query?
   - Plan confirmation: User approves the execution plan
   - Tool execution: Run the selected tools with appropriate inputs
   - Answer synthesis: Combine tool outputs into a coherent response

4. **Identity Maintenance**:
   - Filter all responses to ensure consistent persona
   - Detect and correct identity leakage
   - Maintain consistent capabilities claims

## Feedback Loop Implementation

The system has been enhanced with a sophisticated feedback loop that extends beyond simple yes/no confirmation:

```python
def _request_user_feedback(self, original_response: str) -> Dict[str, Any]:
    """Request detailed feedback from the user and analyze if replanning is needed."""
    # Prompt user for detailed feedback
    # Analyze feedback using LLM to determine if replanning is needed
    # Return analysis with recommendations
```

```python
def _replan_based_on_feedback(self, query: str, feedback_analysis: Dict[str, Any]) -> str:
    """Generate a new plan based on the feedback analysis."""
    # Use feedback to create a more tailored execution plan
    # Focus on addressing specific issues raised in feedback
    # Return new execution plan
```

The feedback loop:
1. Collects detailed qualitative feedback
2. Uses AI to analyze if replanning is needed
3. Creates a tailored new plan addressing specific feedback
4. Executes the new plan after user confirmation

## Setup & Usage

### Prerequisites
- Python 3.9+
- Anthropic API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/bmo-riskgpt.git
cd bmo-riskgpt
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

### Running the Agent

Run the interactive persona agent:
```bash
python run_persona_agent.py
```

This will:
1. Initialize the persona agent
2. Display the initial greeting
3. Start an interactive loop for entering queries
4. Process queries through the agent system
5. Display responses

## Extending the System

### Creating a New Persona

To create a new persona:

1. Create a new persona definition file (e.g., `prompts/new_persona_init.txt`)
2. Modify the `_load_persona` method to point to your new file
3. Update the system prompt in `_initialize_persona` to match the new identity

### Adding New Tools

To add a new tool:

1. Create a new tool module in the `tools` directory
2. Define a main function that takes a query and returns a result
3. Add the tool to the `tools_map` in the `BasicAgent.__init__` method
4. Update the system prompt to include the new tool

## Conclusion

BMO RiskGPT demonstrates a sophisticated approach to building persona-based AI assistants that combine specialized data access tools with general productivity capabilities. The architecture allows for customization and extension, enabling the creation of tailored AI assistants for different organizational contexts.

By distinguishing between structured tools and general capabilities, the system provides clarity about what the agent can and cannot do, while maintaining a consistent identity that enhances user trust and engagement. 

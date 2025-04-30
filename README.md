# Enterprise Internal Agent: Documentation

## 1. System Overview

The Enterprise Internal Agent is a sophisticated AI-powered system designed to provide financial and business data analysis through a conversational interface. It processes natural language queries through a structured pipeline, leveraging various data sources and specialized tools to deliver accurate and contextually appropriate responses.

## 2. Architecture

### 2.1 Core Components

```
main.py                    # Entry point and orchestration
│
├── agents/                # Agent framework components
│   └── internal_agent.py  # Main agent orchestration logic
│
├── stages/                # Pipeline processing stages
│   ├── guardrails.py      # Input validation and safety checks
│   ├── planning.py        # Query analysis and tool selection
│   ├── execution.py       # Tool execution management
│   ├── reasoning.py       # Result analysis
│   └── final_output.py    # Response generation
│
├── tools/                 # Primary tool implementations
│   ├── financial_sql_tool.py     # Financial database access
│   ├── ccr_sql_tool.py           # Credit risk data access
│   ├── financial_news_tool.py    # Web search interface
│   └── earnings_call_tool.py     # Earnings transcript analysis
│
├── langchain_tools/       # Sub-tools and components
│   ├── tool2_category.py          # Category metadata
│   ├── tool4_metadata_lookup.py   # Document retrieval
│   └── tool5_transcript_analysis.py # Document analysis
│
├── prompts/               # System prompts for various stages
│   └── reasoning_prompt.txt       # Analysis template
│
└── scripts/               # Utilities and data management
    └── data/              # Local databases

```

### 2.2 Data Flow

1. User query is received via `main.py`
2. Query passes through sequential pipeline stages:
    - Guardrails → Planning → Execution → Reasoning → Final Output
3. Each stage maintains separation of concerns while sharing contextual information
4. Response is returned as structured JSON with answer and execution summary

## 3. Getting Started

### 3.1 Environment Setup

```bash
# Clone repository
git clone [repository-url]
cd enterprise-internal-agent

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/MacOS
# or
.venv\\Scripts\\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (API keys, database paths)
cp .env.example .env
# Edit .env with appropriate values

```

### 3.2 Database Configuration

The system utilizes multiple databases:

- **Financial Database**: SQLite at `scripts/data/financial_data.db`
    - Contains historical stock prices, company financials
    - Tables: companies, daily_stock_prices, dividends, quarterly_balance_sheet, quarterly_income_statement
- **CCR Database**: SQLite at `scripts/data/ccr_reporting.db`
    - Contains credit risk information
    - Tables: limits, products, report_counterparties, report_daily_exposures, securities, transit_mapping
- **Document Database**: MongoDB
    - Stores earnings call transcripts and other documents
    - Collection structure: categories, documents with summaries

### 3.3 First Run

```bash
# Run the main application
python main.py

# Example queries to test
"What was the closing price for MSFT on October 25, 2018?"
"What is the rating for JPMorgan?"
"Provide a brief summary of the MSFT Q4 2017 earnings call."

```

## 4. Core Components Deep Dive

### 4.1 Pipeline Stages

### Guardrails Stage

- **Purpose**: Validate queries against policy guidelines
- **Implementation**: `stages/guardrails.py`
- **Key Details**:
    - Uses Claude to evaluate query safety and policy compliance
    - Returns ALLOW/BLOCK decision with reasoning
    - Currently configured to only allow enterprise financial and public data queries

### Planning Stage

- **Purpose**: Generate execution plan based on query intent
- **Implementation**: `stages/planning.py`
- **Key Details**:
    - Analyzes query to determine required tools
    - Creates numbered plan specifying exact tool calls
    - Presents plan for user confirmation

### Execution Stage

- **Purpose**: Execute the approved plan by calling tools
- **Implementation**: `stages/execution.py`
- **Key Details**:
    - Processes each step in sequence
    - Passes natural language inputs to appropriate tools
    - Collects and formats results for reasoning stage

### Reasoning Stage

- **Purpose**: Analyze execution results to formulate response
- **Implementation**: `stages/reasoning.py`
- **Key Details**:
    - Uses `reasoning_prompt.txt` template
    - Evaluates if query has been fully answered
    - Structures analysis for final output

### Final Output Stage

- **Purpose**: Generate structured response
- **Implementation**: `stages/final_output.py`
- **Key Details**:
    - Creates JSON with answer and execution summary
    - Formats response for optimal readability

### 4.2 Tools

### FinancialSQL

- **Purpose**: Query financial database for historical metrics
- **Implementation**: `tools/financial_sql_tool.py`
- **Key Details**:
    - Automatically generates SQL from natural language
    - Access to company financial data, stock prices
    - Query templating for common financial questions

### CCRSQL

- **Purpose**: Query credit risk database
- **Implementation**: `tools/ccr_sql_tool.py`
- **Key Details**:
    - Access to credit ratings, exposure, limits, etc.
    - Handles complex relationships between financial entities

### FinancialNewsSearch

- **Purpose**: Search for current financial information
- **Implementation**: `tools/financial_news_tool.py`
- **Key Details**:
    - Web search integration for real-time data
    - Returns formatted article summaries

### EarningsCallSummary

- **Purpose**: Process earnings call transcripts
- **Implementation**: `tools/earnings_call_tool.py`
- **Key Details**:
    - Complex multi-agent system with sub-tools
    - MongoDB integration for document retrieval
    - Multi-step analysis to generate comprehensive summaries

## 5. Productionalization Recommendations

### 5.1 Code Improvements

1. **Deprecation Warnings**
    - Update LangChain imports to resolve deprecation warnings:
        
        ```python
        # Replace deprecated imports
        from langchain.sql_database import SQLDatabase
        # With
        from langchain_community.utilities import SQLDatabase
        
        ```
        
2. **Database Schema Issues**
    - Resolve circular dependencies in CCR database tables
    - Consider schema refactoring to improve query performance
3. **Error Handling**
    - Implement more robust error handling throughout the pipeline
    - Add retry logic for external API calls and database queries
4. **Testing**
    - Add comprehensive unit tests for each component
    - Implement integration tests for the full pipeline
    - Create test fixtures for reproducible results

### 5.2 Infrastructure Requirements

1. **Compute Resources**
    - CPU: 4+ cores for concurrent processing
    - RAM: 8GB+ for handling large document processing
    - Storage: 20GB+ for databases and logs
2. **External Dependencies**
    - Anthropic API (Claude 3.5 Sonnet)
    - MongoDB instance
    - Web search API access
3. **Security Considerations**
    - API key rotation policy
    - Encryption for sensitive data
    - Access controls for database connections

### 5.3 Scaling Strategies

1. **Horizontal Scaling**
    - Containerize application with Docker
    - Deploy with Kubernetes for orchestration
    - Implement load balancing for multiple instances
2. **Performance Optimization**
    - Cache common queries and responses
    - Implement background processing for complex operations
    - Add database indexing for frequently accessed fields
3. **Monitoring and Observability**
    - Enhance logging for production debugging
    - Implement metrics collection (query latency, success rates)
    - Add alerting for system failures

## 6. Known Issues and Limitations

1. **Data Freshness**
    - Financial database contains historical data (2016-2020)
    - Real-time stock data requires additional integration
2. **Tool Selection Accuracy**
    - Planning stage occasionally selects suboptimal tools
    - Document retrieval sometimes identifies incorrect documents
3. **Response Formatting**
    - Occasionally includes technical details in user-facing responses
    - Some formatting inconsistencies in complex responses
4. **External Dependencies**
    - LangChain deprecation warnings need addressing
    - MongoDB circular dependency warnings

## 7. Development Workflow

1. **Code Contribution Process**
    - Branch from `main` for new features/fixes
    - Follow naming convention: `feature/description` or `fix/issue-id`
    - Submit PRs with comprehensive descriptions
2. **Testing Requirements**
    - All new code must include unit tests
    - Integration tests for full pipeline modifications
    - Performance benchmarks for database changes
3. **Documentation Standards**
    - Update [README.md](http://readme.md/) for high-level changes
    - Document all new functions with docstrings
    - Keep this onboarding doc updated for architectural changes

## 8. Contact and Support

- **Original Developer**: [Your Name]
- **Project Lead**: [Project Lead Name]
- **Support Email**: [support@example.com]
- **Repository**: [repository-url]
- **Documentation**: [docs-url]

## 9. Appendix

### A. Example Queries

```
"What was the revenue for AAPL in Q3 2019?"
"What is the credit exposure for Deutsche Bank?"
"Summarize the earnings call for GOOG Q2 2018"
"What are the latest news about interest rates?"

```

### B. Tool Selection Guidelines

| Query Type | Recommended Tool | Example |
| --- | --- | --- |
| Historical Financial Data | FinancialSQL | "Revenue for AAPL in 2019" |
| Credit Risk Information | CCRSQL | "Credit rating for JPMorgan" |
| Current News/Events | FinancialNewsSearch | "Latest tariff news" |
| Earnings Call Information | EarningsCallSummary | "Summary of MSFT earnings" |

### C. Database Schema Diagrams

[Include diagrams of your database schemas here]

---

# Technical Summary: Enterprise Internal Agent Flow

## System Overview

The Enterprise Internal Agent is an orchestrated system handling financial and business data queries through a multi-stage pipeline. Each query passes through validation, planning, execution, reasoning, and output stages, with each stage leveraging specialized tools.

## Query Processing Pipeline

### 1. Query Ingestion and Validation

- All queries enter via `main.py` and are processed by the Guardrails stage
- LLMChain with Claude 3.5 Sonnet performs policy compliance validation
- Only enterprise financial and public data queries are allowed

### 2. Planning Stage

- System analyzes the query intent and selects appropriate tool(s)
- Generates a numbered execution plan specifying exact tool calls
- Plan is presented to user for approval before execution

### 3. Execution Stage

- Processes approved plan by calling specified tools in sequence
- Each tool performs specialized functions depending on query requirements

### 4. Reasoning Stage

- Analyzes execution results to formulate coherent response
- Identifies if information is sufficient or if additional context is needed
- Structures findings for final output generation

### 5. Final Output Stage

- Generates structured JSON response with answer and execution summary
- Formats information for optimal readability and completeness

---

## Tools and Subsystems

### Primary Tools

1. **FinancialSQL**
    - Queries financial database for historical metrics (2016-2020)
    - Example: Retrieved MSFT closing price ($101.44) on 10/25/2018
    - Automatically generates SQL based on natural language input
2. **CCRSQL**
    - Accesses Customer Credit Risk database
    - Example: Retrieved JPMorgan Chase credit rating (AA-)
    - Handles complex SQL relationships between financial entities
3. **FinancialNewsSearch**
    - Performs web searches for current financial information
    - Example: Located latest tariff news affecting the energy sector
    - Returns article titles, snippets, and links
4. **EarningsCallSummary**
    - Complex multi-agent system with internal tools
    - Analyzes earnings call transcripts for specific companies
    - Example: Provided MSFT Q4 2017 earnings call summary with financial performance, initiatives, and outlook

### EarningsCallSummary Sub-tools

1. **category_tool**: Retrieves high-level category summaries for companies
2. **metadata_lookup_tool**: Identifies relevant document IDs from MongoDB
3. **document_content_analysis_tool**: Analyzes specific document content

## Technical Implementation

- Built with LangChain components with Claude 3.5 Sonnet as the base LLM
- MongoDB for document storage and retrieval
- SQLite databases for financial and CCR data
- Modular design with separate stages and tools for maintainability
- Detailed logging for debugging and transparency

## Performance Observations

- Query processing typically takes 1-2 seconds per tool call
- Complex multi-agent workflows (like EarningsCallSummary) require multiple LLM calls
- The system demonstrates robust error handling and graceful recovery from inconsistencies
- MongoDB warnings regarding circular dependencies in some database relationships should be addressed

## Sample Query Flow

For query "What is the rating for JPMorgan?":

1. Guardrails validates query is permitted (financial data)
2. Planning identifies CCRSQL as appropriate tool
3. CCRSQL generates and executes SQL: `SELECT rating FROM report_counterparties WHERE short_name = 'JPMorgan Chase' LIMIT 10`
4. Result `[('AA-',)]` retrieved from database
5. Reasoning analyzes and contextualizes the rating information
6. Final structured answer explains JPMorgan Chase has AA- rating

---

# Enterprise Internal Agent: Analysis of Query Processing Steps

Based on the logs from our test runs, here's a detailed breakdown of the processing steps for each query:

## Query 1: "What was the closing price for MSFT on October 25, 2018?"

1. **Guardrails Stage**
    - System checked query against safety policy
    - Claude determined query was about public financial data
    - Policy validation result: ALLOW
2. **Planning Stage**
    - System analyzed query and available tools
    - Selected tool: `FinancialSQL`
    - Generated plan: "1. FinancialSQL: What was the closing price for MSFT on October 25, 2018?"
    - User confirmed plan
3. **Execution Stage**
    - LLM formatted the tool call
    - Tool initialized with DB path: `/Users/saadahmed/Desktop/Apps/BussGPT/scripts/data/financial_data.db`
    - Generated SQL: `SELECT close FROM daily_stock_prices WHERE ticker = 'MSFT' AND date = '2018-10-25' LIMIT 1`
    - Executed SQL query (processing time: 1.64s)
    - Result retrieved: `[(101.43556213378906,)]`
4. **Reasoning Stage**
    - System analyzed query result
    - Verified all parts of question were answered
    - Determined rounding to nearest cent was appropriate
5. **Final Output Stage**
    - Generated formatted JSON response
    - Final answer: MSFT closing price was $101.44 on October 25, 2018
    - Included execution summary for transparency

## Query 2: "What is the rating for JPMorgan?"

1. **Guardrails Stage**
    - System checked query against safety policy
    - Claude determined query was about public financial data
    - Policy validation result: ALLOW
2. **Planning Stage**
    - System analyzed query and available tools
    - Selected tool: `CCRSQL` (recognized this was a credit rating query)
    - Generated plan: "1. CCRSQL: What is the current credit rating for JPMorgan Chase?"
    - User confirmed plan
3. **Execution Stage**
    - LLM formatted the tool call
    - Tool initialized with DB path: `/Users/saadahmed/Desktop/Apps/BussGPT/scripts/data/ccr_reporting.db`
    - Generated SQL: `SELECT rating FROM report_counterparties WHERE short_name = 'JPMorgan Chase' LIMIT 10`
    - Warning: Circular dependencies in database detected
    - Executed SQL query (processing time: 1.18s)
    - Result retrieved: `[('AA-',)]`
4. **Reasoning Stage**
    - System analyzed query result
    - Noted the company name in database is "JPMorgan Chase" vs. "JPMorgan" in query
    - Interpreted "AA-" rating in financial context
5. **Final Output Stage**
    - Generated formatted JSON response
    - Final answer: JPMorgan Chase has an AA- credit rating
    - Explained rating indicates strong capacity to meet financial commitments

## Query 3: "Provide a brief summary of the MSFT Q4 2017 earnings call."

1. **Guardrails Stage**
    - System checked query against safety policy
    - Claude determined query was about public financial data
    - Policy validation result: ALLOW
2. **Planning Stage**
    - System analyzed query and available tools
    - Selected tool: `EarningsCallSummary`
    - Generated plan: "1. EarningsCallSummary: Provide a summary of Microsoft's Q4 2017 earnings call..."
    - User confirmed plan
3. **Execution Stage (Complex Multi-Agent)**
    - Tool initialized agent execution with multiple internal steps:
    a. Called `category_tool` to fetch high-level Microsoft summary
    b. Called `metadata_lookup_tool` to identify relevant documents in MongoDB:
        - Fetched metadata for 188 documents across 10 categories
        - Found 2 relevant document IDs for MSFT Q4 2017
        c. Called `document_content_analysis_tool` on first document
        - System analyzed incorrect document (Cisco earnings call)
        d. Called `document_content_analysis_tool` on second document
        - Successfully retrieved Microsoft Q4 2017 earnings data
    - Agent synthesized final report covering:
        - Financial performance ($24.7B revenue, 10% growth)
        - Strategic initiatives (Microsoft 365, Azure expansion)
        - Management outlook (cloud revenue goals)
4. **Reasoning Stage**
    - System analyzed the synthesized earnings call summary
    - Determined information was complete and relevant
5. **Final Output Stage**
    - Generated formatted JSON response
    - Final answer: Comprehensive summary of Microsoft's Q4 2017 performance
    - Included full tools and sub-tools execution summary

## Query 4: "Latest tariff news impacting energy sector"

1. **Guardrails Stage**
    - System checked query against safety policy
    - Claude determined query was about public financial/economic data
    - Policy validation result: ALLOW
2. **Planning Stage**
    - System analyzed query and available tools
    - Selected tool: `FinancialNewsSearch`
    - Generated plan: "1. FinancialNewsSearch: Latest tariff news impacting energy sector"
    - User confirmed plan
3. **Execution Stage**
    - LLM formatted the tool call
    - Tool performed web search for tariff news related to energy sector
    - Retrieved 3 relevant articles about Trump tariffs on batteries and solar industry
4. **Reasoning Stage**
    - System analyzed the search results
    - Identified key themes: impacts on utilities, energy storage, solar industry
    - Noted limitations in available information (rates, dates, global impact)
5. **Final Output Stage**
    - Generated formatted JSON response
    - Final answer: Detailed overview of tariff impacts on energy sector
    - Highlighted implications for grid reliability, solar companies, and renewable adoption

Each query demonstrates the system's consistent processing pipeline while adapting to different information needs and data sources.

---

---

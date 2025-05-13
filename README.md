# BussGPT: Financial & Business Intelligence Agent

BussGPT is an AI-powered financial and business intelligence agent that provides sophisticated analysis of financial data, market information, and earnings call transcripts. It leverages multiple specialized tools and integrates advanced guardrails for safe, reliable operation.

## Core Capabilities

- **Financial Data Analysis**: Access historical stock prices, financial metrics, and market data
- **Credit Risk Assessment**: Analyze counterparty credit risk, exposures, and ratings
- **Earnings Call Intelligence**: Extract qualitative insights from earnings call transcripts
- **Market News**: Search for current financial and business news
- **Multi-Tool Orchestration**: Combine results from multiple data sources for comprehensive answers

## Agent Architecture

BussGPT implements two agent architectures:

### 1. BasicAgent (Latest)

The primary agent implementation follows a structured, reliable workflow:

```
Guardrail → Plan → Confirm → Execute → Synthesize
```

#### Key Features:

- **Guardrail System**: Pre-processes queries for safety, appropriateness, and capabilities
- **Planning**: Determines which tools are needed to answer the query
- **User Confirmation**: Displays the planned approach and waits for user approval
- **Tool Execution**: Runs the necessary tools sequentially
- **Answer Synthesis**: Combines tool results into a comprehensive answer

#### Agent "Thinking" Display:
The agent shows its reasoning process through simplified thinking steps, providing transparency into how it approached the query.

### 2. ReAct Agent (Legacy)

An alternative implementation based on the ReAct (Reasoning and Acting) paradigm.

## Setup

1. Clone this repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your Anthropic API key:
   ```bash
   # Create .env file
   echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
   ```

## Usage

### CLI Interface

Run the agent in interactive command-line mode:

```bash
python main.py
```

### Web Interface

Start the backend server:

```bash
python backend_server.py
```

Then access the web interface via Socket.IO.

## Database Structure

BussGPT works with SQLite databases for financial and credit risk data:

1. **financial_data.db**: Contains historical financial information
   - Tables: companies, daily_stock_prices, quarterly_income_statement, etc.

2. **ccr_reporting.db**: Contains counterparty credit risk data
   - Tables: limits, counterparties, exposures, etc.

## Tools

The agent integrates multiple specialized tools:

1. **FinancialSQL**: Queries historical financial data
2. **CCRSQL**: Queries counterparty credit risk data
3. **FinancialNewsSearch**: Retrieves current financial news
4. **EarningsCallSummary**: Analyzes earnings call transcripts

## Query Examples

BussGPT can handle a wide range of financial queries:

- "What was the stock price of Apple on June 2, 2017?"
- "What is our total exposure to JP Morgan?"
- "Summarize Microsoft's Q4 2017 earnings call"
- "What recent news might affect Bank of America's rating?"

## Advanced Features

### Conversation Memory

The agent maintains memory of previous interactions to handle follow-up questions appropriately.

### Emergency Stop

Long-running operations can be interrupted with Ctrl+C while preserving work done so far.

### Thinking Steps Display

The agent shows its reasoning process:

```
Thinking...
- Validating query against safety and capability guardrails...
- Planning which tools are needed to answer your question...
- Querying financial database: 'What was the stock price of AAPL on...'
- Database returned results: '('2017-06-02', 36.256385803'...
- Synthesizing comprehensive answer from all gathered information...
```

## Development and Testing

Several test scripts are provided to verify agent functionality:

```bash
# Test BasicAgent with sample queries
python test_basic_agent.py

# Test ReactAgent with sample queries
python test_react_agent.py
```

## Requirements

- Python 3.8+
- Anthropic API key (Claude 3)
- SQLite
- Socket.IO (for web interface)

## Directory Structure

```
BussGPT/
├── basic_agent.py        # Main BasicAgent implementation
├── main.py               # CLI entrypoint
├── backend_server.py     # Web interface server
├── tools/                # Tool implementations
│   ├── ccr_sql_tool.py   # Credit risk data tool
│   ├── financial_sql_tool.py  # Financial data tool
│   ├── financial_news_tool.py  # News search tool
│   └── earnings_call_tool.py  # Transcript analysis tool
├── scripts/              # Utility scripts
│   └── data/             # Database files
├── react_agent/          # Legacy ReAct agent
└── tests/                # Test scripts
```

## Transcript Database

The system can also work with a MongoDB transcript database. See the [Transcript Database](#transcript-database) section for more details.

## Transcript Database

This project imports earnings call transcripts into MongoDB for later use with LLM applications.

### Setup Instructions

1. Install MongoDB
   - Download and install MongoDB from https://www.mongodb.com/try/download/community
   - Start the MongoDB service

2. Import transcripts
   ```bash
   python import_transcripts.py
   ```

3. Update documents with metadata (date, quarter, fiscal year)
   ```bash
   python update_transcripts.py
   ```

4. Calculate token counts for LLM usage
   ```bash
   python add_token_counts.py
   ```

### Database Collections

The MongoDB database consists of the following collections:

1. **transcripts**: Contains the actual transcript documents
2. **document_summaries**: Contains summaries of individual transcripts
3. **category_summaries**: Contains cross-quarter analyses for each company
4. **department_summaries**: Contains sector-level summaries across companies

## License

MIT License

## Contributing

We welcome contributions to BussGPT! Please submit pull requests with improvements, bugfixes, or new features. 
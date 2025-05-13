# BussGPT Testing Guide

This document provides instructions on how to test the BussGPT agent without needing the full frontend application.

## 1. Simple Command Line Testing

The simplest way to test the agent is using the `simple_query_test.py` script:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run a single query
python simple_query_test.py "Your query here"

# Or use interactive mode
python simple_query_test.py
```

## 2. API Test Server

For a more web-like experience, you can use the API test server:

```bash
# Activate the virtual environment
source venv/bin/activate

# Start the API test server
python api_test_server.py
```

Then open your browser and navigate to: http://localhost:5002/

You can also test the API directly with curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"What is the current price of Tesla stock?"}' \
  http://localhost:5002/api/query
```

## 3. Running Test Scripts

There are also predefined test scripts in the `scripts/agent_tests` directory:

```bash
# Activate the virtual environment
source venv/bin/activate

# Run a test with a specific query
python scripts/agent_tests/test_main_agent.py -q "Your query here"
```

## Troubleshooting

If you encounter any issues:

1. Make sure your virtual environment is activated
2. Check that all required environment variables are set
3. Verify that you have the necessary API keys (ANTHROPIC_API_KEY, etc.)
4. Look for error messages in the console output

For server-related issues, check if the port (5002) is already in use:

```bash
# Check if port 5002 is in use
lsof -i :5002

# Kill any process using port 5002
kill $(lsof -t -i:5002)
``` 
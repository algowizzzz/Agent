# BussGPT Test Scripts

This directory contains various test scripts for verifying and troubleshooting the BussGPT application.

## API Key Setup and Verification

### `setup_api_key.py`

Interactive script to set up and verify your Anthropic API key.

```bash
python3 scripts/setup_api_key.py
```

This script will:
1. Check for existing API keys in your `.env` and `.env.anthropic` files
2. Verify if the existing key is valid
3. Allow you to enter a new API key if needed
4. Verify the new key and save it to both configuration files

## Component Tests

### `test_api_key.py`

Tests the API key handling across different components of the application.

```bash
python3 scripts/test_api_key.py
```

### `test_document_analysis.py`

Tests the document analysis functionality with a real or sample document ID.

```bash
python3 scripts/test_document_analysis.py
```

### `test_agent.py`

Tests the main agent with a simple query to verify end-to-end functionality.

```bash
python3 scripts/test_agent.py
```

### `test_api_direct.py`

Directly tests both API keys from `.env` and `.env.anthropic` files against the Anthropic API.

```bash
python3 scripts/test_api_direct.py
```

## Main Agent Test

### `test_main_agent.py`

Runs the main agent with a custom query.

```bash
python3 scripts/agent_tests/test_main_agent.py -q "What was Microsoft's cloud strategy in Q1 2017?"
```

## Troubleshooting

If you encounter authentication errors (HTTP 401):

1. Run `setup_api_key.py` to configure a valid API key
2. Ensure your API key is properly formatted and starts with `sk-ant-`
3. Verify your API key has the necessary permissions for Claude models
4. Check that your account has sufficient credits

For database or connection errors:
1. Verify that the database files exist in `scripts/data/`
2. Check that the MongoDB service is running if using document analysis features 

This directory contains various test scripts for verifying and troubleshooting the BussGPT application.

## API Key Setup and Verification

### `setup_api_key.py`

Interactive script to set up and verify your Anthropic API key.

```bash
python3 scripts/setup_api_key.py
```

This script will:
1. Check for existing API keys in your `.env` and `.env.anthropic` files
2. Verify if the existing key is valid
3. Allow you to enter a new API key if needed
4. Verify the new key and save it to both configuration files

## Component Tests

### `test_api_key.py`

Tests the API key handling across different components of the application.

```bash
python3 scripts/test_api_key.py
```

### `test_document_analysis.py`

Tests the document analysis functionality with a real or sample document ID.

```bash
python3 scripts/test_document_analysis.py
```

### `test_agent.py`

Tests the main agent with a simple query to verify end-to-end functionality.

```bash
python3 scripts/test_agent.py
```

### `test_api_direct.py`

Directly tests both API keys from `.env` and `.env.anthropic` files against the Anthropic API.

```bash
python3 scripts/test_api_direct.py
```

## Main Agent Test

### `test_main_agent.py`

Runs the main agent with a custom query.

```bash
python3 scripts/agent_tests/test_main_agent.py -q "What was Microsoft's cloud strategy in Q1 2017?"
```

## Troubleshooting

If you encounter authentication errors (HTTP 401):

1. Run `setup_api_key.py` to configure a valid API key
2. Ensure your API key is properly formatted and starts with `sk-ant-`
3. Verify your API key has the necessary permissions for Claude models
4. Check that your account has sufficient credits

For database or connection errors:
1. Verify that the database files exist in `scripts/data/`
2. Check that the MongoDB service is running if using document analysis features 
 
 
#!/bin/bash
# Script to start the API test server

# Stop any existing instances
echo "Stopping any existing test servers..."
pkill -f api_test_server.py
sleep 2

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Start the API test server
echo "Starting API test server..."
python api_test_server.py 
#!/bin/bash

# Kill any existing backend server processes
echo "Stopping any existing backend processes..."
kill $(lsof -t -i:5001) 2>/dev/null || true

# Wait a moment to ensure port is released
sleep 2

# Activate virtual environment and run backend with logging
echo "Starting backend server with logging..."
source venv/bin/activate && \
PYTHONUNBUFFERED=1 python backend_server.py > backend_log.txt 2>&1

echo "Backend server process ended. Check backend_log.txt for details." 
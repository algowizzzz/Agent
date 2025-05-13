#!/bin/bash

# Kill any existing processes
echo "Stopping any existing processes..."
# Kill backend server if running on port 5001
kill $(lsof -t -i:5001) 2>/dev/null || true
# Kill Angular server if running on port 4200
kill $(lsof -t -i:4200) 2>/dev/null || true

# Wait a moment to ensure ports are released
sleep 2

# Start the backend server in a new terminal window
echo "Starting backend server..."
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && source venv/bin/activate && python backend_server.py"'

# Wait for the backend to initialize
sleep 5

# Start the Angular frontend in a new terminal window
echo "Starting Angular frontend..."
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"'/agent-ui/agent-ui && ng serve"'

echo "Services started. Backend running at http://localhost:5001, Frontend at http://localhost:4200" 
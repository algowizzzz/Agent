#!/bin/bash
# Wrapper script to run the CCR SQL tool test within its virtual environment.

# Get the directory where the script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Navigate to the project root (assuming this script is in scripts/tool_tests)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &> /dev/null && pwd)"

# Define the virtual environment path
VENV_PATH="$PROJECT_ROOT/venv"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH" >&2
    exit 1
fi

# Check if Python script exists
PYTHON_SCRIPT="$PROJECT_ROOT/scripts/tool_tests/test_ccr_sql_tool.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python test script not found at $PYTHON_SCRIPT" >&2
    exit 1
fi

# Activate the virtual environment
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment at $VENV_PATH/bin/activate" >&2
    exit 1
fi

echo "Virtual environment activated."

# Run the Python script, passing all arguments received by this wrapper
python "$PYTHON_SCRIPT" "$@"

# Capture the exit code of the Python script
EXIT_CODE=$?

# Deactivate the virtual environment
deactivate

echo "Virtual environment deactivated."

# Exit with the Python script's exit code
exit $EXIT_CODE 
#!/bin/bash

# Script to backup and remove the Angular frontend (agent-ui directory)
# This script should be run from the project root directory

# Define paths
PROJECT_ROOT="/Users/saadahmed/Desktop/Apps/BussGPT"
BACKUP_DIR="$PROJECT_ROOT/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/angular_frontend_$TIMESTAMP.tar.gz"

echo "Creating backup of Angular frontend (agent-ui)..."

# Create backup directory if it doesn't exist
if [ ! -d "$BACKUP_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    if [ $? -ne 0 ]; then
        echo "Failed to create backup directory. Aborting."
        exit 1
    fi
    echo "Created backup directory: $BACKUP_DIR"
fi

# Check if agent-ui directory exists
if [ ! -d "$PROJECT_ROOT/agent-ui" ]; then
    echo "Angular frontend directory (agent-ui) not found. Nothing to backup or remove."
    exit 0
fi

# Create backup of agent-ui directory
tar -czf "$BACKUP_FILE" -C "$PROJECT_ROOT" agent-ui
if [ $? -ne 0 ]; then
    echo "Backup failed. Angular frontend will not be removed."
    exit 1
fi

echo "Backup created successfully: $BACKUP_FILE"

# Remove the Angular frontend directory
echo "Removing Angular frontend directory..."
rm -rf "$PROJECT_ROOT/agent-ui"
if [ $? -ne 0 ]; then
    echo "Failed to remove Angular frontend directory."
    exit 1
fi

echo "Angular frontend has been successfully removed."
echo "The API test server will now serve as the main frontend interface."
echo "You can access it at http://localhost:5002/ after starting the server with './run_test_server.sh'"

exit 0 
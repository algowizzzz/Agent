#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# IMPORTANT: Replace with your actual Anthropic API key
# Get your API key from: https://console.anthropic.com/settings/keys
export ANTHROPIC_API_KEY="your_api_key_here"

# Run the summarizer with the provided arguments
python summarize_transcript.py "$@" 
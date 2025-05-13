#!/usr/bin/env python3
"""
Utility script to set up and verify an Anthropic API key
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_api_key(api_key):
    """Verify that the given API key is valid by making a test request"""
    if not api_key:
        logger.error("No API key provided")
        return False
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Say hello"
            }
        ]
    }
    
    try:
        logger.info("Making test API call to Anthropic")
        response = requests.post(url, headers=headers, json=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ API key verified successfully: {result}")
            return True
        else:
            logger.error(f"❌ API key verification failed with status code {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API call failed with error: {e}")
        return False

def save_api_key(api_key):
    """Save the API key to the .env and .env.anthropic files"""
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    env_anthropic_path = project_root / ".env.anthropic"
    
    # Update .env file
    try:
        # Read existing content
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
                
            # Find and replace the API key line
            api_key_found = False
            for i, line in enumerate(lines):
                if line.startswith("ANTHROPIC_API_KEY="):
                    lines[i] = f"ANTHROPIC_API_KEY={api_key}\n"
                    api_key_found = True
                    break
            
            # Add the API key if not found
            if not api_key_found:
                lines.append(f"ANTHROPIC_API_KEY={api_key}\n")
                
            # Write updated content back
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        else:
            # Create new .env file
            with open(env_path, 'w') as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
        
        logger.info(f"✅ API key saved to {env_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save API key to {env_path}: {e}")
    
    # Update .env.anthropic file
    try:
        with open(env_anthropic_path, 'w') as f:
            f.write(f"export ANTHROPIC_API_KEY={api_key}\n")
        logger.info(f"✅ API key saved to {env_anthropic_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save API key to {env_anthropic_path}: {e}")

def setup_api_key():
    """Interactive setup for the API key"""
    print("\n=== Anthropic API Key Setup ===\n")
    print("This script will help you set up and verify your Anthropic API key.")
    print("You'll need an API key from https://console.anthropic.com/\n")
    
    # Try to load existing key
    load_dotenv()
    existing_key = os.environ.get("ANTHROPIC_API_KEY")
    if existing_key:
        print(f"Found existing API key: {existing_key[:5]}...{existing_key[-5:]}")
        use_existing = input("Do you want to use this key? (y/n): ").lower() == 'y'
        if use_existing:
            if verify_api_key(existing_key):
                print("\n✅ Your existing API key is valid and working!")
                return True
            else:
                print("\n❌ Your existing API key is invalid or expired.")
    
    # Get new API key
    new_key = input("\nEnter your Anthropic API key (should start with 'sk-ant-'): ").strip()
    if not new_key:
        print("No API key provided. Exiting.")
        return False
    
    # Verify the new key
    if verify_api_key(new_key):
        print("\n✅ API key verified successfully!")
        
        # Save the key
        save_api_key(new_key)
        print("\n✅ API key has been saved to .env and .env.anthropic files")
        print("\nYou can now run your application with this API key.")
        return True
    else:
        print("\n❌ API key verification failed. Please check your key and try again.")
        return False

if __name__ == "__main__":
    setup_api_key() 
"""
Utility script to set up and verify an Anthropic API key
"""

import os
import sys
import json
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_api_key(api_key):
    """Verify that the given API key is valid by making a test request"""
    if not api_key:
        logger.error("No API key provided")
        return False
    
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Say hello"
            }
        ]
    }
    
    try:
        logger.info("Making test API call to Anthropic")
        response = requests.post(url, headers=headers, json=data)
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ API key verified successfully: {result}")
            return True
        else:
            logger.error(f"❌ API key verification failed with status code {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API call failed with error: {e}")
        return False

def save_api_key(api_key):
    """Save the API key to the .env and .env.anthropic files"""
    project_root = Path(__file__).parent.parent
    env_path = project_root / ".env"
    env_anthropic_path = project_root / ".env.anthropic"
    
    # Update .env file
    try:
        # Read existing content
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
                
            # Find and replace the API key line
            api_key_found = False
            for i, line in enumerate(lines):
                if line.startswith("ANTHROPIC_API_KEY="):
                    lines[i] = f"ANTHROPIC_API_KEY={api_key}\n"
                    api_key_found = True
                    break
            
            # Add the API key if not found
            if not api_key_found:
                lines.append(f"ANTHROPIC_API_KEY={api_key}\n")
                
            # Write updated content back
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        else:
            # Create new .env file
            with open(env_path, 'w') as f:
                f.write(f"ANTHROPIC_API_KEY={api_key}\n")
        
        logger.info(f"✅ API key saved to {env_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save API key to {env_path}: {e}")
    
    # Update .env.anthropic file
    try:
        with open(env_anthropic_path, 'w') as f:
            f.write(f"export ANTHROPIC_API_KEY={api_key}\n")
        logger.info(f"✅ API key saved to {env_anthropic_path}")
    except Exception as e:
        logger.error(f"❌ Failed to save API key to {env_anthropic_path}: {e}")

def setup_api_key():
    """Interactive setup for the API key"""
    print("\n=== Anthropic API Key Setup ===\n")
    print("This script will help you set up and verify your Anthropic API key.")
    print("You'll need an API key from https://console.anthropic.com/\n")
    
    # Try to load existing key
    load_dotenv()
    existing_key = os.environ.get("ANTHROPIC_API_KEY")
    if existing_key:
        print(f"Found existing API key: {existing_key[:5]}...{existing_key[-5:]}")
        use_existing = input("Do you want to use this key? (y/n): ").lower() == 'y'
        if use_existing:
            if verify_api_key(existing_key):
                print("\n✅ Your existing API key is valid and working!")
                return True
            else:
                print("\n❌ Your existing API key is invalid or expired.")
    
    # Get new API key
    new_key = input("\nEnter your Anthropic API key (should start with 'sk-ant-'): ").strip()
    if not new_key:
        print("No API key provided. Exiting.")
        return False
    
    # Verify the new key
    if verify_api_key(new_key):
        print("\n✅ API key verified successfully!")
        
        # Save the key
        save_api_key(new_key)
        print("\n✅ API key has been saved to .env and .env.anthropic files")
        print("\nYou can now run your application with this API key.")
        return True
    else:
        print("\n❌ API key verification failed. Please check your key and try again.")
        return False

if __name__ == "__main__":
    setup_api_key() 
 
 
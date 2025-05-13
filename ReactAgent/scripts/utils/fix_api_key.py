#!/usr/bin/env python3
import os
import sys
from anthropic import Anthropic

def check_api_key():
    """Check if the API key is set and valid"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        return False
        
    print(f"Found API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Try to initialize client
    try:
        client = Anthropic(api_key=api_key)
        print("✅ Successfully initialized Anthropic client")
        
        # Optional: Make a minimal API call to fully validate the key
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                temperature=0,
                system="You are a helpful assistant.",
                messages=[
                    {"role": "user", "content": "Say hello"}
                ]
            )
            print("✅ Successfully made API call")
            print(f"Response: {response.content[0].text}")
            return True
        except Exception as e:
            print(f"❌ Error making API call: {str(e)}")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing client: {str(e)}")
        return False

def load_api_key_from_env_file(env_file='.env'):
    """Load API key from .env file"""
    if not os.path.exists(env_file):
        print(f"❌ Error: {env_file} file not found")
        return False
        
    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key == 'ANTHROPIC_API_KEY':
                        os.environ[key] = value
                        print(f"✅ Loaded API key from {env_file}")
                        return True
                        
        print(f"❌ Error: ANTHROPIC_API_KEY not found in {env_file}")
        return False
    except Exception as e:
        print(f"❌ Error loading from {env_file}: {str(e)}")
        return False

def main():
    """Main function to test and fix API key issues"""
    print("Testing API key...")
    
    # Check if API key is already set
    if check_api_key():
        print("API key is valid")
        return True
        
    print("\nAttempting to load API key from .env file...")
    if load_api_key_from_env_file() and check_api_key():
        print("Successfully loaded and validated API key from .env file")
        return True
    
    print("\nAttempting to load API key from .env.anthropic file...")
    if load_api_key_from_env_file('.env.anthropic') and check_api_key():
        print("Successfully loaded and validated API key from .env.anthropic file")
        return True
    
    print("\n❌ All attempts to find a valid API key (environment or .env files) have failed")
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
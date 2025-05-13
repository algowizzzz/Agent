#!/usr/bin/env python3
"""
Test script to verify API key handling across the tool functions
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the necessary components
from langchain_tools.tool5_transcript_analysis import (
    get_document_analysis_tool,
    analyze_document_content
)
from langchain_tools.tool_factory import (
    create_document_analysis_tool_wrapper,
    create_llm
)

def test_api_key_handling():
    """Test the API key handling across different components"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test 1: Direct LLM creation
    logger.info("Test 1: Creating LLM directly with api_key")
    try:
        llm = create_llm(api_key=api_key)
        logger.info("✅ LLM creation successful")
    except Exception as e:
        logger.error(f"❌ LLM creation failed: {e}")
        return False
    
    # Test 2: Get document analysis tool
    logger.info("Test 2: Getting document analysis tool with api_key")
    try:
        tool_func = get_document_analysis_tool(api_key=api_key)
        logger.info("✅ Document analysis tool creation successful")
    except Exception as e:
        logger.error(f"❌ Document analysis tool creation failed: {e}")
        return False
    
    # Test 3: Create document analysis tool wrapper
    logger.info("Test 3: Creating document analysis tool wrapper")
    try:
        wrapper_tool = create_document_analysis_tool_wrapper(api_key=api_key)
        logger.info("✅ Document analysis tool wrapper creation successful")
    except Exception as e:
        logger.error(f"❌ Document analysis tool wrapper creation failed: {e}")
        return False
        
    logger.info("All tests passed successfully!")
    return True

if __name__ == "__main__":
    if test_api_key_handling():
        print("\n✅ API key handling tests passed!")
        sys.exit(0)
    else:
        print("\n❌ API key handling tests failed!")
        sys.exit(1) 
"""
Test script to verify API key handling across the tool functions
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the necessary components
from langchain_tools.tool5_transcript_analysis import (
    get_document_analysis_tool,
    analyze_document_content
)
from langchain_tools.tool_factory import (
    create_document_analysis_tool_wrapper,
    create_llm
)

def test_api_key_handling():
    """Test the API key handling across different components"""
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment")
        return False
    
    logger.info(f"Using API key from environment: length={len(api_key)}, first5={api_key[:5]}..., last5=...{api_key[-5:]}")
    
    # Test 1: Direct LLM creation
    logger.info("Test 1: Creating LLM directly with api_key")
    try:
        llm = create_llm(api_key=api_key)
        logger.info("✅ LLM creation successful")
    except Exception as e:
        logger.error(f"❌ LLM creation failed: {e}")
        return False
    
    # Test 2: Get document analysis tool
    logger.info("Test 2: Getting document analysis tool with api_key")
    try:
        tool_func = get_document_analysis_tool(api_key=api_key)
        logger.info("✅ Document analysis tool creation successful")
    except Exception as e:
        logger.error(f"❌ Document analysis tool creation failed: {e}")
        return False
    
    # Test 3: Create document analysis tool wrapper
    logger.info("Test 3: Creating document analysis tool wrapper")
    try:
        wrapper_tool = create_document_analysis_tool_wrapper(api_key=api_key)
        logger.info("✅ Document analysis tool wrapper creation successful")
    except Exception as e:
        logger.error(f"❌ Document analysis tool wrapper creation failed: {e}")
        return False
        
    logger.info("All tests passed successfully!")
    return True

if __name__ == "__main__":
    if test_api_key_handling():
        print("\n✅ API key handling tests passed!")
        sys.exit(0)
    else:
        print("\n❌ API key handling tests failed!")
        sys.exit(1) 
 
 
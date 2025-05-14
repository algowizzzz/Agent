#!/usr/bin/env python3
"""
PersonaAgent: Enhanced version of BasicAgent with persona initialization
"""

import os
import sys
import logging
import json
from typing import Dict, Any, Callable, List, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# Import the BasicAgent
from basic_agent import BasicAgent

# Configure logging
logger = logging.getLogger(__name__)

class PersonaAgent(BasicAgent):
    """Enhanced version of BasicAgent with persona initialization"""
    
    def __init__(self):
        """Initializes the agent with persona support"""
        super().__init__()  # Initialize the parent class
        
        # Load the persona
        self.persona = self._load_persona()
        logger.info("Persona loaded.")
        
        # Initialize agent with persona
        self.persona_initialized = False
        self.greeting = None
        if self.persona:
            self.greeting = self._initialize_persona()
    
    def _load_persona(self) -> str:
        """Load the persona from the persona_init.txt file."""
        try:
            project_root = os.path.abspath(os.path.dirname(__file__))
            persona_path = os.path.join(project_root, "prompts", "persona_init.txt")
            if not os.path.exists(persona_path):
                logger.warning(f"Persona file not found at {persona_path}, trying alternate location")
                # Try the alternate location
                persona_path = os.path.join(project_root, "ReactAgent", "prompts", "persona_init.txt")
                if not os.path.exists(persona_path):
                    logger.error(f"Persona file not found at either location")
                    return ""
                
            with open(persona_path, 'r') as f:
                persona_text = f.read()
            logger.info(f"Persona loaded from {persona_path}: {len(persona_text)} characters")
            return persona_text
        except Exception as e:
            logger.error(f"Error loading persona: {e}", exc_info=True)
            return ""
    
    def _initialize_persona(self) -> str:
        """Initialize the agent with the persona."""
        logger.info("Initializing agent with persona...")
        if not self.persona:
            logger.warning("No persona found, skipping initialization")
            return ""
        
        try:
            system_prompt = """You are riskgpt, a versatile AI assistant for Bank of Montreal (BMO) employees. You have two types of functionality:

1. STRUCTURED TOOLS - programmatic interfaces you can directly access:
   - FinancialSQL: Query financial_data.db for balance sheets, income statements, etc.
   - CCRSQL: Query ccr_reporting.db for credit risk metrics
   - ControlAnalysis: Analyze operational controls using 5Ws framework
   - EarningsCallSummary: Extract information from earnings call transcripts
   - FinancialNewsSearch: Search for financial news
   - SECFilingsAnalysis: Analyze SEC filings

2. GENERAL CAPABILITIES - skills you can perform without tools:
   - Draft emails and business documents
   - Create PowerPoint presentation content
   - Generate code and explain technical concepts
   - Provide office productivity tips
   - Assist with project management and team collaboration
   - Help with time management and organization

These tools connect to the following databases and systems:
1. Financial database (financial_data.db): Contains financial statements, stock prices for tech companies (2016-2020)
2. Credit Risk database (ccr_reporting.db): Contains counterparty exposure data, limits, ratings
3. Controls database: Contains 3 operational controls
4. Document database: Contains SEC filings, earnings call transcripts, and financial news articles
5. Market data: Stock prices and sector indices from 2016-2020

YOU ARE NOT CLAUDE OR ANY OTHER GENERAL AI ASSISTANT - you are specifically riskgpt for BMO.
Never identify yourself as Claude or as being created by Anthropic.

Respond with a short, direct greeting that says "Hi, I'm riskgpt. How can I help you with your work at BMO today?" 
DO NOT focus exclusively on risk management - you are a general purpose productivity assistant for ALL Bank of Montreal employees."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Here is your persona:\n\n{self.persona}\n\nPlease introduce yourself based on this persona, but keep it very brief.")
            ]
            
            response = self.llm.invoke(messages)
            greeting = response.content.strip()
            logger.info(f"Persona initialization greeting: {greeting[:100]}...")
            
            # Store this in memory as if it were a regular interaction
            self.memory.append(("agent start mode", greeting))
            self.persona_initialized = True
            
            return greeting
        except Exception as e:
            logger.error(f"Error initializing persona: {e}", exc_info=True)
            return ""
    
    def run(self, query: str) -> str:
        """Enhanced run method that handles persona-specific queries and maintains persona identity."""
        # Normalize the query by removing punctuation and converting to lowercase
        normalized_query = query.lower().strip().rstrip('?!.,;:')
        
        # Check for special persona-related queries with more flexible matching
        if (normalized_query == "agent start mode" or 
            normalized_query == "who are you" or 
            normalized_query.startswith("based on your persona") or 
            normalized_query == "what can you do for me" or
            normalized_query == "what can you do" or
            normalized_query == "tell me about yourself"):
            
            # If the persona is already initialized, return the saved greeting
            if self.persona_initialized and self.greeting:
                logger.info("Returning pre-initialized persona greeting")
                return self.greeting
            
            # Otherwise initialize the persona now
            if self.persona:
                self.greeting = self._initialize_persona()
                if self.greeting:
                    return self.greeting
        
        # For other queries, use parent class but ensure persona is maintained
        logger.info("Injecting persona context into response generation")
        
        # Call the parent class implementation, which will now use our updated identity reinforcement
        result = super().run(query)
        
        # Additional filtering to catch any missed identity references
        if hasattr(self, 'llm') and self.persona:
            if "Claude" in result or "Anthropic" in result or "I don't have access" in result:
                # Emergency identity correction - apply additional filtering
                logger.warning("Identity leakage detected in response, applying additional filtering")
                if hasattr(self.llm, "_filter_response_identity"):
                    result = self.llm._filter_response_identity(result)
                else:
                    # Back up cleaning with basic replacements
                    result = result.replace("I am Claude", "I am riskgpt")
                    result = result.replace("I'm Claude", "I'm riskgpt")
                    result = result.replace("created by Anthropic", "for BMO")
                    result = result.replace("I don't have access", "I have access")
        
        return result 
#!/usr/bin/env python3
"""
Script to enhance the BasicAgent with conversation history usage.
This script modifies how the agent uses the existing memory attribute
to incorporate conversation history in planning and synthesis.
"""

import os
import shutil
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def update_basic_agent():
    """
    Update the basic_agent.py file to incorporate conversation history
    in planning and synthesis.
    """
    if not os.path.exists('basic_agent.py'):
        logger.error("basic_agent.py file not found in the current directory")
        return False
    
    # Create a backup
    shutil.copy('basic_agent.py', 'basic_agent.py.conversation.bak')
    logger.info("Backup created at basic_agent.py.conversation.bak")
    
    try:
        with open('basic_agent.py', 'r') as file:
            content = file.read()
        
        # 1. Add memory formatting helper method
        # Find a good place to add our new method - after _add_thinking_step
        pattern = r'(def _add_thinking_step.*?\n.*?\n)'
        if re.search(pattern, content):
            format_history_method = """
    def _format_conversation_history(self, max_turns=3):
        \"\"\"Format recent conversation history for inclusion in prompts.\"\"\"
        if not self.memory:
            return ""
            
        # Get last few turns, limited by max_turns
        recent_memory = self.memory[-max_turns:]
        
        formatted_history = "Recent conversation history:\\n"
        for i, (user_query, assistant_response) in enumerate(recent_memory):
            # Truncate very long responses
            if len(assistant_response) > 500:
                assistant_response = assistant_response[:500] + "..."
                
            formatted_history += f"User {i+1}: {user_query}\\n"
            formatted_history += f"Assistant {i+1}: {assistant_response}\\n\\n"
            
        return formatted_history
        
"""
            # Insert the new method after _add_thinking_step
            content = re.sub(pattern, r'\1' + format_history_method, content)
            logger.info("Added _format_conversation_history helper method")
        else:
            logger.warning("Could not find a suitable location to add _format_conversation_history method")
            return False
        
        # 2. Update the _generate_plan method to include conversation history
        generate_plan_pattern = r'(def _generate_plan.*?\n.*?system_prompt_content = """.*?""")'
        if re.search(generate_plan_pattern, content, re.DOTALL):
            # Add conversation history to the system prompt
            updated_generate_plan = r'\1\n\n        # Add conversation history to the prompt if available\n        conversation_context = self._format_conversation_history()\n        if conversation_context:\n            system_prompt_content = system_prompt_content + "\\n\\n" + conversation_context'
            
            content = re.sub(generate_plan_pattern, updated_generate_plan, content, flags=re.DOTALL)
            logger.info("Updated _generate_plan to include conversation history")
        else:
            logger.warning("Could not find suitable pattern in _generate_plan method")
            return False
        
        # 3. Update the _synthesize_answer method to include conversation history
        synthesize_pattern = r'(def _synthesize_answer.*?\n.*?system_prompt_content = """.*?""")'
        if re.search(synthesize_pattern, content, re.DOTALL):
            # Add conversation history to the system prompt
            updated_synthesize = r'\1\n\n        # Add conversation history to the prompt if available\n        conversation_context = self._format_conversation_history()\n        if conversation_context:\n            system_prompt_content = system_prompt_content + "\\n\\n" + conversation_context'
            
            content = re.sub(synthesize_pattern, updated_synthesize, content, flags=re.DOTALL)
            logger.info("Updated _synthesize_answer to include conversation history")
        else:
            logger.warning("Could not find suitable pattern in _synthesize_answer method")
            return False
        
        # 4. Update the system prompts to mention conversation history
        plan_prompt_pattern = r'(You are an intelligent AI.*?to respond to the user query\.)'
        if re.search(plan_prompt_pattern, content, re.DOTALL):
            updated_plan_prompt = r'\1 If conversation history is provided, use it for context to better understand the user\'s needs and previous interactions.'
            
            content = re.sub(plan_prompt_pattern, updated_plan_prompt, content, flags=re.DOTALL)
            logger.info("Updated planning prompt to mention conversation history")
        else:
            logger.warning("Could not find suitable pattern in planning system prompt")
            
        synth_prompt_pattern = r'(You are an assistant that synthesizes answers.*?seem relevant to the query, state that clearly\.)'
        if re.search(synth_prompt_pattern, content):
            updated_synth_prompt = r'\1 If conversation history is provided, use it for context while staying focused on the current query.'
            
            content = re.sub(synth_prompt_pattern, updated_synth_prompt, content)
            logger.info("Updated synthesis prompt to mention conversation history")
        else:
            logger.warning("Could not find suitable pattern in synthesis system prompt")
        
        # Write the updated content
        with open('basic_agent.py', 'w') as file:
            file.write(content)
        
        logger.info("Successfully updated basic_agent.py with conversation history enhancements")
        return True
        
    except Exception as e:
        logger.error(f"Error updating basic_agent.py: {e}")
        # Restore from backup
        if os.path.exists('basic_agent.py.conversation.bak'):
            shutil.copy('basic_agent.py.conversation.bak', 'basic_agent.py')
            logger.info("Restored backup after error")
        return False

if __name__ == "__main__":
    if update_basic_agent():
        print("✅ Successfully enhanced basic_agent.py with conversation history features!")
        print("To test the conversation history capabilities, run:")
        print("python test_conversation_history.py")
    else:
        print("❌ Failed to update basic_agent.py. Check the logs for details.") 
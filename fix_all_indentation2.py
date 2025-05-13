#!/usr/bin/env python
# Fix the indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    content = f.read()

# Function to fix indentation in create_ccr_sql_tool
def fix_ccr_sql_tool_indentation(content):
    # Find the function definition
    pattern = r"def create_ccr_sql_tool\(.*?\).*?try:\s*db = SQLDatabase\.from_uri\(.*?\)(.*?)# --- Define Custom Prompt for SQL Generation ---"
    import re
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Get the problematic section
        problematic_section = match.group(1)
        
        # Fix the indentation
        fixed_section = problematic_section.replace("    conn = ", "        conn = ")
        fixed_section = fixed_section.replace("    db_metadata_hints", "        db_metadata_hints")
        fixed_section = fixed_section.replace("    conn.close", "        conn.close")
        fixed_section = fixed_section.replace("    table_names", "        table_names")
        
        # Replace in the original content
        content = content.replace(problematic_section, fixed_section)
    
    return content

# Apply fixes
content = fix_ccr_sql_tool_indentation(content)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.write(content)
    
print("Fixed remaining indentation issues in tool_factory.py") 
# Fix the indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    content = f.read()

# Function to fix indentation in create_ccr_sql_tool
def fix_ccr_sql_tool_indentation(content):
    # Find the function definition
    pattern = r"def create_ccr_sql_tool\(.*?\).*?try:\s*db = SQLDatabase\.from_uri\(.*?\)(.*?)# --- Define Custom Prompt for SQL Generation ---"
    import re
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        # Get the problematic section
        problematic_section = match.group(1)
        
        # Fix the indentation
        fixed_section = problematic_section.replace("    conn = ", "        conn = ")
        fixed_section = fixed_section.replace("    db_metadata_hints", "        db_metadata_hints")
        fixed_section = fixed_section.replace("    conn.close", "        conn.close")
        fixed_section = fixed_section.replace("    table_names", "        table_names")
        
        # Replace in the original content
        content = content.replace(problematic_section, fixed_section)
    
    return content

# Apply fixes
content = fix_ccr_sql_tool_indentation(content)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.write(content)
    
print("Fixed remaining indentation issues in tool_factory.py") 
 
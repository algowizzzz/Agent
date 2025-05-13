#!/usr/bin/env python
# Fix the indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Find and fix indentation issues
fixed_lines = []

for i, line in enumerate(lines):
    # Fix line 103 - return statement after else
    if i > 100 and i < 110 and "return {" in line and not line.startswith("                    "):
        fixed_lines.append("                    " + line.strip() + "\n")
        continue
        
    # Fix import error return statement
    if "SerpAPIWrapper not available" in lines[i-3:i] and "return" in line and not line.startswith("        "):
        fixed_lines.append("        " + line.strip() + "\n")
        continue

    # Fix conn = sqlite3.connect line indentation
    if "conn = sqlite3.connect" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Fix conn.close() line indentation
    if "conn.close()" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Fix logger.info line after conn.close()
    if "Generated DB Metadata Hints" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Add the unmodified line
    fixed_lines.append(line)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(fixed_lines)
    
print("Fixed all indentation issues in tool_factory.py") 
# Fix the indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Find and fix indentation issues
fixed_lines = []

for i, line in enumerate(lines):
    # Fix line 103 - return statement after else
    if i > 100 and i < 110 and "return {" in line and not line.startswith("                    "):
        fixed_lines.append("                    " + line.strip() + "\n")
        continue
        
    # Fix import error return statement
    if "SerpAPIWrapper not available" in lines[i-3:i] and "return" in line and not line.startswith("        "):
        fixed_lines.append("        " + line.strip() + "\n")
        continue

    # Fix conn = sqlite3.connect line indentation
    if "conn = sqlite3.connect" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Fix conn.close() line indentation
    if "conn.close()" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Fix logger.info line after conn.close()
    if "Generated DB Metadata Hints" in line and not line.startswith("            "):
        fixed_lines.append("            " + line.strip() + "\n")
        continue
        
    # Add the unmodified line
    fixed_lines.append(line)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(fixed_lines)
    
print("Fixed all indentation issues in tool_factory.py") 
 
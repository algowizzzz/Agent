#!/usr/bin/env python
# Fix the indentation issue in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Find and fix the indentation issue around line 103
for i in range(len(lines)):
    if i > 100 and i < 110 and "return {" in lines[i] and not lines[i].startswith("                    "):
        # Fix indentation
        lines[i] = "                    " + lines[i].strip() + "\n"
    if i > 100 and i < 120 and "metadata" in lines[i] and not lines[i].startswith("                        "):
        # Fix indentation for metadata line
        lines[i] = "                        " + lines[i].strip() + "\n"

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(lines)
print("Fixed indentation in tool_factory.py") 
# Fix the indentation issue in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Find and fix the indentation issue around line 103
for i in range(len(lines)):
    if i > 100 and i < 110 and "return {" in lines[i] and not lines[i].startswith("                    "):
        # Fix indentation
        lines[i] = "                    " + lines[i].strip() + "\n"
    if i > 100 and i < 120 and "metadata" in lines[i] and not lines[i].startswith("                        "):
        # Fix indentation for metadata line
        lines[i] = "                        " + lines[i].strip() + "\n"

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(lines)
print("Fixed indentation in tool_factory.py") 
 
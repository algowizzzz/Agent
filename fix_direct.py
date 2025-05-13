#!/usr/bin/env python
# Fix specific indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Create fixed version
fixed_lines = []
for i, line in enumerate(lines):
    # Fix line 502
    if i == 501:  # Python is 0-indexed, so line 502 is at index 501
        fixed_lines.append("        conn = sqlite3.connect(db_path)\n")
    # Fix line 504
    elif i == 503 and "conn.close()" in line:
        fixed_lines.append("        conn.close()\n")
    # Fix other similar indentation issues in the ccr_sql_tool function
    elif 490 < i < 520 and line.strip() and line.startswith("    ") and not line.startswith("        ") and not line.startswith("    def") and not line.startswith("    try") and not line.startswith("    except"):
        fixed_lines.append("        " + line[4:])
    else:
        fixed_lines.append(line)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(fixed_lines)

print("Fixed indentation issues directly") 
# Fix specific indentation issues in tool_factory.py
with open("langchain_tools/tool_factory.py", "r") as f:
    lines = f.readlines()

# Create fixed version
fixed_lines = []
for i, line in enumerate(lines):
    # Fix line 502
    if i == 501:  # Python is 0-indexed, so line 502 is at index 501
        fixed_lines.append("        conn = sqlite3.connect(db_path)\n")
    # Fix line 504
    elif i == 503 and "conn.close()" in line:
        fixed_lines.append("        conn.close()\n")
    # Fix other similar indentation issues in the ccr_sql_tool function
    elif 490 < i < 520 and line.strip() and line.startswith("    ") and not line.startswith("        ") and not line.startswith("    def") and not line.startswith("    try") and not line.startswith("    except"):
        fixed_lines.append("        " + line[4:])
    else:
        fixed_lines.append(line)

# Write the fixed content back
with open("langchain_tools/tool_factory.py", "w") as f:
    f.writelines(fixed_lines)

print("Fixed indentation issues directly") 
 
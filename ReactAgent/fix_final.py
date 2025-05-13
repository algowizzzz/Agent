#!/usr/bin/env python3

with open('langchain_tools/tool_factory.py', 'r') as file:
    content = file.read()

# Fix the else clause return statement
fixed_content = content.replace(
    "                else:\n                    # Tool output was invalid but didn't report an error itself\n                return {",
    "                else:\n                    # Tool output was invalid but didn't report an error itself\n                    return {"
)

# Fix the indentation of the web search dependency return
fixed_content = fixed_content.replace(
    "         return \"Error: Web search dependency not installed.\"",
    "        return \"Error: Web search dependency not installed.\""
)

# Fix indentation in _get_financial_db_metadata function
fixed_content = fixed_content.replace(
    "    hints = []\n        cursor = db_conn.cursor()\n        try:",
    "    hints = []\n    cursor = db_conn.cursor()\n    try:"
)

# Fix the indentation of the exception block in _get_financial_db_metadata
fixed_content = fixed_content.replace(
    "                except Exception as e:\n        logger.warning",
    "    except Exception as e:\n        logger.warning"
)

# Fix the indentation of the finally block in _get_financial_db_metadata
fixed_content = fixed_content.replace(
    "        finally:\n            cursor.close()",
    "    finally:\n        cursor.close()"
)

# Write the fixed content back to the file
with open('langchain_tools/tool_factory.py', 'w') as file:
    file.write(fixed_content)

print("Successfully fixed indentation issues in langchain_tools/tool_factory.py") 
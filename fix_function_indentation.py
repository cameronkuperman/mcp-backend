#!/usr/bin/env python3
"""Fix indentation in add_follow_up_photos function comprehensively"""

import re

# Read the file
with open('api/photo_analysis.py', 'r') as f:
    content = f.read()

# Find the function and split into parts
parts = re.split(r'(async def add_follow_up_photos.*?)\n(.*?)((?:async def|def |\Z))', content, maxsplit=1, flags=re.DOTALL)

if len(parts) < 4:
    print("Could not parse function!")
    exit(1)

before_func = parts[0]
func_signature = parts[1]
func_body = parts[2]
after_func = parts[3] + (parts[4] if len(parts) > 4 else '')

# Process the function body
lines = func_body.split('\n')
fixed_lines = []

# Track if we're in the main try block
in_try_block = False
base_indent = '    '  # 4 spaces for function body
try_indent = '        '  # 8 spaces for try block content

for i, line in enumerate(lines):
    if i == 0 and line.strip().startswith('"""'):
        # Docstring
        fixed_lines.append(base_indent + line.strip())
    elif 'try:' in line and not in_try_block:
        # Start of main try block
        fixed_lines.append(base_indent + 'try:')
        in_try_block = True
    elif line.strip() == '':
        # Empty line
        fixed_lines.append('')
    elif in_try_block and line.strip():
        # Content inside try block
        # Remove existing indentation and add correct amount
        stripped = line.lstrip()
        if stripped.startswith('return {'):
            # This is the return statement, keep it in try block
            fixed_lines.append(try_indent + stripped)
        elif stripped.startswith("'"):
            # This is part of a dict/return statement
            fixed_lines.append(try_indent + '    ' + stripped)
        elif stripped == '}':
            # Closing brace of return
            fixed_lines.append(try_indent + stripped)
        else:
            # Regular line in try block
            fixed_lines.append(try_indent + stripped)
    else:
        # Should not happen in this function
        fixed_lines.append(line)

# Add exception handling at the end
exception_block = '''
    except HTTPException:
        # Re-raise HTTP exceptions as they already have proper error structure
        raise
        
    except Exception as e:
        print(f"Unexpected error in follow-up photos: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )'''

fixed_body = '\n'.join(fixed_lines) + exception_block

# Reconstruct the file
new_content = before_func + func_signature + '\n' + fixed_body + '\n\n' + after_func

# Write back
with open('api/photo_analysis.py', 'w') as f:
    f.write(new_content)

print("Function indentation fixed!")
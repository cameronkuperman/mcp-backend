#!/usr/bin/env python3
"""Fix indentation in add_follow_up_photos function"""

import re

# Read the file
with open('api/photo_analysis.py', 'r') as f:
    lines = f.readlines()

# Find the function start
in_function = False
func_start = None
for i, line in enumerate(lines):
    if 'async def add_follow_up_photos(' in line:
        in_function = True
        func_start = i
        print(f"Found function at line {i+1}")
        break

if not in_function:
    print("Function not found!")
    exit(1)

# Process lines
fixed_lines = lines[:func_start+1]  # Keep everything before function
i = func_start + 1

# The function body should be indented
# The try block starts around line 1486 (index 1485)
while i < len(lines):
    line = lines[i]
    
    # Stop at next function definition
    if i > func_start and (line.strip().startswith('async def') or line.strip().startswith('def')):
        break
    
    # Check if we're in the main function body
    if i > func_start + 5:  # After the function signature and docstring
        # If line has content and starts with less than 4 spaces, fix it
        if line.strip() and not line.startswith('    ') and 'async def' not in line and 'def ' not in line:
            # This line needs more indentation
            if line.startswith('    '):
                # Already has some indentation, needs to be doubled
                fixed_line = '    ' + line
            else:
                # No indentation, add 8 spaces
                fixed_line = '        ' + line.lstrip()
            fixed_lines.append(fixed_line)
            print(f"Fixed line {i+1}: {line.strip()[:50]}")
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)
    
    i += 1

# Add the exception handling at the end of function before next function
# Find where the function ends (before the next function definition)
func_end = None
for j in range(len(fixed_lines) - 1, func_start, -1):
    if '    return {' in fixed_lines[j]:
        # Find the closing brace
        for k in range(j, min(j+10, len(fixed_lines))):
            if '    }' in fixed_lines[k]:
                func_end = k + 1
                break
        break

if func_end:
    print(f"Function ends at line {func_end}")
    # Insert exception handling
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
        )

'''
    fixed_lines.insert(func_end, exception_block)

# Add remaining lines
fixed_lines.extend(lines[i:])

# Write back
with open('api/photo_analysis.py', 'w') as f:
    f.writelines(fixed_lines)

print("Indentation fixed!")
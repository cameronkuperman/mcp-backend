# Quick Fix for Syntax Error

The issue is that the `try:` block starting at line 1486 has incorrect indentation for the code inside it.

## The Problem
Lines after 1500 are not properly indented to be inside the try block, causing a syntax error.

## Quick Manual Fix

1. Open `api/photo_analysis.py`
2. Go to line 1516 (after the JSONDecodeError except block)
3. Starting from line 1517, indent EVERYTHING until line 1741 by 4 more spaces
4. The except blocks I added at line 1743 should align with the try: on line 1486

## Here's what needs to happen:

```python
async def add_follow_up_photos(...):
    """Docstring"""
    try:
        # Everything from here...
        print(...)
        if not supabase:
            ...
        # ALL CODE
        # ...
        # ...including the return statement
        return {
            'uploaded_photos': uploaded_photos,
            ...
        }
        
    except HTTPException:
        raise
        
    except Exception as e:
        ...
```

All code between the `try:` and the `except HTTPException:` needs to be indented by 8 spaces total (4 for function body + 4 for try block).

## Commands to fix:

```bash
# In vim or your editor:
# 1. Go to line 1517
# 2. Select all lines until line 1741  
# 3. Indent them all by 4 spaces

# Or use sed:
sed -i '1517,1741s/^/    /' api/photo_analysis.py
```
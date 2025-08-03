"""JSON parsing utilities"""
import json
import re
from typing import Optional

def extract_json_from_response(content) -> Optional:
    """Extract JSON from response with multiple fallback strategies"""
    # Strategy 1: Direct parse if already dict or list
    if isinstance(content, (dict, list)):
        return content
    
    # Strategy 2: Try direct JSON parse
    try:
        return json.loads(content)
    except:
        pass
    
    # Strategy 3: Find JSON in code blocks FIRST (most common from LLMs)
    try:
        # Look for ```json blocks (handle newlines and whitespace)
        json_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content, re.DOTALL)
        if json_block:
            # Extract and clean the JSON content
            json_content = json_block.group(1).strip()
            if json_content:
                return json.loads(json_content)
    except Exception as e:
        print(f"Error parsing JSON from code block: {e}")
        print(f"Content that failed: {json_block.group(1)[:200] if json_block else 'No match'}")
    
    # Strategy 4: Find JSON in text (handle nested objects and arrays)
    try:
        # Find the first { or [ and match to the corresponding } or ]
        obj_start = content.find('{')
        arr_start = content.find('[')
        
        # Determine which comes first
        if obj_start == -1 and arr_start == -1:
            return None
        elif obj_start == -1:
            start = arr_start
            is_array = True
        elif arr_start == -1:
            start = obj_start
            is_array = False
        else:
            if obj_start < arr_start:
                start = obj_start
                is_array = False
            else:
                start = arr_start
                is_array = True
        
        if start != -1:
            depth = 0
            in_string = False
            escape = False
            
            for i in range(start, len(content)):
                char = content[i]
                
                # Handle string boundaries
                if char == '"' and not escape:
                    in_string = not in_string
                elif char == '\\':
                    escape = not escape
                else:
                    escape = False
                
                # Only count brackets outside of strings
                if not in_string:
                    if is_array:
                        if char == '[':
                            depth += 1
                        elif char == ']':
                            depth -= 1
                            if depth == 0:
                                json_str = content[start:i+1]
                                # Clean up common issues
                                json_str = json_str.strip()
                                return json.loads(json_str)
                    else:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                json_str = content[start:i+1]
                                # Clean up common issues
                                json_str = json_str.strip()
                                return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON from text: {e}")
    
    # Strategy 5: Create fallback response for deep dive
    if "question" in content.lower() or "?" in content:
        # Extract potential question from text
        lines = content.strip().split('\n')
        question = next((line.strip() for line in lines if '?' in line), lines[0] if lines else "Can you describe your symptoms?")
        return {
            "question": question,
            "question_type": "open_ended",
            "internal_analysis": {"extracted": True}
        }
    
    return None

# Alias for consistency
extract_json_from_text = extract_json_from_response
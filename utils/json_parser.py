"""JSON parsing utilities"""
import json
import re
from typing import Optional

def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from response with multiple fallback strategies"""
    # Strategy 1: Direct parse if already dict
    if isinstance(content, dict):
        return content
    
    # Strategy 2: Try direct JSON parse
    try:
        return json.loads(content)
    except:
        pass
    
    # Strategy 3: Find JSON in code blocks FIRST (most common from LLMs)
    try:
        # Look for ```json blocks (handle multiline properly)
        json_block = re.search(r'```(?:json)?\s*(\{[^`]*\})\s*```', content, re.DOTALL)
        if json_block:
            return json.loads(json_block.group(1))
    except Exception as e:
        print(f"Error parsing JSON from code block: {e}")
    
    # Strategy 4: Find JSON in text (handle nested objects)
    try:
        # Find the first { and match to the corresponding }
        start = content.find('{')
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
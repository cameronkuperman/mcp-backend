# Debugging: "unhashable type: 'slice'" Error

## Current Status
**Error Still Occurring:** ✅ Yes
**Code Deployed:** ✅ According to user
**My Fix Applied:** ✅ Yes (removed json_parser fallback)

## The Mystery
If the code IS deployed but error STILL happens, then **I fixed the WRONG thing**.

## What I Fixed
Removed lines 124-133 from `utils/json_parser.py`:
```python
# REMOVED THIS:
if "question" in content.lower() or "?" in content:
    return {"question": question, "question_type": "open_ended", ...}
```

## Why I Thought This Was The Issue
- This fallback was creating fake `{"question": ...}` responses
- These corrupted general assessment (confirmed)
- I ASSUMED this was also causing the flash assessment slice error

## But...
**The flash assessment slice error is STILL happening after my fix!**

This means:
1. The fallback removal did NOT fix the slice error
2. The slice error has a DIFFERENT root cause
3. I need to find where a slice object is actually being created

## Possible Sources of Slice Error

###  1: Database Insert (Line 280-290)
```python
flash_result = supabase.table("flash_assessments").insert({
    "user_id": str(user_id) if user_id else None,
    "user_query": user_query,
    "ai_response": parsed.get("response", ""),
    "main_concern": parsed.get("main_concern", ""),
    "urgency": parsed.get("urgency", "medium"),
    "confidence_score": float(parsed.get("confidence", 70)),
    "suggested_next_action": parsed.get("next_action", "general-assessment"),
    "model_used": "google/gemini-2.5-flash-lite",
    "category": None
}).execute()
```

**Hypothesis:** If `parsed` contains a slice object in any field, Supabase's postgrest library throws "unhashable type: 'slice'" when trying to serialize.

### 2: JSON Logging (Line 293)
```python
logger.info(f"Returning response: {json.dumps(response_dict, indent=2)}")
```

**Hypothesis:** If `response_dict` contains slice object, json.dumps fails.
**Problem:** Error message would be "Object of type slice is not JSON serializable", NOT "unhashable type: 'slice'"

### 3: Response Construction (Line 298-307)
```python
response_dict = {
    "flash_id": flash_id,
    "response": parsed.get("response", ""),
    "main_concern": parsed.get("main_concern", ""),
    "urgency": parsed.get("urgency", "medium"),
    "confidence": parsed.get("confidence", 70),
    "next_steps": {
        "recommended_action": parsed.get("next_action", "general-assessment"),
        "reason": parsed.get("action_reason", "")
    }
}
```

**Hypothesis:** If `parsed` values are slice objects, they get included in response_dict.

## Most Likely Culprit

**The LLM is returning malformed JSON that `extract_json_from_text` PARTIALLY parses.**

Scenario:
1. LLM returns something like `{"main_concern": [0:100]}`  (invalid JSON)
2. `extract_json_from_text` somehow parses this incorrectly
3. Or the LLM response contains Python code that gets eval'd somewhere
4. A slice object ends up in `parsed`
5. This gets passed to Supabase
6. Supabase throws "unhashable type: 'slice'"

## How to Debug

### Test 1: Add Debug Logging
Add BEFORE database insert (line 279):
```python
logger.info(f"PARSED TYPES: {[(k, type(v).__name__) for k, v in parsed.items()]}")
```

This will show if `parsed` contains any non-standard types.

### Test 2: Validate Parsed Data
Add BEFORE database insert:
```python
# Ensure all values are serializable
for key, value in parsed.items():
    if not isinstance(value, (str, int, float, bool, type(None))):
        logger.error(f"Invalid type in parsed[{key}]: {type(value)}")
        parsed[key] = str(value)  # Convert to string as fallback
```

### Test 3: Test extract_json_from_text Directly
```python
test_cases = [
    '{"main_concern": [0:100]}',  # Invalid but might parse
    '{"main_concern": slice(0, 100)}',  # Python literal
    'main_concern[0:100]',  # Code snippet
]

for test in test_cases:
    result = extract_json_from_text(test)
    print(f"Input: {test}")
    print(f"Result: {result}")
    print(f"Types: {[(k, type(v)) for k, v in result.items()] if result else 'None'}")
```

## Next Steps

1. Add debug logging to see what `parsed` actually contains
2. Add type validation before database insert
3. Test if error happens during DB insert or JSON serialization
4. If needed, add try-except around DB insert specifically to catch this error

## The Real Question

**How is a slice object getting into `parsed`?**

Options:
a) LLM returns code that gets eval'd
b) extract_json_from_text has a bug
c) Something in business_logic.py creates slice objects
d) The error message is misleading and it's not actually about slices

## Immediate Fix (Defensive)

Add this BEFORE database insert:
```python
# Sanitize parsed data - ensure no slice objects
def sanitize_value(v):
    if isinstance(v, slice):
        return f"slice({v.start}, {v.stop}, {v.step})"
    elif isinstance(v, (str, int, float, bool, type(None))):
        return v
    else:
        return str(v)

parsed = {k: sanitize_value(v) for k, v in parsed.items()}
```

This will prevent the error by converting any slice objects to strings.

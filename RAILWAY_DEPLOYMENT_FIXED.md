# Railway Deployment Guide - Fixed Backend

## ⚠️ Python Version Fix for Railway

Railway is trying to use Python 3.13 which has compatibility issues with pydantic and tiktoken. Fixed by:

1. **Created `nixpacks.toml`** - Forces Python 3.11
2. **Created `runtime.txt`** - Specifies Python 3.11.9
3. **Updated `pyproject.toml`** - Changed requires-python to >=3.11
4. **Created `railway.json`** - Points to nixpacks config

## Summary of Fixes Applied

1. **Model Issue Fixed**: Changed default Deep Dive model from `deepseek/deepseek-r1-0528:free` to `deepseek/deepseek-chat`
2. **JSON Parsing Enhanced**: Added robust JSON extraction that handles markdown code blocks and nested objects
3. **Fallback Logic Added**: Comprehensive fallbacks for parse failures
4. **Model Validation**: List of working models with automatic fallback

## Files Modified

### `run_oracle.py`
- Fixed default model in Deep Dive endpoints
- Added `extract_json_from_response()` function with multiple parsing strategies
- Enhanced error handling with fallback questions/analysis
- Added model validation and working models list

## Environment Variables Required

Add these to Railway's environment variables:
```
SUPABASE_URL=https://ekaxwbatykostnmopnhn.supabase.co
SUPABASE_ANON_KEY=[your_anon_key]
SUPABASE_SERVICE_KEY=[your_service_key]
OPENROUTER_API_KEY=[your_openrouter_key]
```

## Deployment Steps

1. **Commit ALL the changes**:
```bash
git add run_oracle.py nixpacks.toml runtime.txt pyproject.toml railway.json
git commit -m "Fix deep dive model issues and Python 3.13 compatibility"
git push origin main
```

2. **Railway will auto-deploy** from your GitHub repository

3. **Verify deployment** by checking Railway logs for:
```
🚀 ORACLE AI SERVER - READY!
```

## Testing the Fixed Endpoints

Test Deep Dive without specifying model (should work now):
```bash
curl -X POST https://web-production-945c4.up.railway.app/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "chest",
    "form_data": {"symptoms": "chest pain"}
  }'
```

## Frontend Changes Required

Update your frontend to handle empty questions gracefully:

```typescript
// In deepdive-client.ts
const DEFAULT_MODEL = 'deepseek/deepseek-chat'; // NOT deepseek-r1

// In your component
if (!response.question || response.question.trim() === '') {
  // Retry with explicit model or show error
  console.error('Empty question received, retrying...');
}
```

## Working Models List

These models are validated and working:
- `deepseek/deepseek-chat` (default, most reliable)
- `meta-llama/llama-3.2-3b-instruct:free` (fast)
- `google/gemini-2.0-flash-exp:free` (good for context)
- `microsoft/phi-3-mini-128k-instruct:free` (lightweight)

## Monitoring

Watch Railway logs for any parse errors:
- "Parse error in deep dive" messages indicate model issues
- Check for "Warning: Model X not in working list" messages

The backend should now handle all edge cases gracefully and always return valid responses.
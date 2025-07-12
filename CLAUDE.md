# CLAUDE.md - Project Guidelines for AI Assistants

## 🚨 CRITICAL SECURITY RULES

### NEVER EXPOSE SENSITIVE INFORMATION
1. **NEVER display or log API keys, tokens, or credentials**
2. **NEVER commit .env files or any file containing secrets**
3. **ALWAYS check .gitignore before creating files with sensitive data**
4. **NEVER include real API keys in documentation or examples**

### When Working with Environment Variables:
- ✅ DO: Reference them as placeholders (e.g., `YOUR_API_KEY_HERE`)
- ❌ DON'T: Show actual values in logs, outputs, or files
- ✅ DO: Ensure .env is in .gitignore
- ❌ DON'T: Create new files that might contain secrets without checking

## 🤖 MODEL CONFIGURATION

### NEVER USE THESE BROKEN MODELS:
- ❌ `deepseek/deepseek-r1-0528:free` - Returns unparseable responses
- ❌ `deepseek/deepseek-r1` - Same broken model

### ALWAYS USE THESE WORKING MODELS:
1. ✅ `tngtech/deepseek-r1t-chimera:free` - BEST for Deep Dive & Oracle Chat
2. ✅ `deepseek/deepseek-chat` - Good for Quick Scan
3. ✅ `meta-llama/llama-3.2-3b-instruct:free` - Fast and reliable
4. ✅ `google/gemini-2.0-flash-exp:free` - Good for large contexts
5. ✅ `microsoft/phi-3-mini-128k-instruct:free` - Lightweight

### MODEL USAGE BY ENDPOINT:
- **Oracle Chat**: Uses chimera (working great!)
- **Deep Dive**: Uses chimera (same as Oracle)
- **Quick Scan**: Uses deepseek-chat
- **Summaries**: Uses deepseek-chat

## 🏗️ PROJECT STRUCTURE

### Python Version:
- Use Python 3.11 for Railway deployment (3.13 has compatibility issues)
- Local development can use 3.13 with uv

### Key Files:
- `run_oracle.py` - Main Oracle server with all endpoints
- `api_routes.py` - Basic API routes (not used in production)
- `llm_summary_tools.py` - Summary generation service
- `business_logic.py` - Shared business logic
- `.env` - Environment variables (NEVER COMMIT)

### Important Endpoints:
- `/api/health` - Health check
- `/api/chat` - Main chat endpoint
- `/api/quick-scan` - Quick health scan
- `/api/deep-dive/start` - Start deep dive (MUST use working models)
- `/api/deep-dive/continue` - Continue deep dive
- `/api/deep-dive/complete` - Complete deep dive

## 📝 DEPLOYMENT CHECKLIST

Before deploying to Railway:
1. ✅ Ensure all deepseek-r1 references are removed
2. ✅ Check Python version compatibility (use 3.11)
3. ✅ Verify .env is NOT being committed
4. ✅ Test endpoints locally with working models
5. ✅ Ensure JSON parsing handles all response formats

## 🔧 COMMON ISSUES & FIXES

### Deep Dive Not Working:
- **Issue**: Returns empty questions or parse errors
- **Fix**: Ensure using `deepseek/deepseek-chat`, not deepseek-r1

### Railway Build Failing:
- **Issue**: Pydantic/tiktoken build errors
- **Fix**: Use Python 3.11 via nixpacks.toml and runtime.txt

### Railway "pip: command not found" Error:
- **Issue**: pip not available in Nixpacks build environment
- **Fix**: 
  1. Update nixpacks.toml to include `python311Packages.pip` in nixPkgs
  2. Create railway-build.sh script that ensures pip installation:
     ```bash
     python -m ensurepip --upgrade
     python -m pip install --upgrade pip
     python -m pip install -r requirements.txt
     ```
  3. Use `python -m pip` instead of bare `pip` command
  4. NOTE: First deployment takes 5-10 minutes to download packages (~550MB)

### API Keys Exposed:
- **Issue**: Sensitive data in logs or commits
- **Fix**: IMMEDIATELY rotate keys and update .gitignore

## 🛡️ SECURITY BEST PRACTICES

1. **API Key Management**:
   - Store in .env file only
   - Use environment variables in production
   - Rotate keys if exposed

2. **Database Access**:
   - Use ANON key for client-side
   - Use SERVICE key for server-side only
   - Never expose SERVICE key

3. **Error Handling**:
   - Don't expose internal errors to users
   - Log errors server-side only
   - Return generic error messages

## 🚀 QUICK START

```bash
# Install with uv (local development)
uv sync

# Run Oracle server
uv run python run_oracle.py

# Test health check
curl http://localhost:8000/api/health

# Test deep dive (uses chimera by default - same as Oracle!)
curl -X POST http://localhost:8000/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "chest",
    "form_data": {"symptoms": "pain"}
  }'
```

## ⚠️ WARNINGS

1. **NEVER expose environment variables in responses**
2. **ALWAYS use working models from the approved list**
3. **NEVER commit .env or files with secrets**
4. **ALWAYS test locally before deploying**
5. **NEVER log sensitive information**

---
Last Updated: 2025-01-12
Remember: Security first, functionality second!
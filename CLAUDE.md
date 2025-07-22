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
1. ✅ `deepseek/deepseek-chat` - DeepSeek V3 - DEFAULT for Quick Scan
2. ✅ `google/gemini-2.5-pro` - BEST for Deep Dive & Photo Analysis
3. ✅ `openai/o4-mini` - Think Harder tier 2 (balanced cost/performance)
4. ✅ `x-ai/grok-4` - Ultra Think & Deep Dive Think Harder (maximum reasoning)
5. ✅ `tngtech/deepseek-r1t-chimera:free` - Fallback option
6. ✅ `google/gemini-2.0-flash-exp:free` - Good for large contexts

### MODEL USAGE BY ENDPOINT:
- **Quick Scan**: Uses `deepseek/deepseek-chat` (DeepSeek V3)
- **Deep Dive**: Uses `google/gemini-2.5-pro`
- **Photo Analysis**: Uses `google/gemini-2.5-pro`
- **Think Harder (o4)**: Uses `openai/o4-mini`
- **Ultra Think**: Uses `x-ai/grok-4`
- **Deep Dive Think Harder**: Uses `x-ai/grok-4`

## 🏗️ PROJECT STRUCTURE

### Python Version:
- Use Python 3.11 for Railway deployment (3.13 has compatibility issues)
- Local development can use 3.13 with uv

### Modular Architecture (NEW):
```
mcp-backend/
├── run_oracle.py          # Main entry point - KEEP SLIM (~100 lines)
├── api/
│   ├── chat.py           # Chat & Oracle endpoints
│   ├── health_scan.py    # Quick scan & Deep dive endpoints
│   ├── health_story.py   # Health story generation
│   ├── tracking.py       # Symptom tracking endpoints
│   ├── population_health.py  # Population health alerts
│   └── reports/
│       ├── general.py    # General report endpoints
│       ├── specialist.py # Specialist reports (cardio, neuro, etc.)
│       ├── time_based.py # 30-day, annual summaries
│       └── urgent.py     # Urgent triage reports
├── models/
│   └── requests.py       # All request/response models
├── utils/
│   ├── json_parser.py    # JSON extraction utilities
│   ├── token_counter.py  # Token counting
│   └── data_gathering.py # Data fetching functions
└── core/
    └── middleware.py     # CORS and other middleware
```

### CRITICAL: Modular Code Rules
1. **NEVER add new endpoints to run_oracle.py** - Use appropriate module
2. **Each module should be focused** - One concern per file
3. **Use FastAPI routers** - Not direct app imports
4. **Keep functions where they're used** - Don't create unnecessary abstractions
5. **run_oracle.py only imports and includes routers** - No business logic

### Key Files:
- `run_oracle.py` - Main entry point (imports routers only)
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

## 🎯 BACKEND IMPLEMENTATION STATUS

### Deep Dive Session States (COMPLETED ✅)
- **Active**: Session is asking questions
- **Analysis Ready**: Initial analysis complete, Ask Me More available
- **Completed**: Final state after all interactions

### Key Features Implemented:
1. **Deep Dive Ultra Think** ✅
   - Endpoint: `/api/deep-dive/ultra-think`
   - Uses Grok 4 for maximum reasoning
   - Returns confidence progression

2. **Ask Me More** ✅
   - Works with `analysis_ready` and `completed` states
   - Supports up to 5 additional questions
   - Auto-completes after 6 total questions

3. **Oracle AI Chat** ✅
   - Accepts both `message` and `query` fields
   - Supports `context` parameter
   - Returns both `response` and `message` fields

4. **Model Fallback Support** ✅
   - All Deep Dive endpoints accept `fallback_model`
   - Automatic retry on failure

5. **No Undefined Values** ✅
   - All responses use explicit `null` instead of undefined
   - Include helpful messages

## 🔧 COMMON ISSUES & FIXES

### Deep Dive Not Working:
- **Issue**: Returns empty questions or parse errors
- **Fix**: Ensure using `deepseek/deepseek-chat`, not deepseek-r1

### Railway Build Failing:
- **Issue**: Pydantic/tiktoken build errors
- **Fix**: Use Python 3.11 via nixpacks.toml and runtime.txt

### CRITICAL DEPLOYMENT RULES:
1. **NEVER BREAK THE DEPLOYMENT**
2. **ALWAYS TEST WITH**: `python -m py_compile run_oracle.py`
3. **NEVER USE INVALID MODEL NAMES** (no :nitro unless verified)
4. **ALWAYS ENSURE PYTHON IS AVAILABLE**:
   - railway.toml specifies Python 3.11
   - nixpacks.toml ensures pip is installed
   - runtime.txt has exact version
5. **PROCFILE MUST USE**: `python run_oracle.py` NOT uvicorn command

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

## 🏗️ CODE ORGANIZATION

### Modular Structure (Completed 2025-01-17):
The codebase has been modularized from a single 4,871-line file into organized modules:
- **api/** - Feature-based endpoint modules (chat, health_scan, tracking, etc.)
- **api/reports/** - Report-specific endpoints (general, specialist, time_based, urgent)
- **models/** - Pydantic request/response models
- **utils/** - Shared utilities (JSON parsing, token counting, data gathering)
- **core/** - Core functionality (middleware, config)

**IMPORTANT**: When adding new endpoints:
1. Add to the appropriate module based on feature area
2. Don't add to run_oracle.py - it's now just the entry point
3. Follow the existing pattern in the modules
4. Update imports in run_oracle.py if adding new modules

## ⚠️ WARNINGS

1. **NEVER expose environment variables in responses**
2. **ALWAYS use working models from the approved list**
3. **NEVER commit .env or files with secrets**
4. **ALWAYS test locally before deploying**
5. **NEVER log sensitive information**
6. **NEVER add new endpoints to run_oracle.py** - use appropriate modules

---
Last Updated: 2025-01-17
Remember: Security first, functionality second!
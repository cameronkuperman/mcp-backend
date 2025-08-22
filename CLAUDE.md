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
1. ✅ `openai/gpt-5-mini` - DEFAULT for Quick Scan, Chat & Flash Assessment
2. ✅ `x-ai/grok-4` - Ultra Think & Deep Dive Think Harder (maximum reasoning)
3. ✅ `google/gemini-2.5-pro` - Photo Analysis & Deep Dive
4. ✅ `openai/gpt-5-mini` - Think Harder tier 2 (balanced cost/performance)
5. ✅ `deepseek/deepseek-chat` - DeepSeek V3 - Fallback option
6. ✅ `tngtech/deepseek-r1t-chimera:free` - Secondary fallback
7. ✅ `google/gemini-2.0-flash-exp:free` - Good for large contexts
8. ✅ `meta-llama/llama-3.2-1b-instruct:free` - Nano model fallback

### MODEL USAGE BY ENDPOINT:
- **Quick Scan**: Uses `openai/gpt-5-mini` (Updated for better performance)
- **Chat**: Uses `deepseek/deepseek-chat` (DeepSeek V3)
- **Deep Dive**: Uses `deepseek/deepseek-chat` (Good JSON compliance)
- **Photo Analysis**: Uses `openai/gpt-5` (with `google/gemini-2.5-pro` as fallback)
- **Think Harder**: Uses `openai/gpt-5-mini` (with `deepseek/deepseek-chat` as fallback)
- **Ultra Think**: Uses `x-ai/grok-4` (UNCHANGED - maximum reasoning)
- **Deep Dive Think Harder**: Uses `x-ai/grok-4`

## 🚀 SCALABILITY & BEST PRACTICES

### Industry-Standard Design Principles
Following FAANG-level scalability patterns for production-ready systems:

#### 1. **Data Immutability**
- ✅ DO: Create new records for updates (audit trail)
- ✅ DO: Use chain_id or similar for linking related records
- ❌ DON'T: Modify existing health assessment records
- **Why**: Ensures complete medical history and compliance

#### 2. **Event Sourcing for Medical Data**
- ✅ DO: Track all state changes as events
- ✅ DO: Store progression/evolution as temporal events
- ✅ DO: Maintain complete audit trails
- **Example**: Follow-ups create new assessments, not modify existing

#### 3. **Database Design Patterns**
- **Proper Indexing**: Add indexes for all foreign keys and query patterns
- **Temporal Queries**: Design for "state at any point in time" queries
- **Denormalization**: Strategic denormalization for read-heavy operations
- **JSONB Usage**: Use for flexible schema (medical data evolves)

#### 4. **API Design Standards**
- **Idempotency**: All POST operations should be idempotent
- **Pagination**: All list endpoints must support pagination
- **Versioning**: Prepare for API versioning from day one
- **Rate Limiting**: Implement rate limiting for all endpoints

#### 5. **Performance Optimization**
- **Caching Strategy**: Cache expensive LLM calls when appropriate
- **Async Operations**: Use async/await for all I/O operations
- **Connection Pooling**: Proper database connection management
- **Batch Operations**: Support batch operations where sensible

#### 6. **Error Handling & Resilience**
- **Retry Logic**: Implement exponential backoff for external services
- **Circuit Breakers**: Prevent cascade failures
- **Graceful Degradation**: System should degrade gracefully
- **Dead Letter Queues**: For failed async operations

#### 7. **Medical Data Specific**
- **Temporal Awareness**: All medical data must maintain temporal context
- **Chain of Custody**: Clear audit trail for all medical records
- **Privacy by Design**: HIPAA-compliant data handling
- **Progressive Disclosure**: Reveal complexity gradually

### Code Quality Standards
```python
# ✅ GOOD: Immutable, traceable, scalable
async def create_follow_up(assessment_id: str, responses: dict):
    chain_id = get_or_create_chain_id(assessment_id)
    new_assessment = create_new_assessment(chain_id, responses)
    track_event("follow_up_created", assessment_id, new_assessment.id)
    return new_assessment

# ❌ BAD: Mutating existing records
def update_assessment(assessment_id: str, responses: dict):
    assessment = get_assessment(assessment_id)
    assessment.update(responses)  # Don't do this!
    assessment.save()
```

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

6. **JSON Response Format** ✅
   - **Backend returns parsed JavaScript objects, NOT JSON strings**
   - **Frontend should NOT use JSON.parse() on responses**
   - All numeric values are numbers, not strings
   - Deep Dive now uses DeepSeek V3 by default (better JSON compliance)
   - Enhanced JSON extraction for Gemini models

## 🔧 COMMON ISSUES & FIXES

### Deep Dive Not Working:
- **Issue**: Returns generic fallback responses instead of real medical analysis
- **Fix**: 
  1. Changed default model to `deepseek/deepseek-chat` (better JSON compliance)
  2. Added aggressive JSON extraction for Gemini models
  3. Enhanced debug logging to track parsing failures
  4. Frontend should NOT double-parse responses (they're already objects)

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

### CORS Errors with Credentials:
- **Issue**: "The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'"
- **Fix**: Updated `core/middleware.py` to use specific allowed origins instead of wildcard
- **Details**: 
  - CORS spec doesn't allow `*` with `credentials: 'include'`
  - Now supports localhost:3000-3002, Netlify URLs, and healthoracle.ai domains
  - Can add custom origins via `CORS_ORIGINS` env variable (comma-separated)

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

# Test deep dive (uses DeepSeek V3 by default for better JSON)
curl -X POST http://localhost:8000/api/deep-dive/start \
  -H "Content-Type: application/json" \
  -d '{
    "body_part": "chest",
    "form_data": {"symptoms": "pain"}
  }'
```

## 🧠 CORE PHILOSOPHY: LLM-FIRST PRINCIPLE

### All Health Metrics & Scores Are LLM-Generated
**CRITICAL**: This application uses LLMs to generate ALL health scores, metrics, and insights from first principles.
- ✅ DO: Use LLMs to analyze data and generate scores/patterns/insights
- ❌ DON'T: Use hardcoded algorithms or formulas for health metrics
- ✅ DO: Let the LLM evaluate symptom severity, body system health, patterns
- ❌ DON'T: Calculate scores with simple math (unless extremely beneficial)

**Rationale**: LLMs understand context, nuance, and relationships better than rigid algorithms.

Example:
```python
# ❌ WRONG - Hardcoded calculation
health_velocity = (10 - avg_symptom_severity) * 10

# ✅ RIGHT - LLM analysis
prompt = "Analyze this week's health data and provide a velocity score 0-100..."
health_velocity = llm_response.score
```

## 🏗️ CODE ORGANIZATION

### Modular Structure (Completed 2025-01-17):
The codebase has been modularized from a single 4,871-line file into organized modules:
- **api/** - Feature-based endpoint modules (chat, health_scan, tracking, etc.)
- **api/reports/** - Report-specific endpoints (general, specialist, time_based, urgent)
- **api/intelligence/** - NEW: Data intelligence endpoints (health velocity, patterns, etc.)
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
Last Updated: 2025-08-07
Remember: Security first, functionality second!
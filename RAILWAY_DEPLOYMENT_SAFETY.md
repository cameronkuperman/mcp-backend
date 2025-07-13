# Railway Deployment Safety Guide

## 🚨 CRITICAL: NEVER BREAK THE DEPLOYMENT

### Current Working Configuration

We now use a **Dockerfile** for Railway deployment because it's the most reliable:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "run_oracle.py"]
```

### Files That Control Deployment

1. **Dockerfile** - Main deployment configuration
2. **railway.json** - Tells Railway to use Dockerfile
3. **requirements.txt** - Python dependencies
4. **Procfile** - Backup (uses: `web: python run_oracle.py`)
5. **runtime.txt** - Specifies Python 3.11.9

### DO NOT CHANGE THESE WITHOUT TESTING

## Pre-Deployment Checklist

Before EVERY commit that might affect deployment:

1. **Test Python syntax**:
   ```bash
   python -m py_compile run_oracle.py
   python -m py_compile business_logic.py
   ```

2. **Verify model names exist**:
   - ✅ `deepseek/deepseek-chat`
   - ✅ `tngtech/deepseek-r1t-chimera:free`
   - ❌ `deepseek/deepseek-chat:nitro` (DOES NOT EXIST)

3. **Check imports**:
   ```python
   # At top of run_oracle.py
   from datetime import datetime, timezone, timedelta  # ✅ Correct
   # NOT: from datetime import datetime, timezone; from datetime import timedelta
   ```

4. **Ensure CORS is configured**:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## Common Deployment Failures & Fixes

### 1. "python: command not found"
**Cause**: Nixpacks build without proper config
**Fix**: Use Dockerfile (already implemented)

### 2. "No module named pip"
**Cause**: Python installed without pip
**Fix**: Dockerfile handles this with `python:3.11-slim`

### 3. CORS errors from frontend
**Cause**: Usually means backend crashed/not running
**Fix**: Check Railway logs for actual error

### 4. Import errors
**Cause**: Missing dependencies or syntax errors
**Fix**: Test locally first, check requirements.txt

## Emergency Recovery

If deployment breaks:

1. **Revert to last working commit**:
   ```bash
   git log --oneline -5  # Find last working commit
   git revert HEAD      # If last commit broke it
   ```

2. **Check Railway logs**:
   - Look for Python errors
   - Check for missing dependencies
   - Verify environment variables are set

3. **Test locally with same Python version**:
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python run_oracle.py
   ```

## Environment Variables Required

Make sure Railway has these:
- `OPENROUTER_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (not anon key!)
- `PORT` (Railway provides this automatically)

## Testing Health Story Locally

```bash
# Test the endpoint
curl -X POST http://localhost:8000/api/health-story \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id",
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-07T23:59:59Z"
    }
  }'
```

## Golden Rules

1. **NEVER deploy without testing syntax**
2. **NEVER add dependencies without testing locally**
3. **NEVER change model names without verifying they exist**
4. **ALWAYS check Railway logs if deployment fails**
5. **ALWAYS keep Dockerfile as primary deployment method**

---

Last Updated: 2024-01-13
Deployment Method: Dockerfile
Python Version: 3.11.9
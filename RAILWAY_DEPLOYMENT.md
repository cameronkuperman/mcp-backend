# Railway Deployment Guide for MCP Backend

## Overview
This guide will help you deploy your MCP backend to Railway, which should resolve the DNS issues since Railway's infrastructure handles external API calls differently than your local network.

## Prerequisites
- Railway account (sign up at https://railway.app)
- GitHub account (to connect your repo)
- Your environment variables ready

## Step 1: Prepare Your Repository

1. **Create a new GitHub repository** or use existing one
2. **Push your code**:
```bash
git init
git add .
git commit -m "Initial MCP backend commit"
git remote add origin https://github.com/YOUR_USERNAME/mcp-backend.git
git push -u origin main
```

## Step 2: Set Up Railway Project

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Click "New Project"**
3. **Select "Deploy from GitHub repo"**
4. **Connect your GitHub account** and select your repository
5. **Railway will automatically detect it's a Python app**

## Step 3: Configure Environment Variables

In Railway dashboard, go to your project's Variables tab and add:

```env
# Required
OPENROUTER_API_KEY=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
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key

# Optional
APP_URL=https://your-app.railway.app
PYTHON_VERSION=3.11
```

## Step 4: Configure Build & Deploy

Railway will use the `railway.json` file we created:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn run_full_server:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Step 5: Update Your Code for Production

1. **Update `run_full_server.py`** to use PORT environment variable:

```python
import os
import uvicorn
from mcp_server import mcp

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app = mcp.http_app()
    uvicorn.run(app, host="0.0.0.0", port=port)
```

2. **Update CORS in `api_routes.py`** for your frontend domain:

```python
api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend.vercel.app",  # Add your production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 6: Deploy

1. **Push your changes** to GitHub:
```bash
git add .
git commit -m "Configure for Railway deployment"
git push
```

2. **Railway will automatically deploy** when you push to main branch

3. **Monitor deployment** in Railway dashboard

## Step 7: Get Your API URL

Once deployed, Railway will provide you with a URL like:
```
https://mcp-backend-production-xxxx.up.railway.app
```

## Step 8: Update Your Frontend

Update your Next.js app to use the Railway URL:

```typescript
// In your API client
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://mcp-backend-production-xxxx.up.railway.app/api';
```

## Testing Your Deployment

1. **Health Check**:
```bash
curl https://your-app.railway.app/api/health
```

2. **Test Chat Endpoint**:
```bash
curl -X POST https://your-app.railway.app/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Test message",
    "user_id": "test-user",
    "conversation_id": "test-conv",
    "category": "health-scan"
  }'
```

## Troubleshooting

### If DNS Issues Persist
The `openrouter_proxy.py` file includes fallback mechanisms:
- Direct IP connection attempts
- Multiple endpoint retries
- Mock responses as last resort

### Logs
View logs in Railway dashboard or use Railway CLI:
```bash
railway logs
```

### Common Issues

1. **Port binding errors**: Make sure to use `$PORT` environment variable
2. **Module not found**: Ensure all dependencies are in `requirements.txt`
3. **Timeout errors**: Railway has a 5-minute timeout for requests

## Alternative: Use Different LLM Provider

If OpenRouter continues to have issues, you can switch to:

1. **OpenAI Direct**:
```python
# In business_logic.py
response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {openai_key}"},
    json={"model": "gpt-3.5-turbo", "messages": messages}
)
```

2. **Anthropic Claude**:
```python
response = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={"x-api-key": anthropic_key},
    json={"model": "claude-3-sonnet", "messages": messages}
)
```

## Environment-Specific Configuration

Create a `config.py`:

```python
import os

class Config:
    # Detect environment
    IS_PRODUCTION = os.environ.get("RAILWAY_ENVIRONMENT") == "production"
    
    # API endpoints
    if IS_PRODUCTION:
        # Production endpoints that work on Railway
        OPENROUTER_URL = "https://api.openrouter.ai/v1/chat/completions"
    else:
        # Local development with potential DNS issues
        OPENROUTER_URL = "http://localhost:8000/api/chat"  # Use mock
    
    # Other config
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")
```

## Summary

Deploying to Railway should resolve the DNS issues because:
1. Railway's infrastructure has proper DNS resolution
2. Requests go through Railway's network, not your local network
3. No VPN or local network restrictions apply

After deployment, your Oracle API will be accessible globally and the DNS issues should be resolved!
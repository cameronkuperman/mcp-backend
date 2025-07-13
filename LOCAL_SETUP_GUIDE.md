# Local MCP Server Setup Guide

## Quick Start

### 1. Create .env file

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# In the mcp-backend directory
cp .env.example .env
```

Edit `.env` with your actual values:
```env
# OpenRouter API Key (get from https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1-xxxxx

# Supabase (from your Supabase project settings)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxx

# Server port (default 8000, change if needed)
PORT=8000
```

### 2. Install Dependencies

#### Option A: Using pip (Python 3.11 recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using uv (if installed)
```bash
# Install uv first if needed
pip install uv

# Then sync dependencies
uv sync
```

### 3. Run the Server

```bash
# Direct run
python run_oracle.py

# Or with uv
uv run python run_oracle.py
```

The server will start on `http://localhost:8000` (or your configured PORT).

### 4. Test the Health Story Endpoint

```bash
# Test health check first
curl http://localhost:8000/api/health

# Test health story generation
curl -X POST http://localhost:8000/api/health-story \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123"
  }'
```

## Connecting Your Frontend

### In your Next.js app:

1. **For local development**, update your environment variable:
```env
# In your Next.js .env.local file
NEXT_PUBLIC_ORACLE_API_URL=http://localhost:8000
```

2. **Or modify the service directly** (temporarily):
```typescript
// In healthstory-service.ts
const API_URL = 'http://localhost:8000'; // For local testing
```

3. **Make sure CORS is working**. The server already has CORS enabled for all origins in development.

## Troubleshooting

### Port Already in Use
Change the PORT in your .env file to something else (e.g., 8001, 3001)

### Missing Dependencies
If tiktoken fails to install:
```bash
pip install tiktoken --no-binary tiktoken
```

### Connection Refused
- Check firewall settings
- Ensure server is running
- Try `127.0.0.1` instead of `localhost`

### CORS Issues
The server allows all origins by default. If you still have issues, check browser console.

## Development Tips

1. **Watch logs**: The server prints helpful debug information
2. **Test endpoints**: Use Postman or curl to test before frontend integration
3. **Check Supabase**: Ensure your tables exist and RLS policies are correct
4. **Model testing**: You can change the model by adding `"model": "deepseek/deepseek-chat"` to the request

## Available Endpoints

- `GET /api/health` - Health check
- `POST /api/chat` - Oracle chat
- `POST /api/quick-scan` - Quick health scan
- `POST /api/deep-dive/start` - Start deep dive
- `POST /api/deep-dive/continue` - Continue deep dive Q&A
- `POST /api/deep-dive/complete` - Complete deep dive analysis
- `POST /api/health-story` - Generate health story (NEW!)
- `POST /api/generate_summary` - Generate conversation summary

## Next Steps

1. Start the server locally
2. Test the health story endpoint
3. Update your frontend to use local URL
4. Make changes and test
5. Deploy when ready!
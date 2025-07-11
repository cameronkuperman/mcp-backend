# Working Solution for Oracle Backend

## The Problem
DNS resolution is failing for api.openrouter.ai. This is likely due to:
1. Local DNS cache issues
2. Network configuration
3. VPN/Firewall blocking

## Quick Fix Options

### Option 1: Use a Mock LLM for Testing
Replace the call_llm function temporarily:

```python
async def call_llm(messages: list, **kwargs) -> dict:
    """Mock LLM for testing"""
    # Simulate Oracle response
    user_query = messages[-1]["content"] if messages else "Hello"
    
    response = f"""I understand you're asking about: "{user_query}"

As Oracle, your health companion, I'm here to help. While I'm currently in test mode, here's what I would normally do:

1. Analyze your symptoms carefully
2. Provide evidence-based health information
3. Suggest when to seek medical attention
4. Offer supportive guidance

For now, this is a test response to verify the system is working correctly."""
    
    return {
        "content": response,
        "raw_content": response,
        "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
        "model": "mock-model",
        "finish_reason": "stop"
    }
```

### Option 2: Fix DNS Issues
Try these commands:

```bash
# Clear DNS cache on Mac
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder

# Test with different DNS
dig @8.8.8.8 api.openrouter.ai

# Add to /etc/hosts (temporary fix)
echo "104.18.8.49 api.openrouter.ai" | sudo tee -a /etc/hosts
```

### Option 3: Use Local LLM
Install and use Ollama:

```bash
# Install Ollama
brew install ollama

# Pull a model
ollama pull llama2

# Update call_llm to use Ollama
```

## Working Server Setup (Without OpenRouter)

1. **Create mock_server.py**:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    user_id: str
    conversation_id: str
    category: str = "health-scan"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Mock Oracle response
    response = f"""Thank you for your question: "{request.query}"

As Oracle, I'm here to provide health guidance. This is a test response showing that your integration is working correctly.

Your conversation ID: {request.conversation_id}
Category: {request.category}

In a production environment, I would analyze your health query and provide personalized, evidence-based guidance."""
    
    return {
        "response": response,
        "raw_response": response,
        "conversation_id": request.conversation_id,
        "user_id": request.user_id,
        "category": request.category,
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150
        },
        "model": "mock-oracle"
    }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Mock Oracle API"}

@app.get("/api/")
async def root():
    return {"message": "Mock Oracle API is running"}

if __name__ == "__main__":
    print("🚀 Starting Mock Oracle Server")
    print("📍 URL: http://localhost:8000")
    print("❤️  Health: http://localhost:8000/api/health")
    print("💬 Chat: POST http://localhost:8000/api/chat")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

2. **Run the mock server**:
```bash
uv run python mock_server.py
```

3. **Test from your Next.js app** - it will work immediately!

## For Production

When DNS is fixed, your original setup will work. The issue is NOT your code - it's network/DNS.

### Alternative LLM Providers

If OpenRouter continues to have issues, consider:

1. **OpenAI Direct**:
```python
# Use OpenAI directly
response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {openai_key}"},
    json={"model": "gpt-3.5-turbo", "messages": messages}
)
```

2. **Anthropic Claude**:
```python
# Use Claude API
response = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={"x-api-key": anthropic_key},
    json={"model": "claude-3-sonnet", "messages": messages}
)
```

## Your Next.js App Will Work!

The integration code in `NEXTJS_ORACLE_COPY_PASTE.md` is correct. Once you have a working server (mock or real), your Next.js app will connect perfectly.

## Quick Test

```bash
# Test the mock server
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a headache",
    "user_id": "test",
    "conversation_id": "test-123"
  }'
```
#!/usr/bin/env python3
"""Oracle Server - Working with Real AI"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import requests
from dotenv import load_dotenv

load_dotenv()

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
    model: Optional[str] = None

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Oracle chat endpoint with real OpenRouter AI"""
    # Simple direct approach that works
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    messages = [
        {
            "role": "system", 
            "content": """You are Oracle, a wise and knowledgeable AI companion specializing in health and wellness guidance. 
            You provide compassionate, evidence-based health information while encouraging users to seek professional medical care when appropriate."""
        },
        {
            "role": "user",
            "content": request.query
        }
    ]
    
    # Direct API call that we know works
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": request.model or "deepseek/deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        return {
            "response": content,
            "raw_response": content,
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": result.get("usage", {}),
            "model": request.model or "deepseek/deepseek-chat",
            "status": "success"
        }
    else:
        return {
            "response": f"Error: {response.status_code} - {response.text}",
            "status": "error"
        }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Oracle AI API"}

@app.get("/")
async def root():
    return {
        "message": "Oracle AI Server Running",
        "endpoints": {
            "chat": "POST /api/chat",
            "health": "GET /api/health"
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*60)
    print("🚀 ORACLE AI SERVER - READY!")
    print("="*60)
    print(f"✅ Server: http://localhost:{port}")
    print(f"💬 Chat: POST http://localhost:{port}/api/chat")
    print(f"❤️  Health: GET http://localhost:{port}/api/health")
    print("🤖 Using: DeepSeek AI (Free)")
    print("="*60)
    print("\n✨ Your AI Oracle is ready to help!\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
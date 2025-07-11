#!/usr/bin/env python3
"""Oracle Server - Simplified version without Supabase RLS issues"""
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

# In-memory storage for testing
conversations = {}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Oracle chat endpoint with real AI - Simplified"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Get conversation history from memory
    if request.conversation_id not in conversations:
        conversations[request.conversation_id] = []
    
    history = conversations[request.conversation_id]
    
    # Build concise system prompt with history awareness
    has_history = len(history) > 0
    system_prompt = f"""You are Oracle, a compassionate health AI assistant{"with memory of our past conversations" if has_history else ""}.

{"CONVERSATION HISTORY: We've been discussing health concerns in this chat." if has_history else "This is our first interaction."}

CRITICAL INSTRUCTIONS:
• If this is a follow-up question, reference what was discussed earlier
• Connect current symptoms to previous ones mentioned in this chat
• Say things like "As we discussed..." or "Earlier you mentioned..." when relevant
• Give concise advice (2-3 paragraphs max) but show continuity
• Be warm and personal - you remember this conversation
• Recommend doctors for serious/persistent issues

IMPORTANT: Show that you remember the conversation context when applicable."""
    
    # Build messages with history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add last 5 exchanges from history
    for msg in history[-10:]:
        messages.append(msg)
    
    # Add current query
    messages.append({"role": "user", "content": request.query})
    
    # Save user message
    history.append({"role": "user", "content": request.query})
    
    # Call OpenRouter
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
            "max_tokens": 500  # Limit for concise responses
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
        # Save assistant response
        history.append({"role": "assistant", "content": content})
        conversations[request.conversation_id] = history
        
        return {
            "response": content,
            "raw_response": content,
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": result.get("usage", {}),
            "model": request.model or "deepseek/deepseek-chat",
            "status": "success",
            "message_count": len(history)
        }
    else:
        return {
            "response": f"Error: {response.status_code}",
            "status": "error"
        }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Oracle AI (Simple)"}

@app.get("/")
async def root():
    return {"message": "Oracle AI Server", "version": "simple"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*60)
    print("🚀 ORACLE AI SERVER (SIMPLE) - READY!")
    print("="*60)
    print(f"✅ Server: http://localhost:{port}")
    print(f"💬 Chat: POST http://localhost:{port}/api/chat")
    print("🤖 Using: DeepSeek AI")
    print("📝 Note: Using in-memory storage (no Supabase)")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)
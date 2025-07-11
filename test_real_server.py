#!/usr/bin/env python3
"""Test server with real OpenRouter integration"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from business_logic import get_user_data, get_llm_context, call_llm, build_messages_for_llm, store_message, update_conversation_timestamp

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
    """Real Oracle endpoint with OpenRouter"""
    try:
        # Get user data
        user_data = await get_user_data(request.user_id)
        
        # Build messages
        messages = await build_messages_for_llm(
            conversation_id=request.conversation_id,
            new_query=request.query,
            category=request.category,
            user_data=user_data,
            user_id=request.user_id
        )
        
        # Store user message
        await store_message(
            conversation_id=request.conversation_id,
            role="user",
            content=request.query
        )
        
        # Call real OpenRouter LLM
        print(f"Calling OpenRouter with model: {request.model or 'default'}")
        llm_response = await call_llm(
            messages=messages,
            model=request.model,
            user_id=request.user_id
        )
        
        # Store assistant response
        await store_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=llm_response["raw_content"],
            token_count=llm_response["usage"].get("completion_tokens", 0),
            model_used=llm_response["model"]
        )
        
        # Update conversation
        await update_conversation_timestamp(request.conversation_id, llm_response["raw_content"])
        
        return {
            "response": llm_response["content"],
            "raw_response": llm_response["raw_content"],
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": llm_response["usage"],
            "model": llm_response["model"],
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return {
            "response": f"Error occurred: {str(e)}",
            "raw_response": f"Error occurred: {str(e)}",
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "model": "error",
            "status": "error"
        }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Oracle API with OpenRouter"}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Oracle Server with REAL OpenRouter!")
    print("="*50)
    print("📍 Server URL: http://localhost:8000")
    print("❤️  Health Check: http://localhost:8000/api/health")
    print("💬 Chat Endpoint: POST http://localhost:8000/api/chat")
    print("🤖 Using DeepSeek and other free models")
    print("="*50)
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
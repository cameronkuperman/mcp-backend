#!/usr/bin/env python3
"""Oracle Server - Working with Real AI and Supabase"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase_client import supabase
import tiktoken

load_dotenv()

app = FastAPI()

# Token counter
try:
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
except:
    encoding = None

def count_tokens(text: str) -> int:
    """Count tokens in text"""
    if encoding:
        return len(encoding.encode(text))
    return len(text.split()) * 1.3  # Rough estimate if tiktoken fails

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

class GenerateSummaryRequest(BaseModel):
    conversation_id: str
    user_id: str

# Supabase helper functions
async def get_user_medical_data(user_id: str) -> dict:
    """Fetch user's medical data from Supabase"""
    try:
        response = supabase.table("medical").select("*").eq("id", user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {"user_id": user_id, "note": "No medical data found"}
    except Exception as e:
        print(f"Error fetching medical data: {e}")
        return {"user_id": user_id, "error": str(e)}

async def get_llm_context(user_id: str, conversation_id: str, current_query: str = "") -> str:
    """Fetch LLM context/summary from Supabase with intelligent aggregation"""
    try:
        # First check if we need aggregate (all summaries for user)
        all_summaries = supabase.table("llm_context").select("llm_summary").eq("user_id", user_id).execute()
        
        if all_summaries.data:
            # Calculate total tokens across all summaries
            total_context = "\n\n".join([s.get("llm_summary", "") for s in all_summaries.data])
            total_tokens = count_tokens(total_context)
            
            if total_tokens > 25000:
                # Need to aggregate - inline the aggregation logic here
                print(f"Context too large ({total_tokens} tokens), aggregating...")
                
                # Aggregate inline to avoid import issues
                compression_ratio = 1.5 if total_tokens < 50000 else 2.0 if total_tokens < 100000 else 5.0
                target_tokens = int(total_tokens / compression_ratio)
                
                aggregate_prompt = f"""Summarize this medical history in {target_tokens} tokens, focusing on: {current_query}
                
HISTORY: {total_context[:10000]}...

Write concise medical summary:"""
                
                # Call OpenRouter directly to avoid recursion
                api_key = os.getenv("OPENROUTER_API_KEY")
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek/deepseek-chat",
                        "messages": [{"role": "system", "content": aggregate_prompt}],
                        "max_tokens": target_tokens,
                        "temperature": 0.3
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return total_context[:2000]  # Fallback to truncated context
            else:
                # Just return the specific conversation summary
                response = supabase.table("llm_context").select("llm_summary").eq("user_id", user_id).eq("conversation_id", conversation_id).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0].get("llm_summary", "")
        
        return ""
    except Exception as e:
        print(f"Error fetching LLM context: {e}")
        return ""

async def get_conversation_history(conversation_id: str) -> list:
    """Get recent messages from conversation"""
    try:
        response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).limit(10).execute()
        return response.data or []
    except:
        return []

async def save_message(conversation_id: str, role: str, content: str, user_id: str = None, model: str = None):
    """Save message to Supabase"""
    try:
        message_data = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "content_type": "text",
            "token_count": len(content.split()),
            "model_used": model,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("messages").insert(message_data).execute()
    except Exception as e:
        print(f"Error saving message: {e}")

async def update_conversation(conversation_id: str, user_id: str):
    """Update or create conversation record"""
    try:
        # Check if conversation exists
        existing = supabase.table("conversations").select("id").eq("id", conversation_id).execute()
        
        if not existing.data:
            # Create new conversation
            supabase.table("conversations").insert({
                "id": conversation_id,
                "user_id": user_id,
                "title": "Health Consultation",
                "ai_provider": "openrouter",
                "model_name": "deepseek/deepseek-chat",
                "conversation_type": "health_analysis",
                "status": "active",
                "message_count": 0,
                "total_tokens": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_message_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        else:
            # Update existing
            supabase.table("conversations").update({
                "last_message_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", conversation_id).execute()
    except Exception as e:
        print(f"Error updating conversation: {e}")

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Oracle chat endpoint with real OpenRouter AI and Supabase integration"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Fetch user medical data
    user_medical_data = await get_user_medical_data(request.user_id)
    
    # Fetch LLM context/summary with intelligent aggregation
    llm_context = await get_llm_context(request.user_id, request.conversation_id, request.query)
    
    # Get conversation history
    history = await get_conversation_history(request.conversation_id)
    
    # Build comprehensive system prompt with all context
    medical_summary = ""
    if user_medical_data and "error" not in user_medical_data and "note" not in user_medical_data:
        # Extract key medical info if available
        medical_summary = f"User has medical history on file. Key details: {str(user_medical_data)[:200]}..."
    
    system_prompt = f"""You are Oracle, a compassionate health AI assistant with memory of past interactions.

MEDICAL HISTORY: {medical_summary if medical_summary else "No medical history on file."}
CONVERSATION CONTEXT: {llm_context[:300] + "..." if llm_context else "This is our first conversation."}

CRITICAL INSTRUCTIONS:
• ALWAYS check if current symptoms relate to past conditions mentioned in medical history or previous conversations
• If user mentions something discussed before, acknowledge it: "As we discussed previously..." or "Given your history of..."
• Connect current concerns to past patterns: "This is similar to what you experienced..."
• Reference specific past advice if relevant: "Last time, we talked about..."
• Give concise advice (2-3 paragraphs max) but make connections to history
• Be warm and show you remember them as an individual
• Recommend doctors for serious/persistent issues

IMPORTANT: Actively reference their medical history and past conversations when relevant. Show continuity of care."""
    
    # Build messages with history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (last 5 exchanges)
    for msg in history[-10:]:  # Last 5 user/assistant pairs
        if msg.get("role") in ["user", "assistant"]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Add current query
    messages.append({
        "role": "user",
        "content": request.query
    })
    
    # Save user message to Supabase
    await save_message(
        conversation_id=request.conversation_id,
        role="user",
        content=request.query,
        user_id=request.user_id
    )
    
    # Update conversation record
    await update_conversation(request.conversation_id, request.user_id)
    
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
        model_used = request.model or "deepseek/deepseek-chat"
        
        # Save assistant response to Supabase
        await save_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=content,
            user_id=request.user_id,
            model=model_used
        )
        
        # Update conversation with token usage
        try:
            usage = result.get("usage", {})
            total_tokens = usage.get("total_tokens", 0)
            
            # Get current total_tokens from conversation
            conv_response = supabase.table("conversations").select("total_tokens").eq("id", request.conversation_id).execute()
            current_tokens = 0
            if conv_response.data and len(conv_response.data) > 0:
                current_tokens = conv_response.data[0].get("total_tokens", 0) or 0
            
            supabase.table("conversations").update({
                "total_tokens": current_tokens + total_tokens,
                "message_count": len(history) + 2  # +2 for new user/assistant messages
            }).eq("id", request.conversation_id).execute()
        except Exception as e:
            print(f"Error updating conversation tokens: {e}")
        
        return {
            "response": content,
            "raw_response": content,
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": result.get("usage", {}),
            "model": model_used,
            "status": "success",
            "medical_data_loaded": bool(user_medical_data),
            "context_loaded": bool(llm_context),
            "history_count": len(history)
        }
    else:
        error_msg = f"Error: {response.status_code} - {response.text}"
        
        # Save error as assistant message
        await save_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=error_msg,
            user_id=request.user_id,
            model="error"
        )
        
        return {
            "response": error_msg,
            "status": "error"
        }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Oracle AI API"}

@app.post("/api/generate_summary")
async def generate_summary_endpoint(request: GenerateSummaryRequest):
    """Generate medical summary of conversation"""
    try:
        # Fetch all messages from conversation
        messages_response = supabase.table("messages").select("*").eq("conversation_id", request.conversation_id).order("created_at").execute()
        
        if not messages_response.data:
            return {"error": "No messages found", "status": "error"}
        
        messages = messages_response.data
        
        # Build conversation text
        conversation_text = ""
        for msg in messages:
            timestamp = msg.get("created_at", "")[:10]
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            conversation_text += f"{timestamp} - {role}: {content}\n\n"
        
        # Calculate summary length
        total_tokens = count_tokens(conversation_text)
        if total_tokens < 1000:
            summary_tokens = 100
        elif total_tokens < 10000:
            summary_tokens = 500
        elif total_tokens < 20000:
            summary_tokens = 750
        else:
            summary_tokens = 1000
        
        # Create medical summary prompt
        summary_prompt = f"""You are a physician creating clinical notes. Create a {summary_tokens}-token medical summary.

Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
Messages: {len(messages)}

Include: symptoms, timeline, treatments discussed, patient response, recommendations, follow-up needed.

CONVERSATION:
{conversation_text[:10000]}

Write concise medical summary:"""

        # Generate summary
        summary_response = await call_llm(
            messages=[{"role": "system", "content": summary_prompt}],
            model="deepseek/deepseek-chat",
            max_tokens=summary_tokens + 100,
            temperature=0.3
        )
        
        summary_content = summary_response["content"]
        
        # Delete old summary
        supabase.table("llm_context").delete().eq("conversation_id", request.conversation_id).eq("user_id", request.user_id).execute()
        
        # Insert new summary
        insert_data = {
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "llm_summary": summary_content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("llm_context").insert(insert_data).execute()
        
        return {
            "summary": summary_content,
            "token_count": count_tokens(summary_content),
            "compression_ratio": round(total_tokens / count_tokens(summary_content), 2),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/")
async def root():
    return {
        "message": "Oracle AI Server Running",
        "endpoints": {
            "chat": "POST /api/chat",
            "health": "GET /api/health",
            "generate_summary": "POST /api/generate_summary"
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
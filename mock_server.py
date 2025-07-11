from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
from datetime import datetime
from business_logic import get_user_data, get_llm_context

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
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048

# Store conversations in memory for testing
conversations = {}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    # Get real user data from Supabase
    user_data = await get_user_data(request.user_id)
    llm_context = await get_llm_context(request.user_id, request.conversation_id)
    
    # Track conversation
    if request.conversation_id not in conversations:
        conversations[request.conversation_id] = []
    
    conversations[request.conversation_id].append({
        "role": "user",
        "content": request.query,
        "timestamp": datetime.now().isoformat()
    })
    
    # Enhanced mock Oracle response with real data
    medical_info = ""
    if isinstance(user_data, dict) and "error" not in user_data and "message" not in user_data:
        # User has medical data
        medical_info = "\n\nBased on your medical profile, I can provide more personalized guidance."
    
    context_info = ""
    if llm_context:
        context_info = f"\n\nConsidering our previous discussions: {llm_context[:100]}..."
    
    response = f"""Thank you for sharing that with me. You mentioned: "{request.query}"

As Oracle, your trusted health companion, I understand your concern.{medical_info}{context_info}

While this is currently a test environment with mock responses, the system is successfully:
• Fetching your medical data from Supabase
• Retrieving conversation context
• Processing your health queries

In a full implementation with OpenRouter, I would:
• Analyze your symptoms comprehensively
• Provide evidence-based health information
• Suggest appropriate next steps
• Offer emotional support and guidance

Your conversation ({request.conversation_id}) is being tracked, and the integration is working correctly.

Is there anything specific about your health concern you'd like to discuss further?"""
    
    # Track response
    conversations[request.conversation_id].append({
        "role": "assistant",
        "content": response,
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "response": response,
        "raw_response": response,
        "conversation_id": request.conversation_id,
        "user_id": request.user_id,
        "category": request.category,
        "usage": {
            "prompt_tokens": len(request.query.split()),
            "completion_tokens": len(response.split()),
            "total_tokens": len(request.query.split()) + len(response.split())
        },
        "model": request.model or "mock-oracle-v1"
    }

@app.get("/api/health")
async def health():
    return {"status": "healthy", "service": "Mock Oracle API"}

@app.get("/api/")
async def root():
    return {
        "message": "Mock Oracle API",
        "endpoints": {
            "chat": "POST /api/chat",
            "health": "GET /api/health",
            "docs": "GET /api/docs"
        },
        "active_conversations": len(conversations)
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history (for debugging)"""
    if conversation_id in conversations:
        return {
            "conversation_id": conversation_id,
            "messages": conversations[conversation_id],
            "message_count": len(conversations[conversation_id])
        }
    return {"error": "Conversation not found"}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Mock Oracle Server")
    print("="*50)
    print("📍 Server URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/api/docs")
    print("❤️  Health Check: http://localhost:8000/api/health")
    print("💬 Chat Endpoint: POST http://localhost:8000/api/chat")
    print("="*50)
    print("✅ This server works WITHOUT OpenRouter!")
    print("✅ Perfect for testing your Next.js integration!")
    print("="*50)
    print("\nPress CTRL+C to stop\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
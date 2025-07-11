from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Union
from business_logic import (
    get_user_data, get_llm_context, make_prompt, call_llm,
    build_messages_for_llm, store_message, update_conversation_timestamp
)

api = FastAPI()

# Configure CORS for Next.js
api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Your Next.js URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    query: str
    user_id: str
    conversation_id: str  # Changed from chat_id for consistency
    category: str = "health-scan"
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048

class PromptRequest(BaseModel):
    user_id: str
    query: str
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    llm_context: Optional[str] = None
    part_selected: Optional[str] = None
    region: Optional[str] = None
    model: Optional[str] = None

@api.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """HTTP endpoint for chat - handles conversation history automatically"""
    try:
        # Get user data for context
        user_data = await get_user_data(request.user_id)
        
        # Build messages array (handles new vs existing conversation)
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
            content=request.query,
            token_count=len(request.query.split())
        )
        
        # Call LLM with messages
        llm_response = await call_llm(
            messages=messages,
            model=request.model,
            user_id=request.user_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        # Store assistant response
        await store_message(
            conversation_id=request.conversation_id,
            role="assistant",
            content=llm_response["raw_content"],  # Store raw for consistency
            token_count=llm_response["usage"].get("completion_tokens", 0),
            model_used=llm_response["model"],
            metadata={
                "finish_reason": llm_response["finish_reason"],
                "total_tokens": llm_response["usage"].get("total_tokens", 0)
            }
        )
        
        # Update conversation metadata
        await update_conversation_timestamp(request.conversation_id, llm_response["raw_content"])
        
        return {
            "response": llm_response["content"],  # Can be string or JSON
            "raw_response": llm_response["raw_content"],  # Always string
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": llm_response["usage"],
            "model": llm_response["model"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/prompts/{category}")
async def generate_prompt(category: str, request: PromptRequest):
    """Generate prompts for different medical categories with health data"""
    try:
        user_data = await get_user_data(request.user_id)
        
        # Add health data if provided
        if any([request.height, request.weight, request.age, request.gender]):
            user_data.update({
                "height": request.height,
                "weight": request.weight, 
                "age": request.age,
                "gender": request.gender
            })
        
        llm_context = request.llm_context or await get_llm_context(request.user_id)
        
        prompt = make_prompt(
            query=request.query,
            user_data=user_data,
            llm_context=llm_context,
            category=category,
            part_selected=request.part_selected,
            region=request.region
        )
        
        return {
            "category": category,
            "prompt": prompt,
            "user_data": user_data,
            "parameters": {
                "part_selected": request.part_selected,
                "region": request.region
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/prompts/{category}/{region}")
async def generate_prompt_with_region(category: str, region: str, query: str, user_id: str, part_selected: Optional[str] = None):
    """Generate prompts with category and region in URL"""
    try:
        user_data = await get_user_data(user_id)
        llm_context = await get_llm_context(user_id)
        
        prompt = make_prompt(
            query=query,
            user_data=user_data,
            llm_context=llm_context,
            category=category,
            part_selected=part_selected,
            region=region
        )
        
        return {
            "category": category,
            "region": region,
            "prompt": prompt,
            "parameters": {
                "query": query,
                "user_id": user_id,
                "part_selected": part_selected
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Medical Chat API"}

@api.get("/")
async def root():
    """Root endpoint with helpful information"""
    return {
        "message": "Oracle Medical Chat API",
        "docs": "http://localhost:8000/api/docs",
        "health": "http://localhost:8000/api/health",
        "mcp_tools": [
            "oracle_query",
            "health_scan_query", 
            "quick_scan_query",
            "deep_dive_query",
            "create_llm_summary"
        ]
    }
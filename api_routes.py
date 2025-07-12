from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Union, Dict, List, Any
from business_logic import (
    get_user_data, get_llm_context, make_prompt, call_llm,
    build_messages_for_llm, store_message, update_conversation_timestamp
)
from supabase_client import supabase
import uuid
from datetime import datetime, timezone
import json

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

class QuickScanRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None  # Optional for anonymous users
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

@api.post("/quick-scan")
async def quick_scan_endpoint(request: QuickScanRequest):
    """Quick Scan endpoint for rapid health assessment"""
    try:
        # Get user data if user_id provided (otherwise anonymous)
        user_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            llm_context = await get_llm_context(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data
        }
        
        # Generate the quick scan prompt
        query = request.form_data.get("symptoms", "Health scan requested")
        system_prompt = make_prompt(
            query=query,
            user_data=prompt_data,
            llm_context=llm_context,
            category="quick-scan",
            part_selected=request.body_part
        )
        
        # Call LLM with lower temperature for consistent JSON
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze my symptoms for {request.body_part}: {json.dumps(request.form_data)}"}
            ],
            model=request.model,
            user_id=request.user_id,
            temperature=0.3,  # Lower temperature for more consistent JSON output
            max_tokens=1024
        )
        
        # Parse the response as JSON
        try:
            if isinstance(llm_response["content"], dict):
                analysis_result = llm_response["content"]
            else:
                # Try to extract JSON from string response
                content = llm_response["raw_content"]
                # Find JSON in the response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    analysis_result = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
        except Exception as json_error:
            # If JSON parsing fails, return error and ask for retry
            return {
                "error": "Failed to parse AI response",
                "message": "Please try again",
                "raw_response": llm_response.get("raw_content", ""),
                "parse_error": str(json_error)
            }
        
        # Generate unique scan ID
        scan_id = str(uuid.uuid4())
        
        # Save to database if user is authenticated
        if request.user_id:
            try:
                # Save to quick_scans table
                scan_data = {
                    "id": scan_id,
                    "user_id": request.user_id,
                    "body_part": request.body_part,
                    "form_data": request.form_data,
                    "analysis_result": analysis_result,
                    "confidence_score": analysis_result.get("confidence", 0),
                    "urgency_level": analysis_result.get("urgency", "low"),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                supabase.table("quick_scans").insert(scan_data).execute()
                
                # Save symptoms to tracking table
                if "symptoms" in request.form_data:
                    severity = request.form_data.get("painLevel", 5)
                    tracking_data = {
                        "user_id": request.user_id,
                        "quick_scan_id": scan_id,
                        "symptom_name": request.form_data["symptoms"],
                        "body_part": request.body_part,
                        "severity": severity
                    }
                    supabase.table("symptom_tracking").insert(tracking_data).execute()
                    
            except Exception as db_error:
                print(f"Database error (non-critical): {db_error}")
                # Continue even if DB save fails
        
        return {
            "scan_id": scan_id,
            "analysis": analysis_result,
            "body_part": request.body_part,
            "confidence": analysis_result.get("confidence", 0),
            "user_id": request.user_id,
            "usage": llm_response.get("usage", {}),
            "model": llm_response.get("model", "")
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
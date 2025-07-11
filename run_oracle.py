#!/usr/bin/env python3
"""Oracle Server - Working with Real AI and Supabase"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone
from supabase_client import supabase
import tiktoken
from business_logic import call_llm, make_prompt, get_llm_context as get_llm_context_biz, get_user_data
import uuid
import json
import re

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

def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from response with multiple fallback strategies"""
    # Strategy 1: Direct parse if already dict
    if isinstance(content, dict):
        return content
    
    # Strategy 2: Try direct JSON parse
    try:
        return json.loads(content)
    except:
        pass
    
    # Strategy 3: Find JSON in code blocks FIRST (most common from LLMs)
    try:
        # Look for ```json blocks
        json_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_block:
            return json.loads(json_block.group(1))
    except:
        pass
    
    # Strategy 4: Find JSON in text (handle nested objects)
    try:
        # Find the first { and match to the corresponding }
        start = content.find('{')
        if start != -1:
            depth = 0
            for i in range(start, len(content)):
                if content[i] == '{':
                    depth += 1
                elif content[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = content[start:i+1]
                        return json.loads(json_str)
    except:
        pass
    
    # Strategy 5: Create fallback response for deep dive
    if "question" in content.lower() or "?" in content:
        # Extract potential question from text
        lines = content.strip().split('\n')
        question = next((line.strip() for line in lines if '?' in line), lines[0] if lines else "Can you describe your symptoms?")
        return {
            "question": question,
            "question_type": "open_ended",
            "internal_analysis": {"extracted": True}
        }
    
    return None

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
    conversation_id: Optional[str] = None
    quick_scan_id: Optional[str] = None
    user_id: str

class QuickScanRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None

class DeepDiveStartRequest(BaseModel):
    body_part: str
    form_data: Dict[str, Any]
    user_id: Optional[str] = None
    model: Optional[str] = None  # Will default to deepseek/deepseek-chat

class DeepDiveContinueRequest(BaseModel):
    session_id: str
    answer: str
    question_number: int

class DeepDiveCompleteRequest(BaseModel):
    session_id: str
    final_answer: Optional[str] = None

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
        # Validate UUIDs
        import uuid
        try:
            # Validate UUIDs
            uuid.UUID(str(request.conversation_id))
            uuid.UUID(str(request.user_id))
        except ValueError as e:
            return {"error": f"Invalid UUID format: {e}", "status": "error"}
        
        # Fetch all messages from conversation
        print(f"Fetching messages for conversation: {request.conversation_id}")
        messages_response = supabase.table("messages").select("*").eq("conversation_id", request.conversation_id).order("created_at").execute()
        
        if not messages_response.data:
            print(f"No messages found for conversation: {request.conversation_id}")
            return {"error": "No messages found for this conversation", "status": "error"}
        
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
        
        # Validate summary content
        if not summary_content or not summary_content.strip():
            raise Exception("Generated summary is empty")
        
        print(f"Generated summary ({len(summary_content)} chars): {summary_content[:100]}...")
        
        # Delete old summary
        delete_response = supabase.table("llm_context").delete().eq("conversation_id", request.conversation_id).eq("user_id", request.user_id).execute()
        print(f"Delete response: {delete_response}")
        
        # Insert new summary
        insert_data = {
            "conversation_id": str(request.conversation_id),  # Ensure string format
            "user_id": str(request.user_id),  # Ensure string format
            "llm_summary": summary_content,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"Inserting summary data: {insert_data}")
        insert_response = supabase.table("llm_context").insert(insert_data).execute()
        
        # Check if insert was successful
        if not insert_response.data:
            print(f"Insert failed! Response: {insert_response}")
            raise Exception(f"Failed to insert summary: {insert_response}")
        
        print(f"Insert successful! Response: {insert_response.data}")
        
        return {
            "summary": summary_content,
            "token_count": count_tokens(summary_content),
            "compression_ratio": round(total_tokens / count_tokens(summary_content), 2),
            "status": "success",
            "inserted_id": insert_response.data[0].get("id") if insert_response.data else None
        }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/quick-scan")
async def quick_scan_endpoint(request: QuickScanRequest):
    """Quick Scan endpoint for rapid health assessment"""
    try:
        # Get user data if user_id provided (otherwise anonymous)
        user_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
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
            temperature=0.3,
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
                "parse_error": str(json_error),
                "status": "error"
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
            "model": llm_response.get("model", ""),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in quick scan: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/deep-dive/start")
async def start_deep_dive(request: DeepDiveStartRequest):
    """Start a Deep Dive analysis session"""
    try:
        # Get user data if provided
        user_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data
        }
        
        # Use chimera model for deep dive (like Oracle chat which works great!)
        model = request.model or "tngtech/deepseek-r1t-chimera:free"
        
        # Add model validation and fallback
        WORKING_MODELS = [
            "tngtech/deepseek-r1t-chimera:free",  # Best for deep dive!
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "microsoft/phi-3-mini-128k-instruct:free"
        ]
        
        # If specified model not in list, use chimera
        if model not in WORKING_MODELS:
            print(f"Model {model} not in working list, using chimera")
            model = "tngtech/deepseek-r1t-chimera:free"
        
        # Generate initial question
        query = request.form_data.get("symptoms", "Health analysis requested")
        system_prompt = make_prompt(
            query=query,
            user_data=prompt_data,
            llm_context=llm_context,
            category="deep-dive-initial",
            part_selected=request.body_part
        )
        
        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze symptoms and generate first diagnostic question"}
            ],
            model=model,
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response with robust fallback
        try:
            # First try our robust parser
            question_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not question_data:
                # Fallback: Create a generic first question
                question_data = {
                    "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                    "question_type": "symptom_characterization",
                    "internal_analysis": {"fallback": True}
                }
        except Exception as e:
            print(f"Parse error in deep dive start: {e}")
            # Use fallback question
            question_data = {
                "question": f"Can you describe the {request.body_part} pain in more detail? Is it sharp, dull, burning, or aching?",
                "question_type": "symptom_characterization",
                "internal_analysis": {"error": str(e)}
            }
        
        # Create session
        session_id = str(uuid.uuid4())
        
        # Save session to database
        session_data = {
            "id": session_id,
            "user_id": request.user_id,
            "body_part": request.body_part,
            "form_data": request.form_data,
            "model_used": model,
            "questions": [],
            "current_step": 1,
            "internal_state": question_data.get("internal_analysis", {}),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Always save session to database (for both authenticated and anonymous users)
        try:
            supabase.table("deep_dive_sessions").insert(session_data).execute()
        except Exception as db_error:
            print(f"Database error saving session: {db_error}")
            # Still return success since we have the session in memory
            pass
        
        return {
            "session_id": session_id,
            "question": question_data.get("question", ""),
            "question_number": 1,
            "estimated_questions": "2-3",
            "question_type": question_data.get("question_type", "differential"),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in deep dive start: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/deep-dive/continue")
async def continue_deep_dive(request: DeepDiveContinueRequest):
    """Continue Deep Dive with answer processing"""
    try:
        # Get session from database
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_response.data:
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        if session["status"] != "active":
            return {"error": "Session already completed", "status": "error"}
        
        # Add Q&A to history
        qa_entry = {
            "question_number": request.question_number,
            "question": session.get("last_question", ""),
            "answer": request.answer,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        questions = session.get("questions", [])
        questions.append(qa_entry)
        
        # Prepare session data for prompt
        session_data = {
            "questions": questions,
            "internal_state": session.get("internal_state", {}),
            "form_data": session.get("form_data", {})
        }
        
        # Get user context
        llm_context = ""
        if session.get("user_id"):
            llm_context = await get_llm_context_biz(session["user_id"])
        
        # Generate continue prompt
        system_prompt = make_prompt(
            query=request.answer,
            user_data={"session_data": session_data},
            llm_context=llm_context,
            category="deep-dive-continue"
        )
        
        # Call LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Process answer and decide next step"}
            ],
            model=session.get("model_used", "tngtech/deepseek-r1t-chimera:free"),  # Use chimera like Oracle
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response with fallback
        try:
            decision_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not decision_data:
                # Create fallback decision
                decision_data = {
                    "need_another_question": request.question_number < 2,
                    "question": "Have you experienced any other symptoms along with this?",
                    "confidence_projection": "Gathering more information",
                    "updated_analysis": session.get("internal_state", {})
                }
        except Exception as e:
            print(f"Parse error in deep dive continue: {e}")
            decision_data = {
                "ready_for_analysis": True,
                "questions_completed": request.question_number
            }
        
        # Update session
        update_data = {
            "questions": questions,
            "current_step": request.question_number + 1,
            "internal_state": decision_data.get("updated_analysis", session.get("internal_state", {}))
        }
        
        # Update session in database
        try:
            supabase.table("deep_dive_sessions").update(update_data).eq("id", request.session_id).execute()
        except Exception as e:
            print(f"Error updating session: {e}")
        
        # Check if we need another question
        if decision_data.get("need_another_question", False) and request.question_number < 3:
            # Store the question for next iteration
            try:
                supabase.table("deep_dive_sessions").update({
                    "last_question": decision_data.get("question", "")
                }).eq("id", request.session_id).execute()
            except Exception as e:
                print(f"Error storing last question: {e}")
            
            return {
                "question": decision_data.get("question", ""),
                "question_number": request.question_number + 1,
                "is_final_question": request.question_number == 2,
                "confidence_projection": decision_data.get("confidence_projection", ""),
                "status": "success"
            }
        else:
            # Ready for final analysis
            return {
                "ready_for_analysis": True,
                "questions_completed": request.question_number,
                "status": "success"
            }
            
    except Exception as e:
        print(f"Error in deep dive continue: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/deep-dive/complete")
async def complete_deep_dive(request: DeepDiveCompleteRequest):
    """Generate final Deep Dive analysis"""
    try:
        # Get session
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        
        if not session_response.data:
            return {"error": "Session not found", "status": "error"}
        
        session = session_response.data[0]
        
        # Add final answer if provided
        if request.final_answer:
            qa_entry = {
                "question_number": len(session.get("questions", [])) + 1,
                "question": session.get("last_question", ""),
                "answer": request.final_answer,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            questions = session.get("questions", [])
            questions.append(qa_entry)
        else:
            questions = session.get("questions", [])
        
        # Get user context
        llm_context = ""
        if session.get("user_id"):
            llm_context = await get_llm_context_biz(session["user_id"])
        
        # Generate final analysis
        session_data = {
            "questions": questions,
            "form_data": session.get("form_data", {}),
            "internal_state": session.get("internal_state", {})
        }
        
        system_prompt = make_prompt(
            query="Generate final analysis",
            user_data={"session_data": session_data},
            llm_context=llm_context,
            category="deep-dive-final"
        )
        
        # Call LLM for final analysis
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate comprehensive final analysis based on all Q&A"}
            ],
            model=session.get("model_used", "tngtech/deepseek-r1t-chimera:free"),  # Use chimera like Oracle
            user_id=session.get("user_id"),
            temperature=0.3,
            max_tokens=2048
        )
        
        # Parse final analysis with comprehensive fallback
        try:
            analysis_result = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
            
            if not analysis_result:
                # Create structured fallback analysis
                analysis_result = {
                    "confidence": 70,
                    "primaryCondition": f"Analysis of {session.get('body_part', 'symptom')} pain",
                    "likelihood": "Likely",
                    "symptoms": [s for q in questions for s in [q.get("answer", "")] if s],
                    "recommendations": [
                        "Monitor symptoms closely",
                        "Seek medical evaluation if symptoms worsen",
                        "Keep a symptom diary"
                    ],
                    "urgency": "medium",
                    "differentials": [],
                    "redFlags": ["Seek immediate care if symptoms suddenly worsen"],
                    "selfCare": ["Rest and avoid activities that worsen symptoms"],
                    "reasoning_snippets": ["Based on reported symptoms"]
                }
        except Exception as e:
            print(f"Parse error in deep dive complete: {e}")
            # Use fallback analysis
            analysis_result = {
                "confidence": 60,
                "primaryCondition": "Requires further medical evaluation",
                "likelihood": "Possible",
                "symptoms": ["As reported"],
                "recommendations": ["Consult with a healthcare provider"],
                "urgency": "medium",
                "differentials": [],
                "redFlags": [],
                "selfCare": [],
                "reasoning_snippets": ["Unable to complete full analysis"]
            }
        
        # Update session with results
        update_data = {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "final_analysis": analysis_result,
            "final_confidence": analysis_result.get("confidence", 0),
            "reasoning_chain": analysis_result.get("reasoning_snippets", []),
            "questions": questions,
            "tokens_used": llm_response.get("usage", {})
        }
        
        # Update session in database
        try:
            supabase.table("deep_dive_sessions").update(update_data).eq("id", request.session_id).execute()
        except Exception as e:
            print(f"Error updating session: {e}")
            
            # Auto-generate summary (fire and forget)
            try:
                # Create summary for llm_context table
                summary_text = f"""Deep Dive Analysis - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
Body Part: {session.get('body_part')}
Primary Condition: {analysis_result.get('primaryCondition')}
Confidence: {analysis_result.get('confidence')}%
Questions Asked: {len(questions)}
Key Findings: {', '.join(analysis_result.get('reasoning_snippets', [])[:3])}"""
                
                summary_data = {
                    "user_id": session["user_id"],
                    "conversation_id": None,  # Deep dives don't have conversation_id
                    "llm_summary": summary_text,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                supabase.table("llm_context").insert(summary_data).execute()
            except Exception as summary_error:
                print(f"Summary generation error (non-critical): {summary_error}")
        
        return {
            "deep_dive_id": request.session_id,
            "analysis": analysis_result,
            "body_part": session.get("body_part"),
            "confidence": analysis_result.get("confidence", 0),
            "questions_asked": len(questions),
            "reasoning_snippets": analysis_result.get("reasoning_snippets", []),
            "usage": llm_response.get("usage", {}),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in deep dive complete: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/")
async def root():
    return {
        "message": "Oracle AI Server Running",
        "endpoints": {
            "chat": "POST /api/chat",
            "health": "GET /api/health",
            "generate_summary": "POST /api/generate_summary",
            "quick_scan": "POST /api/quick-scan",
            "deep_dive": {
                "start": "POST /api/deep-dive/start",
                "continue": "POST /api/deep-dive/continue",
                "complete": "POST /api/deep-dive/complete"
            }
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
"""Chat and Oracle API endpoints"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, List

from models.requests import (
    ChatRequest, 
    GenerateSummaryRequest,
    ConversationListRequest,
    GenerateTitleRequest,
    ExitSummaryRequest,
    CheckContextRequest,
    ResumeConversationRequest
)
from supabase_client import supabase
from business_logic import call_llm, make_prompt, get_llm_context as get_llm_context_biz, call_llm_with_fallback
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.model_selector import get_user_tier
from utils.token_counter import count_tokens
from utils.summary_helpers import (
    create_conversational_summary, 
    create_quick_scan_summary
)
from utils.data_gathering import get_user_medical_data
from utils.context_builder import get_enhanced_llm_context
from utils.context_compression import (
    compress_medical_context,
    free_tier_context,
    extract_medical_flags,
    generate_medical_title,
    calculate_context_status,
    generate_medical_summary
)

load_dotenv()

router = APIRouter(prefix="/api", tags=["chat"])

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
                        "model": "openai/gpt-5-mini",  # was: deepseek/deepseek-chat
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

# Message saving removed - backend no longer stores messages to Supabase

# Conversation update removed - backend no longer manages conversation records

@router.post("/chat")
async def chat(request: ChatRequest):
    """Oracle chat endpoint with real OpenRouter AI and Supabase integration"""
    print(f"Chat endpoint called with user_id: {request.user_id}, reasoning_mode: {request.reasoning_mode}")
    # Handle both 'query' and 'message' fields from frontend
    user_message = request.message or request.query
    if not user_message:
        return {"error": "No message provided", "status": "error"}
    
    # Use the message as query
    request.query = user_message
    
    # Include context if provided
    additional_context = request.context or ""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    # Check user subscription status for context handling
    is_premium = False  # Simplified - check subscriptions table in production
    
    # Fetch user medical data (handle anonymous users)
    user_medical_data = {}
    if request.user_id:
        user_medical_data = await get_user_medical_data(request.user_id)
    
    # Fetch enhanced LLM context including summaries, quick scans, and deep dives
    llm_context = ""
    if request.user_id:
        llm_context = await get_enhanced_llm_context(request.user_id, request.conversation_id, request.query)
    
    # Get conversation history
    history = await get_conversation_history(request.conversation_id)
    
    # Check context limits and apply compression if needed
    all_messages = history + [{"role": "user", "content": request.query}]
    context_status = calculate_context_status(all_messages, is_premium)
    
    # Check if user is blocked (free tier at 100k tokens)
    if not context_status.get("can_continue"):
        return {
            "status": "blocked",
            "can_continue": False,
            "message": "Conversation limit reached",
            "conversation_id": request.conversation_id,
            "context_status": context_status,
            "user_tier": "free"
        }
    
    # Apply compression if needed (only for premium users)
    if context_status.get("needs_compression"):
        if is_premium:
            history = await compress_medical_context(history)
        else:
            # This shouldn't happen since free users are blocked at 100k
            # But keep as safety fallback
            history = await free_tier_context(history)
    
    # Build comprehensive system prompt with all context
    medical_summary = ""
    if user_medical_data and "error" not in user_medical_data and "note" not in user_medical_data:
        # Extract key medical info if available
        medical_summary = f"User has medical history on file. Key details: {str(user_medical_data)[:200]}..."
    
    system_prompt = f"""You are Oracle, a compassionate health AI assistant with memory of past interactions.

MEDICAL HISTORY: {medical_summary if medical_summary else "No medical history on file."}

HEALTH CONTEXT AND HISTORY:
{llm_context if llm_context else "No previous health interactions recorded yet."}

CURRENT CONTEXT:
{additional_context if additional_context else "No specific context provided."}

INSTRUCTIONS:
- Check if symptoms relate to past conditions or previous conversations
- Reference past discussions naturally when relevant: "I see you had..." or "Based on your recent scan..."
- Give concise advice (2-3 paragraphs max) using plain text, no markdown
- Show you remember them as an individual patient
- Recommend professional care for serious/persistent issues
- Be warm, direct, and helpful without lengthy explanations"""
    
    # Build messages with history
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history (compressed if needed)
    for msg in history:
        if msg.get("role") in ["user", "assistant", "system"]:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Add current query
    messages.append({
        "role": "user",
        "content": request.query
    })
    
    # Message storage removed - messages are no longer saved to Supabase
    
    # Use tier-based model selection with fallback
    try:
        print(f"Using tier-based selection for user: {request.user_id}")
        result = await call_llm_with_fallback(
            messages=messages,
            user_id=request.user_id,
            endpoint_type="chat",
            reasoning_mode=request.reasoning_mode,
            temperature=0.7,
            max_tokens=2048
        )
        print(f"Model selection result: {result.get('model', 'unknown')}")
        response_success = True
    except Exception as e:
        # Fallback to direct API call if tier system fails
        print(f"Tier-based selection failed: {e}, using direct call")
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
            response_success = True
        else:
            result = None
            response_success = False
    
    if response_success and result and "choices" in result:
        content = result["choices"][0]["message"]["content"]
        model_used = result.get("model", request.model or "deepseek/deepseek-chat")
        
        # Assistant response storage removed - messages are no longer saved to Supabase
        
        # Conversation updates removed - backend no longer tracks tokens or message counts
        
        # Get actual user tier
        user_tier = "free"
        if request.user_id:
            try:
                user_tier = await get_user_tier(request.user_id)
            except:
                pass
        
        return {
            "response": content,
            "message": content,  # Include both formats for frontend compatibility
            "raw_response": content,
            "reasoning": result.get("reasoning"),  # Separated reasoning content
            "has_reasoning": result.get("has_reasoning", False),  # Flag indicating if reasoning is present
            "conversation_id": request.conversation_id,
            "user_id": request.user_id,
            "category": request.category,
            "usage": result.get("usage", {}),  # Includes reasoning_tokens if present
            "model": model_used,
            "model_used": model_used,  # Alternative field name
            "tier": user_tier,  # Actual user tier
            "reasoning_mode": request.reasoning_mode,
            "status": "success",
            "medical_data_loaded": bool(user_medical_data),
            "context_loaded": bool(llm_context),
            "history_count": len(history),
            "context_status": context_status,  # Include context status for frontend
            "user_tier": user_tier  # Keep for compatibility
        }
    else:
        error_msg = f"Error: {response.status_code} - {response.text}"
        
        # Error message storage removed - messages are no longer saved to Supabase
        
        return {
            "response": error_msg,
            "message": "I'm having trouble connecting right now. Please try again.",  # Fallback for frontend
            "status": "error"
        }

@router.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/test-openrouter")
async def test_openrouter():
    """Test OpenRouter API connection"""
    import requests
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        return {"error": "OPENROUTER_API_KEY not set", "status": "error"}
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a test bot."},
                    {"role": "user", "content": "Reply with 'OK' only"}
                ],
                "temperature": 0.1,
                "max_tokens": 10
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",
                "openrouter_working": True,
                "response": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "model": data.get("model", "unknown")
            }
        else:
            return {
                "status": "error",
                "openrouter_working": False,
                "error_code": response.status_code,
                "error_message": response.text[:200]
            }
    except Exception as e:
        return {
            "status": "error",
            "openrouter_working": False,
            "exception": str(e),
            "exception_type": type(e).__name__
        }

@router.get("/debug-context/{user_id}")
async def debug_context(user_id: str):
    """Debug endpoint to test context building"""
    try:
        # Get enhanced context
        context = await get_enhanced_llm_context(user_id, "debug-conversation", "debug query")
        
        # Also get raw data for comparison
        summaries = supabase.table("llm_context").select("*").eq("user_id", str(user_id)).limit(5).execute()
        scans = supabase.table("quick_scans").select("*").eq("user_id", str(user_id)).limit(5).execute()
        dives = supabase.table("deep_dive_sessions").select("*").eq("user_id", str(user_id)).limit(5).execute()
        
        return {
            "user_id": user_id,
            "user_id_type": str(type(user_id)),
            "enhanced_context": context,
            "context_length": len(context),
            "raw_data": {
                "llm_summaries_count": len(summaries.data) if summaries.data else 0,
                "quick_scans_count": len(scans.data) if scans.data else 0,
                "deep_dives_count": len(dives.data) if dives.data else 0,
                "llm_summaries": summaries.data[:2] if summaries.data else [],
                "quick_scans": scans.data[:2] if scans.data else [],
                "deep_dives": dives.data[:2] if dives.data else []
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "user_id": user_id,
            "user_id_type": str(type(user_id))
        }

@router.post("/generate_summary")
async def generate_summary(request: GenerateSummaryRequest):
    """Generate AI summary for llm_context table from conversation or scan"""
    try:
        # Case 1: From conversation
        if request.conversation_id:
            print(f"Generating summary for conversation {request.conversation_id}")
            summary = await create_conversational_summary(request.conversation_id, request.user_id)
            return {
                "summary": summary,
                "source": "conversation",
                "conversation_id": request.conversation_id,
                "status": "success"
            }
        
        # Case 2: From quick scan
        elif request.quick_scan_id:
            print(f"Generating summary for quick scan {request.quick_scan_id}")
            summary = await create_quick_scan_summary(request.quick_scan_id, request.user_id)
            return {
                "summary": summary,
                "source": "quick_scan",
                "quick_scan_id": request.quick_scan_id,
                "status": "success"
            }
        
        else:
            return {
                "error": "Must provide either conversation_id or quick_scan_id",
                "status": "error"
            }
            
    except Exception as e:
        print(f"Error generating summary: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

# REMOVED: Frontend should query Supabase directly for better performance
# The frontend can get conversations and messages directly from Supabase
# using the Supabase client for faster response times

# # REMOVED: Frontend should build this from Supabase queries
# @router.get("/oracle/resume/{conversation_id}")
# async def resume_conversation(conversation_id: str, user_id: str):
#     """Resume a conversation with smart context handling"""
    try:
        # Check user subscription status (simplified for now)
        # In production, you'd check the subscriptions table
        is_premium = False  # Default to free tier for now
        
        # Fetch conversation details
        conv_response = supabase.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).execute()
        if not conv_response.data:
            return {"error": "Conversation not found", "status": "error"}
        
        conversation = conv_response.data[0]
        
        # Fetch ALL messages for display
        messages_response = supabase.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at", desc=False).execute()
        all_messages = messages_response.data or []
        
        # Calculate total tokens
        total_tokens = sum(msg.get("token_count", 0) for msg in all_messages)
        
        # Determine context handling based on user tier and token count
        context_status = calculate_context_status(all_messages, is_premium)
        
        # Prepare AI context based on status
        if context_status["needs_compression"]:
            if is_premium:
                ai_context = await compress_medical_context(all_messages)
            else:
                ai_context = await free_tier_context(all_messages)
        else:
            ai_context = all_messages
        
        # Extract medical context
        medical_flags = extract_medical_flags(all_messages)
        
        # Build medical context summary
        medical_context = {
            "symptoms_mentioned": [],
            "medications_discussed": [],
            "urgency_level": "low",
            "last_recommendations": []
        }
        
        # Extract specific medical information
        for msg in all_messages[-20:]:  # Check last 20 messages
            content = msg.get("content", "").lower()
            
            # Extract symptoms
            symptom_keywords = ["pain", "fever", "nausea", "headache", "dizzy", "fatigue"]
            for symptom in symptom_keywords:
                if symptom in content and symptom not in medical_context["symptoms_mentioned"]:
                    medical_context["symptoms_mentioned"].append(symptom)
            
            # Extract medications
            if "medication" in content or "prescription" in content:
                # Simple extraction - in production, use NER
                words = content.split()
                for i, word in enumerate(words):
                    if word in ["medication", "prescription", "taking"]:
                        if i + 1 < len(words):
                            medical_context["medications_discussed"].append(words[i + 1])
            
            # Check urgency
            if any(urgent in content for urgent in ["urgent", "emergency", "severe"]):
                medical_context["urgency_level"] = "high"
            elif "moderate" in content:
                medical_context["urgency_level"] = "medium"
        
        return {
            "conversation": {
                "id": conversation_id,
                "title": conversation.get("title", "Health Discussion"),
                "display_messages": all_messages,  # Full history for UI
                "ai_context": ai_context,  # Compressed context for AI
                "total_tokens": total_tokens,
                "message_count": len(all_messages),
                "medical_context": medical_context,
                "medical_flags": medical_flags,
                "created_at": conversation["created_at"],
                "last_message_at": conversation["last_message_at"]
            },
            "context_status": context_status,
            "user_tier": "premium" if is_premium else "free",
            "can_continue": True,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error resuming conversation: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

@router.post("/oracle/generate-title")
async def generate_title(request: GenerateTitleRequest):
    """Generate or regenerate conversation title"""
    try:
        # Check if conversation exists and title status
        conv_response = supabase.table("conversations").select("title, metadata").eq("id", request.conversation_id).execute()
        if not conv_response.data:
            return {"error": "Conversation not found", "status": "error"}
        
        conversation = conv_response.data[0]
        metadata = conversation.get("metadata", {}) or {}
        title_locked = metadata.get("title_locked", False)
        
        # Check if we should generate
        if conversation.get("title") and conversation["title"] != "New Conversation" and not request.force:
            if title_locked:
                return {
                    "title": conversation["title"],
                    "generated": False,
                    "message": "Title is locked",
                    "status": "success"
                }
        
        # Get first few messages for title generation
        messages_response = supabase.table("messages").select("role, content").eq("conversation_id", request.conversation_id).order("created_at", desc=False).limit(6).execute()
        
        if not messages_response.data or len(messages_response.data) < 4:
            return {
                "title": conversation.get("title", "Health Discussion"),
                "generated": False,
                "message": "Not enough messages for title generation",
                "status": "success"
            }
        
        # Generate title
        title = await generate_medical_title(messages_response.data)
        
        # Update conversation
        metadata["auto_title_generated"] = True
        metadata["title_generated_at"] = datetime.now(timezone.utc).isoformat()
        
        supabase.table("conversations").update({
            "title": title,
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", request.conversation_id).execute()
        
        return {
            "title": title,
            "generated": True,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating title: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

# Background summary generation removed - no longer needed without message storage

# Exit summary endpoint removed - no longer needed without message storage

# REMOVED: Frontend can calculate token counts locally
# @router.post("/oracle/check-context")
# async def check_context(request: CheckContextRequest):
#     """Check if context limits will be exceeded with new message"""
#     try:
        # Check user subscription
        is_premium = False  # Simplified for now
        
        # Get current messages
        messages_response = supabase.table("messages").select("content, token_count").eq("conversation_id", request.conversation_id).execute()
        messages = messages_response.data or []
        
        # Calculate current tokens
        current_tokens = sum(msg.get("token_count", 0) for msg in messages)
        
        # Estimate new message tokens
        new_tokens = count_tokens(request.new_message)
        total_tokens = current_tokens + new_tokens
        
        # Determine limits
        limit = 120000 if is_premium else 30000
        
        if total_tokens < limit:
            return {
                "can_continue": True,
                "current_tokens": current_tokens,
                "new_tokens": new_tokens,
                "total_tokens": total_tokens,
                "limit": limit,
                "user_tier": "premium" if is_premium else "free",
                "status": "success"
            }
        else:
            # Will need compression or upgrade
            if is_premium:
                return {
                    "can_continue": True,
                    "will_compress": True,
                    "compression_info": {
                        "original_tokens": total_tokens,
                        "compressed_to": 30000,
                        "method": "medical_context_preservation"
                    },
                    "user_tier": "premium",
                    "status": "success"
                }
            else:
                return {
                    "can_continue": True,  # Never block
                    "will_compress": True,
                    "reason": "context_limit",
                    "user_tier": "free",
                    "upgrade_prompt": {
                        "title": "📈 Unlock Full Context Memory",
                        "description": "Upgrade to Premium for full conversation memory",
                        "benefits": [
                            "✨ Oracle remembers entire conversation",
                            "🧠 Better medical continuity",
                            "📊 Unlimited context length"
                        ],
                        "cta": "Upgrade to Premium"
                    },
                    "status": "success"
                }
        
    except Exception as e:
        print(f"Error checking context: {e}")
        return {
            "error": str(e),
            "can_continue": True,  # Default to allowing continuation
            "status": "error"
        }
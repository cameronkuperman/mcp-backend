#!/usr/bin/env python3
"""Oracle Server - Working with Real AI and Supabase"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
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

class HealthStoryRequest(BaseModel):
    user_id: str
    date_range: Optional[Dict[str, str]] = None  # {"start": "ISO date", "end": "ISO date"}
    include_data: Optional[Dict[str, bool]] = None  # Which data sources to include

# Report Generation Models
class ReportAnalyzeRequest(BaseModel):
    user_id: Optional[str] = None
    context: Dict[str, Any] = {}
    available_data: Optional[Dict[str, List[str]]] = None

class ComprehensiveReportRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None

class UrgentTriageRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None

class PhotoProgressionRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None

class SymptomTimelineRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    symptom_focus: Optional[str] = None

class SpecialistReportRequest(BaseModel):
    analysis_id: str
    user_id: Optional[str] = None
    specialty: Optional[str] = None

class AnnualSummaryRequest(BaseModel):
    analysis_id: str
    user_id: str  # Required for annual
    year: Optional[int] = None

class TimePeriodReportRequest(BaseModel):
    user_id: str
    include_wearables: Optional[bool] = False

class DoctorNotesRequest(BaseModel):
    doctor_npi: str
    specialty: str
    notes: str
    sections_reviewed: List[str]
    diagnosis: Optional[str] = None
    plan_modifications: Optional[Dict[str, Any]] = None
    follow_up_instructions: Optional[str] = None

class ShareReportRequest(BaseModel):
    shared_by_npi: str
    recipient_npi: str
    access_level: str = "read_only"  # read_only, full_access
    expiration_days: int = 30
    notes: Optional[str] = None
    base_url: str

class RateReportRequest(BaseModel):
    doctor_npi: str
    usefulness_score: int  # 1-5
    accuracy_score: int    # 1-5
    time_saved: int       # minutes
    would_recommend: bool
    feedback: Optional[str] = None

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

async def get_health_story_data(user_id: str, date_range: Optional[Dict[str, str]] = None) -> dict:
    """Gather all relevant data for health story generation"""
    
    # Default to last 7 days if no date range provided
    if not date_range:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        date_range = {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        }
    
    # Debug: print the date range being used
    print(f"Health story date range: {date_range['start']} to {date_range['end']}")
    
    data = {
        "medical_profile": None,
        "oracle_chats": [],
        "quick_scans": [],
        "deep_dives": [],
        "symptom_tracking": []
    }
    
    try:
        # Get medical profile
        data["medical_profile"] = await get_user_medical_data(user_id)
        
        # Get Oracle chat messages - need to join through conversations table
        # First get user's conversations
        conv_response = supabase.table("conversations")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        conversation_ids = [conv["id"] for conv in (conv_response.data or [])]
        
        # Then get messages from those conversations
        if conversation_ids:
            chat_response = supabase.table("messages")\
                .select("*")\
                .in_("conversation_id", conversation_ids)\
                .gte("created_at", date_range["start"])\
                .lte("created_at", date_range["end"])\
                .order("created_at", desc=False)\
                .execute()
            data["oracle_chats"] = chat_response.data if chat_response.data else []
        else:
            data["oracle_chats"] = []
        
        # Get Quick Scans - comprehensive debugging
        print("\n=== QUICK SCAN RETRIEVAL DEBUG ===")
        print(f"Querying quick_scans for user_id: '{user_id}'")
        print(f"User ID type: {type(user_id)}")
        print(f"User ID repr: {repr(user_id)}")
        print(f"User ID length: {len(str(user_id)) if user_id else 0}")
        
        # Try multiple approaches to get quick scans
        
        # Approach 1: Try with string conversion (since quick_scans.user_id is text)
        print("\nApproach 1: Converting user_id to string")
        scan_response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .execute()
        data["quick_scans"] = scan_response.data if scan_response.data else []
        print(f"Result: {len(data['quick_scans'])} scans found")
        
        # Approach 2: If no results, try without conversion
        if not data["quick_scans"]:
            print("\nApproach 2: Using user_id as-is")
            scan_response = supabase.table("quick_scans")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            data["quick_scans"] = scan_response.data if scan_response.data else []
            print(f"Result: {len(data['quick_scans'])} scans found")
        
        # Approach 3: If still no results, try to get ANY quick scan to see format
        if not data["quick_scans"]:
            print("\nApproach 3: Getting sample quick scans to check user_id format")
            sample_response = supabase.table("quick_scans")\
                .select("id, user_id, body_part, created_at")\
                .limit(5)\
                .execute()
            if sample_response.data:
                print(f"Found {len(sample_response.data)} sample scans:")
                for sample in sample_response.data:
                    print(f"  - user_id: '{sample.get('user_id')}' (type: {type(sample.get('user_id'))}, len: {len(str(sample.get('user_id', '')))})")
                    print(f"    body_part: {sample.get('body_part')}, created: {sample.get('created_at')}")
                
                # Check if our user_id matches any of these formats
                print(f"\nComparing our user_id '{user_id}' with sample user_ids...")
                for sample in sample_response.data:
                    if str(user_id).lower() == str(sample.get('user_id', '')).lower():
                        print(f"  MATCH FOUND (case-insensitive): '{sample.get('user_id')}'")
            else:
                print("No quick scans found in the entire table!")
        
        # If we found scans, show details
        if data["quick_scans"]:
            print(f"\n✓ Successfully retrieved {len(data['quick_scans'])} quick scans")
            first_scan = data["quick_scans"][0]
            print(f"Sample scan: body_part={first_scan.get('body_part')}, created={first_scan.get('created_at')}")
        else:
            print("\n✗ No quick scans found for this user")
            print("Possible issues:")
            print("1. User ID format mismatch (UUID vs string)")
            print("2. Quick scans saved with different user_id")
            print("3. No quick scans exist for this user")
            print("4. Database connection or permission issue")
        
        print("=== END DEBUG ===\n")
        
        # Debug: Print first quick scan if available
        if data["quick_scans"]:
            first_scan = data["quick_scans"][0]
            print(f"Sample quick scan data: body_part={first_scan.get('body_part')}, confidence={first_scan.get('confidence_score')}")
            if first_scan.get('analysis_result'):
                print(f"Analysis contains: primaryCondition={first_scan['analysis_result'].get('primaryCondition')}")
        
        # Get Deep Dive sessions (user_id is text type)
        dive_response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .gte("created_at", date_range["start"])\
            .lte("created_at", date_range["end"])\
            .order("created_at", desc=False)\
            .execute()
        data["deep_dives"] = dive_response.data if dive_response.data else []
        
        # Get symptom tracking data (user_id is text type)
        symptom_response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .gte("occurrence_date", date_range["start"])\
            .lte("occurrence_date", date_range["end"])\
            .order("occurrence_date", desc=False)\
            .execute()
        data["symptom_tracking"] = symptom_response.data if symptom_response.data else []
        
    except Exception as e:
        print(f"Error gathering health story data: {e}")
    
    return data

# Report Generation Helper Functions
async def safe_insert_report(report_record: dict) -> bool:
    """Safely insert report, handling missing columns"""
    try:
        # Try full insert first
        supabase.table("medical_reports").insert(report_record).execute()
        return True
    except Exception as e:
        print(f"Full insert failed: {e}")
        # If it fails, try without optional columns
        essential_fields = [
            "id", "user_id", "analysis_id", "report_type", 
            "created_at", "report_data", "executive_summary",
            "confidence_score", "model_used"
        ]
        clean_record = {k: v for k, v in report_record.items() if k in essential_fields}
        try:
            supabase.table("medical_reports").insert(clean_record).execute()
            print("Insert succeeded with essential fields only")
            return True
        except Exception as e2:
            print(f"Essential insert also failed: {e2}")
            return False

async def gather_report_data(user_id: str, config: dict) -> dict:
    """Gather all data needed for report generation"""
    data = {
        "quick_scans": [],
        "deep_dives": [],
        "symptom_tracking": [],
        "photo_sessions": []
    }
    
    time_range = config.get("time_range", {})
    
    # Get Quick Scans
    if config.get("data_sources", {}).get("quick_scans"):
        scan_ids = config["data_sources"]["quick_scans"]
        scan_response = supabase.table("quick_scans")\
            .select("*")\
            .in_("id", scan_ids)\
            .execute()
        data["quick_scans"] = scan_response.data or []
    
    # Get Deep Dives
    if config.get("data_sources", {}).get("deep_dives"):
        dive_ids = config["data_sources"]["deep_dives"]
        dive_response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .in_("id", dive_ids)\
            .eq("status", "completed")\
            .execute()
        data["deep_dives"] = dive_response.data or []
    
    # Get Symptom Tracking with intelligent merge
    tracking_response = supabase.table("symptom_tracking")\
        .select("*")\
        .eq("user_id", str(user_id) if user_id else "")\
        .gte("created_at", time_range.get("start", ""))\
        .lte("created_at", time_range.get("end", ""))\
        .execute()
    
    # Merge symptom tracking with related sessions
    for entry in (tracking_response.data or []):
        # Find related quick scan or deep dive
        related_session = None
        if entry.get("quick_scan_id"):
            related_session = next((s for s in data["quick_scans"] if s["id"] == entry["quick_scan_id"]), None)
        
        entry["related_session"] = related_session
        entry["enriched_context"] = extract_session_context(related_session) if related_session else None
        data["symptom_tracking"].append(entry)
    
    return data

def extract_session_context(session: dict) -> dict:
    """Extract relevant context from a session"""
    if not session:
        return {}
    
    return {
        "primary_condition": session.get("analysis_result", {}).get("primaryCondition"),
        "confidence": session.get("confidence_score", 0),
        "recommendations": session.get("analysis_result", {}).get("recommendations", [])[:2],
        "urgency": session.get("urgency_level", "low")
    }

def has_emergency_indicators(request: ReportAnalyzeRequest) -> bool:
    """Check for emergency/urgent indicators"""
    context = request.context
    
    # Check explicit emergency purpose
    if context.get("purpose") == "emergency":
        return True
    
    # Check for high-urgency symptoms
    urgent_symptoms = ["chest pain", "difficulty breathing", "severe headache", "sudden weakness"]
    symptom_focus = context.get("symptom_focus", "").lower()
    
    return any(urgent in symptom_focus for urgent in urgent_symptoms)

def determine_time_range(context: dict, report_type: str) -> dict:
    """Determine appropriate time range for report"""
    now = datetime.now(timezone.utc)
    
    # Use provided time frame if available
    if context.get("time_frame"):
        return context["time_frame"]
    
    # Default ranges by report type
    if report_type == "annual_summary":
        return {
            "start": (now - timedelta(days=365)).isoformat(),
            "end": now.isoformat()
        }
    elif report_type == "urgent_triage":
        return {
            "start": (now - timedelta(days=7)).isoformat(),
            "end": now.isoformat()
        }
    else:
        # Default to 30 days
        return {
            "start": (now - timedelta(days=30)).isoformat(),
            "end": now.isoformat()
        }

async def load_analysis(analysis_id: str):
    """Load analysis from database"""
    response = supabase.table("report_analyses")\
        .select("*")\
        .eq("id", analysis_id)\
        .execute()
    
    if not response.data:
        raise ValueError("Analysis not found")
    
    return response.data[0]

async def gather_comprehensive_data(user_id: str, config: dict):
    """Gather ALL available data for time-based reports"""
    time_range = config.get("time_range", {})
    
    # Quick Scans
    scans = supabase.table("quick_scans")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Deep Dives
    dives = supabase.table("deep_dive_sessions")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "completed")\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Symptom Tracking
    tracking = supabase.table("symptom_tracking")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    # Long-term tracking data
    tracking_configs = supabase.table("tracking_configurations")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("status", "approved")\
        .execute()
    
    tracking_data = []
    for config_item in (tracking_configs.data or []):
        points = supabase.table("tracking_data_points")\
            .select("*")\
            .eq("configuration_id", config_item["id"])\
            .gte("recorded_at", time_range.get("start", "2020-01-01"))\
            .lte("recorded_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
            .order("recorded_at")\
            .execute()
        
        if points.data:
            tracking_data.append({
                "metric": config_item["metric_name"],
                "data_points": points.data
            })
    
    # LLM Chat Summaries
    chats = supabase.table("oracle_chats")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("created_at", time_range.get("start", "2020-01-01"))\
        .lte("created_at", time_range.get("end", datetime.now(timezone.utc).isoformat()))\
        .order("created_at")\
        .execute()
    
    return {
        "quick_scans": scans.data or [],
        "deep_dives": dives.data or [],
        "symptom_tracking": tracking.data or [],
        "tracking_data": tracking_data,
        "llm_summaries": chats.data or [],
        "wearables": {}  # Placeholder for wearables integration
    }

async def extract_cardiac_patterns(data: dict) -> str:
    """Extract cardiac-specific patterns from data"""
    cardiac_symptoms = ["chest pain", "palpitations", "shortness of breath", "dizziness", "heart"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(symptom in form_data_str for symptom in cardiac_symptoms):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "severity": scan.get("form_data", {}).get("painLevel"),
                "analysis": scan.get("analysis_result", {})
            })
    
    for dive in data.get("deep_dives", []):
        dive_str = str(dive).lower()
        if any(symptom in dive_str for symptom in cardiac_symptoms):
            relevant_data.append({
                "date": dive["created_at"],
                "body_part": dive["body_part"],
                "final_analysis": dive.get("final_analysis", {})
            })
    
    return f"Cardiac-specific data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_neuro_patterns(data: dict) -> str:
    """Extract neurology-specific patterns from data"""
    neuro_symptoms = ["headache", "migraine", "dizziness", "numbness", "tingling", "vision"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(symptom in form_data_str for symptom in neuro_symptoms):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "severity": scan.get("form_data", {}).get("painLevel"),
                "analysis": scan.get("analysis_result", {})
            })
    
    return f"Neurological data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_mental_health_patterns(data: dict) -> str:
    """Extract mental health patterns from data"""
    psych_keywords = ["anxiety", "depression", "stress", "mood", "sleep", "panic", "worry"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in psych_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "analysis": scan.get("analysis_result", {})
            })
    
    return f"Mental health data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data, indent=2)

async def extract_dermatology_patterns(data: dict, photo_data: dict) -> str:
    """Extract dermatology patterns including photo data"""
    derm_keywords = ["rash", "skin", "itching", "lesion", "mole", "spot"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in derm_keywords):
            relevant_data.append(scan)
    
    return f"Dermatology data found: {len(relevant_data)} text entries, {len(photo_data)} photos\n" + json.dumps(relevant_data[:5], indent=2)

async def extract_gi_patterns(data: dict) -> str:
    """Extract GI patterns from data"""
    gi_keywords = ["stomach", "abdominal", "nausea", "diarrhea", "constipation", "bloating"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in gi_keywords):
            relevant_data.append(scan)
    
    return f"GI data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def extract_endocrine_patterns(data: dict) -> str:
    """Extract endocrine patterns from data"""
    endo_keywords = ["fatigue", "weight", "thyroid", "diabetes", "energy", "temperature"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in endo_keywords):
            relevant_data.append(scan)
    
    return f"Endocrine data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def extract_pulmonary_patterns(data: dict) -> str:
    """Extract pulmonary patterns from data"""
    pulm_keywords = ["breathing", "cough", "wheeze", "asthma", "shortness", "chest"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in pulm_keywords):
            relevant_data.append(scan)
    
    return f"Pulmonary data found: {len(relevant_data)} relevant entries\n" + json.dumps(relevant_data[:10], indent=2)

async def gather_photo_data(user_id: str, config: dict):
    """Placeholder for photo data gathering"""
    # This would integrate with your photo storage system
    return []

async def save_specialist_report(report_id: str, request, specialty: str, report_data: dict):
    """Save specialist report to database"""
    report_record = {
        "id": report_id,
        "user_id": request.user_id,
        "analysis_id": request.analysis_id,
        "report_type": specialty,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "report_data": report_data,
        "executive_summary": report_data.get("executive_summary", {}).get("one_page_summary", ""),
        "confidence_score": 85,
        "model_used": "tngtech/deepseek-r1t-chimera:free",
        "specialty": specialty
    }
    
    await safe_insert_report(report_record)

async def group_data_by_month(all_data: dict):
    """Group health data by month for annual reports"""
    monthly_data = {}
    
    for scan in all_data.get("quick_scans", []):
        month = scan["created_at"][:7]  # YYYY-MM
        if month not in monthly_data:
            monthly_data[month] = {"quick_scans": 0, "deep_dives": 0, "symptoms": {}, "total_interactions": 0}
        monthly_data[month]["quick_scans"] += 1
        
        # Count symptoms
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        if symptoms:
            if symptoms not in monthly_data[month]["symptoms"]:
                monthly_data[month]["symptoms"][symptoms] = 0
            monthly_data[month]["symptoms"][symptoms] += 1
    
    for dive in all_data.get("deep_dives", []):
        month = dive["created_at"][:7]
        if month not in monthly_data:
            monthly_data[month] = {"quick_scans": 0, "deep_dives": 0, "symptoms": {}, "total_interactions": 0}
        monthly_data[month]["deep_dives"] += 1
    
    # Calculate totals
    for month in monthly_data:
        monthly_data[month]["total_interactions"] = (
            monthly_data[month]["quick_scans"] + 
            monthly_data[month]["deep_dives"]
        )
    
    return monthly_data

def count_symptoms_by_frequency(all_data: dict):
    """Count symptom frequency across all data"""
    symptom_counts = {}
    
    for scan in all_data.get("quick_scans", []):
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        if symptoms:
            if symptoms not in symptom_counts:
                symptom_counts[symptoms] = {"count": 0, "severity_sum": 0}
            symptom_counts[symptoms]["count"] += 1
            severity = scan.get("form_data", {}).get("painLevel", 5)
            symptom_counts[symptoms]["severity_sum"] += severity
    
    # Calculate averages
    result = []
    for symptom, data in symptom_counts.items():
        result.append({
            "symptom": symptom,
            "frequency": data["count"],
            "average_severity": round(data["severity_sum"] / data["count"], 1)
        })
    
    return sorted(result, key=lambda x: x["frequency"], reverse=True)

def analyze_seasonal_patterns(all_data: dict):
    """Analyze seasonal patterns in health data"""
    seasonal_data = {
        "winter": {"months": ["12", "01", "02"], "symptoms": {}},
        "spring": {"months": ["03", "04", "05"], "symptoms": {}},
        "summer": {"months": ["06", "07", "08"], "symptoms": {}},
        "fall": {"months": ["09", "10", "11"], "symptoms": {}}
    }
    
    for scan in all_data.get("quick_scans", []):
        month = scan["created_at"][5:7]  # MM
        symptoms = scan.get("form_data", {}).get("symptoms", "")
        
        for season, data in seasonal_data.items():
            if month in data["months"] and symptoms:
                if symptoms not in data["symptoms"]:
                    data["symptoms"][symptoms] = 0
                data["symptoms"][symptoms] += 1
    
    # Get top symptoms per season
    result = {}
    for season, data in seasonal_data.items():
        top_symptoms = sorted(data["symptoms"].items(), key=lambda x: x[1], reverse=True)[:3]
        result[season] = [s[0] for s in top_symptoms]
    
    return result

async def get_average_rating(report_id: str, field: str):
    """Get average rating for a report"""
    response = supabase.table("report_ratings")\
        .select(field)\
        .eq("report_id", report_id)\
        .execute()
    
    if not response.data:
        return None
    
    ratings = [r[field] for r in response.data if r[field] is not None]
    return round(sum(ratings) / len(ratings), 1) if ratings else None

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
PREVIOUS CONVERSATIONS: {llm_context[:300] + "..." if llm_context else "This is our first conversation."}

INSTRUCTIONS:
- Check if symptoms relate to past conditions or previous conversations
- Reference past discussions naturally: "As we discussed..." or "Given your history of..."
- Give concise advice (2-3 paragraphs max) using plain text, no markdown
- Show you remember them as an individual patient
- Recommend professional care for serious/persistent issues
- Be warm, direct, and helpful without lengthy explanations"""
    
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
        medical_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            medical_data = await get_user_medical_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
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
                
                print(f"\n=== SAVING QUICK SCAN ===")
                print(f"Scan ID: {scan_id}")
                print(f"User ID: '{request.user_id}' (type: {type(request.user_id)})")
                print(f"User ID repr: {repr(request.user_id)}")
                print(f"Body part: {request.body_part}")
                
                supabase.table("quick_scans").insert(scan_data).execute()
                print("Quick scan saved successfully!")
                print("=== END SAVE ===\n")
                
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
        medical_data = {}
        llm_context = ""
        
        if request.user_id:
            user_data = await get_user_data(request.user_id)
            medical_data = await get_user_medical_data(request.user_id)
            llm_context = await get_llm_context_biz(request.user_id)
        
        # Prepare data for prompt
        prompt_data = {
            "body_part": request.body_part,
            "form_data": request.form_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
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
            "questions": [],  # PostgreSQL array, not dict
            "current_step": 1,
            "internal_state": question_data.get("internal_analysis", {}),
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Always save session to database (for both authenticated and anonymous users)
        try:
            insert_response = supabase.table("deep_dive_sessions").insert(session_data).execute()
            print(f"Deep dive session saved: {session_id}")
            print(f"Insert response: {insert_response.data if insert_response.data else 'No data returned'}")
        except Exception as db_error:
            print(f"ERROR saving deep dive session: {db_error}")
            print(f"Session data attempted: {session_data}")
            # Return error instead of continuing
            return {
                "error": f"Failed to save session: {str(db_error)}",
                "status": "error"
            }
        
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
        print(f"\n=== DEEP DIVE CONTINUE ===")
        print(f"Looking for session: {request.session_id}")
        
        # Get session from database
        session_response = supabase.table("deep_dive_sessions").select("*").eq("id", request.session_id).execute()
        print(f"Session query response: {len(session_response.data) if session_response.data else 0} records found")
        
        if not session_response.data:
            print(f"ERROR: No session found with ID {request.session_id}")
            # Try to list recent sessions for debugging
            recent = supabase.table("deep_dive_sessions").select("id, created_at").order("created_at", desc=True).limit(5).execute()
            print(f"Recent sessions: {recent.data if recent.data else 'None'}")
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
        
        # Fetch medical data if user_id exists
        medical_data = {}
        if session.get("user_id"):
            medical_data = await get_user_medical_data(session["user_id"])
        
        # Get user context
        llm_context = ""
        if session.get("user_id"):
            llm_context = await get_llm_context_biz(session["user_id"])
        
        # Generate continue prompt with medical data
        prompt_data = {
            "session_data": session_data,
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
        }
        
        system_prompt = make_prompt(
            query=request.answer,
            user_data=prompt_data,
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
        
        # Fetch medical data if user_id exists
        medical_data = {}
        if session.get("user_id"):
            medical_data = await get_user_medical_data(session["user_id"])
        
        # Generate final analysis
        session_data = {
            "questions": questions,
            "form_data": session.get("form_data", {}),
            "internal_state": session.get("internal_state", {}),
            "medical_data": medical_data if medical_data and "error" not in medical_data else None
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

@app.post("/api/health-story")
async def generate_health_story(request: HealthStoryRequest):
    """Generate weekly health story analysis"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    print(f"Health story request received for user_id: '{request.user_id}'")
    print(f"User ID type: {type(request.user_id)}, length: {len(request.user_id)}")
    
    try:
        # Gather all relevant data
        health_data = await get_health_story_data(request.user_id, request.date_range)
        
        # Count tokens and prepare context
        total_tokens = 0
        context_parts = []
        
        # Add medical profile if available
        if health_data["medical_profile"]:
            profile_text = f"Medical Profile: {json.dumps(health_data['medical_profile'], indent=2)}"
            context_parts.append(profile_text)
            total_tokens += count_tokens(profile_text)
        
        # Add recent oracle chats (limit to most relevant)
        if health_data["oracle_chats"]:
            recent_chats = health_data["oracle_chats"][-10:]  # Last 10 messages
            chat_text = "Recent Oracle Conversations:\n"
            for msg in recent_chats:
                chat_text += f"- {msg.get('created_at', '')}: {msg.get('content', '')[:200]}...\n"
            context_parts.append(chat_text)
            total_tokens += count_tokens(chat_text)
        
        # Add quick scans with detailed information
        if health_data["quick_scans"]:
            print(f"Adding {len(health_data['quick_scans'])} quick scans to health story context")
            scan_text = "Recent Quick Scans:\n"
            for scan in health_data["quick_scans"]:
                # Get the analysis result - it's stored directly in the scan
                analysis = scan.get('analysis_result', {})
                form_data = scan.get('form_data', {})
                
                # Format the date more nicely
                created_at = scan.get('created_at', '')
                if created_at:
                    try:
                        date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_date = created_at[:10]
                else:
                    formatted_date = 'Unknown date'
                
                scan_text += f"\n- {formatted_date}: {scan.get('body_part', 'Unknown body part')} scan\n"
                
                # Add user-reported symptoms from form data
                if form_data.get('symptoms'):
                    scan_text += f"  Reported Symptoms: {form_data.get('symptoms')}\n"
                if form_data.get('painLevel'):
                    scan_text += f"  Pain Level: {form_data.get('painLevel')}/10\n"
                if form_data.get('duration'):
                    scan_text += f"  Duration: {form_data.get('duration')}\n"
                
                # Add analysis results
                scan_text += f"  Primary Condition: {analysis.get('primaryCondition', 'Unknown')}\n"
                scan_text += f"  Likelihood: {analysis.get('likelihood', 'Unknown')}\n"
                scan_text += f"  Confidence: {analysis.get('confidence', scan.get('confidence_score', 0))}%\n"
                scan_text += f"  Urgency: {analysis.get('urgency', scan.get('urgency_level', 'unknown'))}\n"
                
                # Add symptoms identified by AI
                symptoms = analysis.get('symptoms', [])
                if symptoms and isinstance(symptoms, list):
                    scan_text += f"  Identified Symptoms: {', '.join(str(s) for s in symptoms[:5])}\n"
                
                # Add key recommendations
                recommendations = analysis.get('recommendations', [])
                if recommendations and isinstance(recommendations, list):
                    scan_text += f"  Key Recommendations: {', '.join(str(r) for r in recommendations[:3])}\n"
                
                # Add self-care if available
                self_care = analysis.get('selfCare', [])
                if self_care and isinstance(self_care, list) and len(self_care) > 0:
                    scan_text += f"  Self-Care Tips: {str(self_care[0])}\n"
                
                # Add red flags if any
                red_flags = analysis.get('redFlags', [])
                if red_flags and isinstance(red_flags, list) and len(red_flags) > 0:
                    scan_text += f"  Warning Signs: {str(red_flags[0])}\n"
                
            context_parts.append(scan_text)
            total_tokens += count_tokens(scan_text)
        else:
            print("No quick scans found for health story")
            # Explicitly add a note about no quick scans
            no_scans_text = "Recent Quick Scans: No quick scans recorded during this period.\n"
            context_parts.append(no_scans_text)
            total_tokens += count_tokens(no_scans_text)
        
        # Add deep dive summaries
        if health_data["deep_dives"]:
            dive_text = "Deep Dive Analyses:\n"
            for dive in health_data["deep_dives"]:
                if dive.get("status") == "completed" and dive.get("final_analysis"):
                    dive_text += f"- {dive.get('created_at', '')}: {dive.get('body_part', '')} - "
                    dive_text += f"{dive.get('final_analysis', {}).get('primaryCondition', 'Analysis completed')}\n"
            context_parts.append(dive_text)
            total_tokens += count_tokens(dive_text)
        
        # Add symptom tracking
        if health_data["symptom_tracking"]:
            symptom_text = "Symptom Tracking:\n"
            for entry in health_data["symptom_tracking"]:
                symptom_text += f"- {entry.get('date', '')}: "
                symptoms = entry.get('symptoms', [])
                if symptoms:
                    symptom_text += f"{', '.join(symptoms[:3])}\n"
            context_parts.append(symptom_text)
            total_tokens += count_tokens(symptom_text)
        
        # If context is too large, summarize it
        if total_tokens > 10000:
            # Use LLM to summarize the context
            summary_response = await call_llm(
                messages=[
                    {"role": "system", "content": "Summarize the following health data concisely, focusing on key patterns and changes:"},
                    {"role": "user", "content": "\n".join(context_parts)}
                ],
                model="deepseek/deepseek-chat",
                user_id=request.user_id,
                temperature=0.3,
                max_tokens=1024
            )
            context = summary_response.get("content", "\n".join(context_parts[:2]))
        else:
            context = "\n\n".join(context_parts)
        
        # Generate health story
        system_prompt = """You are analyzing health patterns and trends from user data to create a narrative health story.

        Write 2-3 paragraphs in a flowing, narrative style that:
        - Identifies patterns and correlations in the health data
        - Uses specific percentages and metrics when available
        - Connects symptoms to lifestyle factors
        - Highlights improvements and positive changes
        - Acknowledges ongoing concerns without alarm
        - Focuses on trends over time

        Style Guidelines:
        - Write in second person ("Your health journey...")
        - Use natural, flowing language without technical jargon
        - Avoid mentioning specific tools, scans, or app features
        - Present insights as observations about their health patterns
        - Include specific metrics (percentages, timeframes, correlations)
        - Connect different health aspects (sleep, pain, exercise, etc.)

        Do NOT:
        - Mention "quick scan", "deep dive", "oracle", or any app features
        - Use medical terminology without explanation
        - Give direct medical advice
        - Use alarmist language
        - Reference the data sources directly
        
        Transform the data into insights like:
        - "Your morning headaches show a pattern..."
        - "The chest discomfort you've been experiencing..."
        - "Your sleep quality has improved by X%..."
        - "Pain levels tend to spike when..."
        
        Example style:
        Your health journey continues to show positive momentum. This week has been marked by significant improvements in your sleep quality, with an average increase of 23% in deep sleep phases compared to last week. This improvement correlates strongly with the reduction in evening screen time you've implemented.

        The persistent morning headaches you've been experiencing appear to be linked to a combination of factors: dehydration, elevated stress levels on weekdays, and potentially your sleeping position. The pattern analysis shows that headaches are 78% more likely on days following less than 6 hours of sleep.

        Your body's response to the new exercise routine has been overwhelmingly positive. Heart rate variability has improved by 15%, and your resting heart rate has decreased by 4 bpm over the past month. These are strong indicators of improving cardiovascular health."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Based on the following health data from the past week, generate a health story:\n\n{context}"}
        ]
        
        # Call LLM
        llm_response = await call_llm(
            messages=messages,
            model="deepseek/deepseek-chat",  # Using quickscan model as requested
            user_id=request.user_id,
            temperature=0.7,
            max_tokens=1024
        )
        
        story_text = llm_response.get("content", "Unable to generate health story at this time.")
        
        # Generate response
        story_id = str(uuid.uuid4())
        generated_date = datetime.now(timezone.utc)
        
        # Save to database (create health_stories table if needed)
        try:
            story_data = {
                "id": story_id,
                "user_id": request.user_id,
                "header": "Current Analysis",
                "story_text": story_text,
                "generated_date": generated_date.isoformat(),
                "date_range": request.date_range,
                "data_sources": {
                    "oracle_chats": len(health_data["oracle_chats"]),
                    "quick_scans": len(health_data["quick_scans"]),
                    "deep_dives": len(health_data["deep_dives"]),
                    "symptom_entries": len(health_data["symptom_tracking"])
                },
                "created_at": generated_date.isoformat()
            }
            
            # Attempt to save to health_stories table
            supabase.table("health_stories").insert(story_data).execute()
        except Exception as db_error:
            print(f"Database save error (non-critical): {db_error}")
        
        return {
            "success": True,
            "health_story": {
                "header": "Current Analysis",
                "story_text": story_text,
                "generated_date": generated_date.strftime("%B %d, %Y • AI-generated analysis"),
                "story_id": story_id
            }
        }
        
    except Exception as e:
        print(f"Error generating health story: {e}")
        return {
            "success": False,
            "error": "Failed to generate health story",
            "message": str(e)
        }

# Report Generation Endpoints
@app.post("/api/report/analyze")
async def analyze_report_type(request: ReportAnalyzeRequest):
    """Determine which report type and endpoint to use"""
    try:
        # Determine report type
        if has_emergency_indicators(request):
            endpoint = "/api/report/urgent-triage"
            report_type = "urgent_triage"
        elif request.context.get("purpose") == "annual_checkup":
            endpoint = "/api/report/annual-summary"
            report_type = "annual_summary"
        elif request.available_data and len(request.available_data.get("photo_session_ids", [])) >= 3:
            endpoint = "/api/report/photo-progression"
            report_type = "photo_progression"
        elif request.context.get("symptom_focus"):
            endpoint = "/api/report/symptom-timeline"
            report_type = "symptom_timeline"
        elif request.context.get("target_audience") == "specialist":
            endpoint = "/api/report/specialist"
            report_type = "specialist_focused"
        else:
            endpoint = "/api/report/comprehensive"
            report_type = "comprehensive"
        
        # Determine time range
        time_range = determine_time_range(request.context, report_type)
        
        # Gather available data sources
        data_sources = {}
        if request.user_id:
            # Get recent scans and dives
            scan_response = supabase.table("quick_scans")\
                .select("id")\
                .eq("user_id", str(request.user_id))\
                .gte("created_at", time_range["start"])\
                .lte("created_at", time_range["end"])\
                .execute()
            data_sources["quick_scans"] = [s["id"] for s in (scan_response.data or [])]
            
            dive_response = supabase.table("deep_dive_sessions")\
                .select("id")\
                .eq("user_id", str(request.user_id))\
                .eq("status", "completed")\
                .gte("created_at", time_range["start"])\
                .lte("created_at", time_range["end"])\
                .execute()
            data_sources["deep_dives"] = [d["id"] for d in (dive_response.data or [])]
        
        # Build report config
        report_config = {
            "time_range": time_range,
            "primary_focus": request.context.get("symptom_focus", "general health"),
            "include_sections": ["executive_summary", "patient_story", "medical_analysis", "action_plan"],
            "data_sources": data_sources,
            "urgency_level": "emergency" if report_type == "urgent_triage" else "routine"
        }
        
        # Save analysis
        analysis_id = str(uuid.uuid4())
        analysis_data = {
            "id": analysis_id,
            "user_id": request.user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "purpose": request.context.get("purpose"),
            "symptom_focus": request.context.get("symptom_focus"),
            "time_range": time_range,
            "recommended_type": report_type,
            "confidence": 0.85,
            "report_config": report_config,
            "data_sources": data_sources
        }
        
        supabase.table("report_analyses").insert(analysis_data).execute()
        
        # Generate reasoning
        reasoning = f"Based on {'emergency indicators' if report_type == 'urgent_triage' else 'available data and context'}, "
        reasoning += f"a {report_type.replace('_', ' ')} report is recommended."
        
        return {
            "recommended_endpoint": endpoint,
            "recommended_type": report_type,
            "reasoning": reasoning,
            "confidence": 0.85,
            "report_config": report_config,
            "analysis_id": analysis_id,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error in report analysis: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/comprehensive")
async def generate_comprehensive_report(request: ComprehensiveReportRequest):
    """Generate comprehensive medical report"""
    try:
        # Load analysis
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Gather all data
        data = await gather_report_data(request.user_id or analysis["user_id"], config)
        
        # Build context for LLM
        context = f"""Generate a comprehensive medical report based on the following data:

Time Range: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}
Primary Focus: {config.get('primary_focus', 'general health')}

Quick Scans ({len(data['quick_scans'])}):
{json.dumps([{
    'date': s['created_at'][:10],
    'body_part': s['body_part'],
    'primary_condition': s.get('analysis_result', {}).get('primaryCondition'),
    'confidence': s.get('confidence_score')
} for s in data['quick_scans']], indent=2)}

Deep Dives ({len(data['deep_dives'])}):
{json.dumps([{
    'date': d['created_at'][:10],
    'body_part': d['body_part'],
    'questions_asked': len(d.get('questions', [])),
    'final_analysis': d.get('final_analysis', {}).get('primaryCondition')
} for d in data['deep_dives']], indent=2)}

Symptom Tracking:
{json.dumps([{
    'date': s['created_at'][:10],
    'symptom': s['symptom_name'],
    'severity': s['severity'],
    'related_context': s.get('enriched_context')
} for s in data['symptom_tracking']], indent=2)}"""

        # Generate report using LLM
        system_prompt = """You are generating a comprehensive medical report. Structure your response as valid JSON matching this format:
{
  "executive_summary": {
    "one_page_summary": "Complete 1-page overview of all health data and findings",
    "chief_complaints": ["list of main health concerns"],
    "key_findings": ["important discoveries from the data"],
    "urgency_indicators": ["any concerning findings"],
    "action_items": ["recommended next steps"]
  },
  "patient_story": {
    "symptoms_timeline": [
      {
        "date": "ISO date",
        "symptom": "symptom name",
        "severity": 1-10,
        "patient_description": "how patient described it"
      }
    ],
    "pain_patterns": {
      "locations": ["affected areas"],
      "triggers": ["what makes it worse"],
      "relievers": ["what helps"],
      "progression": "how symptoms have changed over time"
    }
  },
  "medical_analysis": {
    "conditions_assessed": [
      {
        "condition": "Medical Name (common name)",
        "likelihood": "Very likely/Likely/Possible",
        "supporting_evidence": ["evidence points"],
        "from_sessions": ["scan/dive IDs that suggested this"]
      }
    ],
    "symptom_correlations": ["patterns noticed between symptoms"],
    "risk_factors": ["identified risk factors"]
  },
  "action_plan": {
    "immediate_actions": ["urgent steps if any"],
    "diagnostic_tests": ["recommended tests"],
    "lifestyle_changes": ["suggested changes"],
    "monitoring_plan": ["what to track"],
    "follow_up_timeline": "when to seek care"
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",  # Best model for comprehensive analysis
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=3000
        )
        
        # Parse response
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            # Fallback structure
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Unable to generate full report. Please try again.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Add metadata
        report_data["metadata"] = {
            "sessions_included": len(data["quick_scans"]) + len(data["deep_dives"]),
            "date_range": f"{config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}",
            "confidence_score": 85,
            "generated_by_model": "tngtech/deepseek-r1t-chimera:free"
        }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "comprehensive",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 85,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "data_sources": config.get("data_sources", {}),
            "time_range": config.get("time_range", {})
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "comprehensive",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating comprehensive report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/urgent-triage")
async def generate_urgent_triage(request: UrgentTriageRequest):
    """Generate 1-page urgent triage report"""
    try:
        # Load analysis
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Gather recent data (last 7 days for urgent)
        recent_range = {
            "start": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        }
        config["time_range"] = recent_range
        
        data = await gather_report_data(request.user_id or analysis["user_id"], config)
        
        # Focus on most recent and severe symptoms
        urgent_context = f"""Generate a 1-page URGENT medical summary for immediate medical attention.

RECENT SYMPTOMS (Last 7 days):
{json.dumps([{
    'date': s['created_at'],
    'symptom': s['symptom_name'],
    'severity': s['severity'],
    'body_part': s.get('body_part')
} for s in sorted(data['symptom_tracking'], key=lambda x: x['severity'], reverse=True)[:5]], indent=2)}

MOST RECENT ASSESSMENTS:
{json.dumps([{
    'date': s['created_at'],
    'condition': s.get('analysis_result', {}).get('primaryCondition'),
    'urgency': s.get('urgency_level'),
    'red_flags': s.get('analysis_result', {}).get('redFlags', [])
} for s in data['quick_scans'][:3]], indent=2)}"""

        system_prompt = """Generate a 1-page emergency triage summary. Return JSON:
{
  "immediate_concerns": ["most urgent symptoms/conditions"],
  "vital_symptoms": [
    {
      "symptom": "symptom name",
      "severity": "mild/moderate/severe",
      "duration": "how long",
      "red_flags": ["concerning aspects"]
    }
  ],
  "recommended_action": "Call 911" or "ER Now" or "Urgent Care Today",
  "what_to_tell_doctor": ["key points for ER staff"],
  "recent_progression": "how symptoms changed in last 24-48 hours"
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": urgent_context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.2,  # Lower temp for urgent accuracy
            max_tokens=1000
        )
        
        triage_summary = extract_json_from_response(llm_response.get("content", ""))
        
        if not triage_summary:
            triage_summary = {
                "immediate_concerns": ["Unable to analyze - seek immediate medical attention"],
                "recommended_action": "ER Now"
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "urgent_triage",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": {"triage_summary": triage_summary},
            "executive_summary": f"URGENT: {triage_summary.get('recommended_action', 'Seek immediate care')}",
            "confidence_score": 90,
            "model_used": "tngtech/deepseek-r1t-chimera:free"
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "urgent_triage",
            "triage_summary": triage_summary,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating urgent triage: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/symptom-timeline")
async def generate_symptom_timeline(request: SymptomTimelineRequest):
    """Generate symptom timeline report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Gather data with focus on timeline
        data = await gather_report_data(request.user_id or analysis["user_id"], config)
        
        # Build timeline context
        context = f"""Generate a symptom timeline report focused on: {request.symptom_focus or config.get('primary_focus', 'symptoms')}

Time Range: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}

Symptom Data:
{json.dumps([{
    'date': s['created_at'][:10],
    'symptom': s.get('symptom_name', 'Unknown'),
    'severity': s.get('severity', 0),
    'body_part': s.get('body_part')
} for s in data['symptom_tracking']], indent=2)}

Quick Scans:
{json.dumps([{
    'date': s['created_at'][:10],
    'body_part': s['body_part'],
    'condition': s.get('analysis_result', {}).get('primaryCondition'),
    'severity': s.get('analysis_result', {}).get('painLevel', 0)
} for s in data['quick_scans']], indent=2)}"""

        system_prompt = """Generate a symptom timeline report. Return JSON:
{
  "executive_summary": {
    "one_page_summary": "Timeline overview",
    "chief_complaints": ["main symptoms"],
    "key_findings": ["patterns discovered"]
  },
  "symptom_progression": {
    "primary_symptom": "main symptom tracked",
    "timeline": [
      {
        "date": "YYYY-MM-DD",
        "severity": 1-10,
        "description": "symptom description",
        "triggers_identified": ["potential triggers"],
        "treatments_tried": ["treatments used"],
        "effectiveness": "treatment response"
      }
    ],
    "patterns_identified": {
      "frequency": "how often symptoms occur",
      "peak_times": ["when symptoms are worst"],
      "seasonal_trends": "seasonal patterns",
      "correlation_factors": ["correlated factors"]
    }
  },
  "trend_analysis": {
    "overall_direction": "improving/worsening/stable",
    "severity_trend": "severity changes over time",
    "frequency_trend": "frequency changes",
    "response_to_treatment": "treatment effectiveness"
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=2000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Symptom timeline analysis could not be completed.",
                    "chief_complaints": [],
                    "key_findings": []
                },
                "symptom_progression": {
                    "primary_symptom": request.symptom_focus or "Unknown",
                    "timeline": [],
                    "patterns_identified": {}
                },
                "trend_analysis": {}
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "symptom_timeline",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 80,
            "model_used": "tngtech/deepseek-r1t-chimera:free"
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "symptom_timeline",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating symptom timeline: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/photo-progression")
async def generate_photo_progression(request: PhotoProgressionRequest):
    """Generate photo progression report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Get photo session data (placeholder - would need actual photo table)
        photo_sessions = []
        
        # Build context for photo analysis
        context = f"""Generate a photo progression report.

Time Range: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}

Photo Sessions Available: {len(photo_sessions)}

Note: This is a preliminary photo progression report. Full implementation requires photo analysis capabilities."""

        system_prompt = """Generate a photo progression report. Return JSON:
{
  "executive_summary": {
    "one_page_summary": "Photo progression overview",
    "key_findings": ["visual changes noted"]
  },
  "visual_analysis": {
    "photos_analyzed": [
      {
        "photo_id": "session-id",
        "date": "YYYY-MM-DD",
        "ai_description": "what the AI sees",
        "size_measurement": "estimated size",
        "color_changes": ["color observations"],
        "concerning_features": ["concerning aspects"]
      }
    ],
    "progression_summary": {
      "overall_change": "improvement/worsening/stable",
      "size_change": "size changes over time",
      "color_evolution": "color changes",
      "texture_changes": "texture observations",
      "border_changes": "border changes"
    },
    "ai_recommendations": {
      "urgency_level": "low/medium/high",
      "specific_concerns": ["specific concerns"],
      "recommended_timeline": "when to follow up",
      "what_to_monitor": ["monitoring points"]
    }
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=1500
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Photo progression analysis requires visual data that is not currently available.",
                    "key_findings": ["Photo analysis capabilities pending implementation"]
                },
                "visual_analysis": {
                    "photos_analyzed": [],
                    "progression_summary": {
                        "overall_change": "Unable to assess without photos"
                    },
                    "ai_recommendations": {
                        "urgency_level": "medium",
                        "recommended_timeline": "Consult healthcare provider for visual assessment"
                    }
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "photo_progression",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 60,
            "model_used": "tngtech/deepseek-r1t-chimera:free"
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "photo_progression",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating photo progression: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/specialist")
async def generate_specialist_report(request: SpecialistReportRequest):
    """Generate specialist-focused report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        config = analysis.get("report_config", {})
        
        # Gather all data
        data = await gather_report_data(request.user_id or analysis["user_id"], config)
        
        # Build specialist context
        specialty = request.specialty or "specialist"
        context = f"""Generate a {specialty} referral report.

Time Range: {config['time_range']['start'][:10]} to {config['time_range']['end'][:10]}
Specialty Focus: {specialty}
Primary Concern: {config.get('primary_focus', 'general health')}

Clinical Data:
{json.dumps([{
    'date': s['created_at'][:10],
    'assessment': s.get('analysis_result', {}).get('primaryCondition'),
    'confidence': s.get('confidence_score'),
    'red_flags': s.get('analysis_result', {}).get('redFlags', [])
} for s in data['quick_scans']], indent=2)}

Symptom History:
{json.dumps([{
    'date': s['created_at'][:10],
    'symptom': s.get('symptom_name'),
    'severity': s.get('severity')
} for s in data['symptom_tracking']], indent=2)}"""

        system_prompt = f"""Generate a specialist referral report for {specialty}. Return JSON:
{{
  "executive_summary": {{
    "one_page_summary": "Clinical summary for specialist",
    "chief_complaints": ["primary concerns"],
    "key_findings": ["clinically relevant findings"],
    "referral_reason": "why specialist consultation needed"
  }},
  "clinical_presentation": {{
    "presenting_symptoms": ["current symptoms"],
    "symptom_duration": "timeline of symptoms",
    "progression": "how symptoms have changed",
    "previous_treatments": ["treatments tried"],
    "response_to_treatment": "treatment responses"
  }},
  "specialist_focus": {{
    "relevant_findings": ["findings relevant to {specialty}"],
    "diagnostic_considerations": ["differential diagnoses"],
    "specific_questions": ["questions for specialist"],
    "urgency_assessment": "routine/urgent/emergent"
  }},
  "recommendations": {{
    "suggested_workup": ["recommended tests/procedures"],
    "clinical_questions": ["specific questions to address"],
    "timing": "recommended timeframe for consultation"
  }}
}}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=2000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": f"Specialist referral report for {specialty} consultation.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "referral_reason": "Clinical evaluation needed"
                },
                "clinical_presentation": {},
                "specialist_focus": {},
                "recommendations": {
                    "timing": "Within 2-4 weeks"
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "specialist_focused",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 85,
            "model_used": "tngtech/deepseek-r1t-chimera:free"
        }
        
        # Add specialty field for future use
        report_record["specialty"] = specialty
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "specialist_focused",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "specialty": specialty,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating specialist report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/annual-summary")
async def generate_annual_summary(request: AnnualSummaryRequest):
    """Generate annual summary report"""
    try:
        analysis_response = supabase.table("report_analyses")\
            .select("*")\
            .eq("id", request.analysis_id)\
            .execute()
        
        if not analysis_response.data:
            return {"error": "Analysis not found", "status": "error"}
        
        analysis = analysis_response.data[0]
        
        # Override config for annual scope
        year = request.year or datetime.now().year
        annual_range = {
            "start": f"{year}-01-01T00:00:00Z",
            "end": f"{year}-12-31T23:59:59Z"
        }
        
        config = {
            "time_range": annual_range,
            "data_sources": {"quick_scans": [], "deep_dives": []}
        }
        
        # Get all data for the year
        scan_response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        dive_response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .eq("status", "completed")\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        symptom_response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(request.user_id))\
            .gte("created_at", annual_range["start"])\
            .lte("created_at", annual_range["end"])\
            .execute()
        
        quick_scans = scan_response.data or []
        deep_dives = dive_response.data or []
        symptoms = symptom_response.data or []
        
        # Build annual context
        context = f"""Generate an annual health summary for {year}.

Annual Statistics:
- Total Quick Scans: {len(quick_scans)}
- Total Deep Dives: {len(deep_dives)}
- Symptom Entries: {len(symptoms)}

Conditions Assessed:
{json.dumps([s.get('analysis_result', {}).get('primaryCondition') for s in quick_scans if s.get('analysis_result', {}).get('primaryCondition')], indent=2)}

Symptom Frequency:
{json.dumps({}, indent=2)}

Seasonal Patterns: {len([s for s in symptoms if '01' in s.get('created_at', '')[:7] or '02' in s.get('created_at', '')[:7] or '12' in s.get('created_at', '')[:7]])} winter entries, {len([s for s in symptoms if '06' in s.get('created_at', '')[:7] or '07' in s.get('created_at', '')[:7] or '08' in s.get('created_at', '')[:7]])} summer entries"""

        system_prompt = """Generate an annual health summary. Return JSON:
{
  "executive_summary": {
    "one_page_summary": "Complete year overview",
    "key_findings": ["major health insights"],
    "action_items": ["recommendations for next year"]
  },
  "yearly_overview": {
    "total_assessments": 0,
    "most_common_concerns": ["top health issues"],
    "health_trends": {
      "improving_areas": ["areas of improvement"],
      "concerning_trends": ["areas needing attention"],
      "stable_conditions": ["stable health aspects"]
    },
    "seasonal_patterns": {
      "winter_issues": ["winter health patterns"],
      "summer_concerns": ["summer health patterns"],
      "year_round_stable": ["consistent health aspects"]
    }
  },
  "health_metrics": {
    "symptom_frequency": {},
    "severity_averages": {},
    "improvement_tracking": {
      "symptoms_resolved": ["resolved issues"],
      "new_symptoms": ["new health concerns"],
      "chronic_patterns": ["ongoing health patterns"]
    }
  },
  "preventive_recommendations": {
    "screening_due": ["recommended screenings"],
    "lifestyle_goals": ["health goals for next year"],
    "monitoring_priorities": ["key areas to monitor"],
    "specialist_referrals": ["specialist consultations needed"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=2500
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": f"Annual health summary for {year} could not be generated.",
                    "key_findings": [],
                    "action_items": ["Schedule annual physical exam"]
                },
                "yearly_overview": {
                    "total_assessments": len(quick_scans) + len(deep_dives),
                    "most_common_concerns": [],
                    "health_trends": {},
                    "seasonal_patterns": {}
                },
                "health_metrics": {},
                "preventive_recommendations": {}
            }
        
        # Update total assessments
        if "yearly_overview" in report_data:
            report_data["yearly_overview"]["total_assessments"] = len(quick_scans) + len(deep_dives)
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "analysis_id": request.analysis_id,
            "report_type": "annual_summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 88,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "year": year
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "annual_summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "year": year,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating annual summary: {e}")
        return {"error": str(e), "status": "error"}

# ================== SPECIALIST REPORT ENDPOINTS ==================

@app.post("/api/report/cardiology")
async def generate_cardiology_report(request: SpecialistReportRequest):
    """Generate cardiology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract cardiac-specific patterns
        cardiac_data = await extract_cardiac_patterns(all_data)
        
        # Build cardiology context
        context = f"""Generate a comprehensive cardiology report.

CARDIAC DATA:
{cardiac_data}

VITAL SIGNS AND METRICS:
- Latest recorded blood pressure: [To be integrated with wearables]
- Heart rate patterns: [To be integrated]
- Exercise tolerance: Based on reported symptoms

SYMPTOMS OF INTEREST:
- Chest pain/pressure/discomfort
- Palpitations or irregular heartbeat
- Shortness of breath
- Dizziness or lightheadedness
- Fatigue with exertion
- Swelling in legs/ankles

RISK FACTORS:
[Analyze from patient data for diabetes, hypertension, smoking, family history]

PATIENT PROFILE:
{json.dumps(analysis.get("user_data", {}), indent=2)}"""

        system_prompt = """Generate a cardiology specialist report. Include both general medical sections AND cardiology-specific analysis.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Complete cardiovascular assessment summary",
    "chief_complaints": ["primary cardiac concerns"],
    "key_findings": ["significant cardiovascular findings"],
    "urgency_indicators": ["any concerning cardiac symptoms"],
    "action_items": ["immediate cardiac care needs"]
  },
  "patient_story": {
    "cardiac_symptoms_timeline": [
      {
        "date": "ISO date",
        "symptom": "chest pain/palpitations/etc",
        "severity": 1-10,
        "triggers": ["exertion", "stress", "rest"],
        "duration": "minutes/hours",
        "relief_factors": ["rest", "medication"]
      }
    ],
    "cardiac_risk_factors": {
      "modifiable": ["smoking", "diet", "exercise"],
      "non_modifiable": ["age", "family history", "gender"],
      "comorbidities": ["diabetes", "hypertension", "obesity"]
    }
  },
  "medical_analysis": {
    "cardiac_assessment": {
      "rhythm_concerns": ["arrhythmia patterns if any"],
      "ischemic_symptoms": ["chest pain characteristics"],
      "heart_failure_signs": ["dyspnea", "edema", "fatigue"],
      "vascular_symptoms": ["claudication", "cold extremities"]
    },
    "differential_diagnosis": [
      {
        "condition": "Condition name",
        "icd10_code": "IXX.X",
        "likelihood": "High/Medium/Low",
        "supporting_evidence": ["evidence points"]
      }
    ],
    "pattern_analysis": {
      "symptom_triggers": ["identified triggers"],
      "temporal_patterns": ["when symptoms occur"],
      "progression": "stable/worsening/improving"
    }
  },
  "cardiology_specific": {
    "recommended_tests": {
      "immediate": ["ECG", "Troponin if chest pain"],
      "routine": ["Echo", "Stress test", "Holter monitor"],
      "advanced": ["Cardiac MRI", "Coronary angiography if indicated"]
    },
    "risk_stratification": {
      "ascvd_risk": "Calculate if data available",
      "heart_failure_risk": "Low/Medium/High",
      "arrhythmia_risk": "Low/Medium/High"
    },
    "medication_considerations": {
      "indicated": ["Aspirin", "Statin", "Beta-blocker", "ACE-I/ARB"],
      "contraindicated": ["based on symptoms"],
      "monitoring_required": ["lab work needed"]
    }
  },
  "action_plan": {
    "immediate_actions": ["911 if acute symptoms", "urgent cardiology if concerning"],
    "diagnostic_pathway": {
      "week_1": ["Initial tests"],
      "week_2_4": ["Follow-up tests"],
      "ongoing": ["Monitoring plan"]
    },
    "lifestyle_modifications": {
      "diet": ["DASH diet", "sodium restriction"],
      "exercise": ["cardiac rehab if indicated", "activity recommendations"],
      "risk_reduction": ["smoking cessation", "weight management"]
    },
    "follow_up": {
      "cardiology_appointment": "Urgent/Routine/As needed",
      "primary_care": "Frequency of monitoring",
      "red_flags": ["When to seek immediate care"]
    }
  },
  "billing_optimization": {
    "suggested_codes": {
      "icd10": ["Primary and secondary diagnosis codes"],
      "cpt": ["Recommended procedure codes for workup"]
    },
    "insurance_considerations": ["Prior auth needs", "covered services"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Cardiology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                },
                "error": "Failed to generate complete report"
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "cardiology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "cardiology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating cardiology report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/neurology")
async def generate_neurology_report(request: SpecialistReportRequest):
    """Generate neurology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract neuro-specific patterns
        neuro_data = await extract_neuro_patterns(all_data)
        
        # Build neurology context
        context = f"""Generate a comprehensive neurology report.

NEUROLOGICAL DATA:
{neuro_data}

NEUROLOGICAL SYMPTOMS OF INTEREST:
- Headaches (type, frequency, triggers)
- Dizziness/vertigo
- Numbness/tingling
- Vision changes
- Memory/cognitive issues
- Seizures or blackouts
- Tremors or movement disorders
- Sleep disturbances

PATTERN ANALYSIS NEEDED:
- Headache patterns (migraine vs tension vs cluster)
- Temporal patterns
- Triggers and relief factors
- Associated symptoms
- Progression over time"""

        system_prompt = """Generate a neurology specialist report. Include both general medical sections AND neurology-specific analysis.

Return JSON format matching the cardiology structure but with neurology-specific content:
- executive_summary (with neurological focus)
- patient_story (neurological symptoms timeline)
- medical_analysis (neurological assessment)
- neurology_specific section with:
  - recommended_tests (MRI, EEG, EMG/NCS, LP if indicated)
  - headache_classification if applicable
  - cognitive_assessment if applicable
  - movement_disorder_assessment if applicable
- action_plan (neurology-focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Neurology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "neurology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "neurology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating neurology report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/psychiatry")
async def generate_psychiatry_report(request: SpecialistReportRequest):
    """Generate psychiatry specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract mental health patterns
        mental_health_data = await extract_mental_health_patterns(all_data)
        
        # Build psychiatry context
        context = f"""Generate a comprehensive psychiatry report.

MENTAL HEALTH DATA:
{mental_health_data}

PSYCHIATRIC SYMPTOMS OF INTEREST:
- Mood symptoms (depression, mania, mood swings)
- Anxiety symptoms (panic, worry, phobias)
- Sleep disturbances
- Appetite/weight changes
- Concentration/memory issues
- Social functioning
- Substance use
- Suicidal/homicidal ideation

FUNCTIONAL ASSESSMENT:
- Work/school performance
- Relationships
- Daily activities
- Self-care"""

        system_prompt = """Generate a psychiatry specialist report. Include both general medical sections AND psychiatry-specific analysis.

Return JSON format with:
- executive_summary (mental health focus)
- patient_story (psychiatric history and timeline)
- medical_analysis (psychiatric assessment)
- psychiatry_specific section with:
  - mental_status_exam components
  - risk_assessment (suicide, violence, self-harm)
  - diagnostic_impressions (DSM-5 considerations)
  - psychopharmacology_recommendations
  - therapy_recommendations
- action_plan (mental health focused)
- billing_optimization (psychiatric codes)"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Psychiatry report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "psychiatry", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "psychiatry",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating psychiatry report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/dermatology")
async def generate_dermatology_report(request: SpecialistReportRequest):
    """Generate dermatology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Gather photo data if available
        photo_data = await gather_photo_data(request.user_id or analysis["user_id"], config)
        
        # Extract dermatology patterns
        derm_data = await extract_dermatology_patterns(all_data, photo_data)
        
        # Build dermatology context
        context = f"""Generate a comprehensive dermatology report.

DERMATOLOGICAL DATA:
{derm_data}

SKIN SYMPTOMS OF INTEREST:
- Rashes (location, appearance, progression)
- Lesions/moles (ABCDE criteria)
- Itching/burning/pain
- Color changes
- Texture changes
- Hair/nail changes
- Photo progression data: {len(photo_data)} images available

PATTERN ANALYSIS:
- Distribution patterns
- Symmetry
- Evolution over time
- Response to treatments
- Environmental triggers"""

        system_prompt = """Generate a dermatology specialist report. Include both general medical sections AND dermatology-specific analysis.

Return JSON format with:
- executive_summary (dermatological focus)
- patient_story (skin condition timeline)
- medical_analysis (dermatological assessment)
- dermatology_specific section with:
  - lesion_descriptions (morphology, distribution)
  - photo_analysis_summary
  - differential_diagnosis (skin conditions)
  - biopsy_recommendations if indicated
  - treatment_plan (topical, systemic, procedures)
  - sun_protection_counseling
- action_plan (dermatology focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Dermatology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "dermatology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "dermatology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating dermatology report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/gastroenterology")
async def generate_gastroenterology_report(request: SpecialistReportRequest):
    """Generate gastroenterology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract GI patterns
        gi_data = await extract_gi_patterns(all_data)
        
        # Build gastroenterology context
        context = f"""Generate a comprehensive gastroenterology report.

GASTROINTESTINAL DATA:
{gi_data}

GI SYMPTOMS OF INTEREST:
- Abdominal pain (location, quality, timing)
- Nausea/vomiting
- Diarrhea/constipation
- Bloating/gas
- Heartburn/reflux
- Blood in stool
- Weight changes
- Appetite changes

DIETARY PATTERNS:
- Food triggers
- Meal timing
- Dietary restrictions
- Symptom-food correlations"""

        system_prompt = """Generate a gastroenterology specialist report. Include both general medical sections AND GI-specific analysis.

Return JSON format with:
- executive_summary (GI focus)
- patient_story (GI symptoms timeline)
- medical_analysis (GI assessment)
- gastroenterology_specific section with:
  - symptom_patterns (relation to meals, bowel habits)
  - alarm_symptoms (bleeding, weight loss, etc)
  - recommended_tests (endoscopy, colonoscopy, imaging)
  - dietary_recommendations
  - medication_options (PPIs, antispasmodics, etc)
  - probiotic_recommendations
- action_plan (GI focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Gastroenterology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "gastroenterology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "gastroenterology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating gastroenterology report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/endocrinology")
async def generate_endocrinology_report(request: SpecialistReportRequest):
    """Generate endocrinology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract endocrine patterns
        endo_data = await extract_endocrine_patterns(all_data)
        
        # Build endocrinology context
        context = f"""Generate a comprehensive endocrinology report.

ENDOCRINE DATA:
{endo_data}

ENDOCRINE SYMPTOMS OF INTEREST:
- Fatigue/energy levels
- Weight changes
- Temperature intolerance
- Hair/skin changes
- Menstrual irregularities
- Libido changes
- Mood changes
- Excessive thirst/urination

METABOLIC INDICATORS:
- Blood sugar patterns
- Weight trends
- Energy fluctuations
- Sleep quality"""

        system_prompt = """Generate an endocrinology specialist report. Include both general medical sections AND endocrine-specific analysis.

Return JSON format with:
- executive_summary (endocrine focus)
- patient_story (metabolic/hormonal timeline)
- medical_analysis (endocrine assessment)
- endocrinology_specific section with:
  - suspected_hormonal_imbalances
  - recommended_labs (thyroid, diabetes, hormones)
  - metabolic_assessment
  - treatment_options (hormone replacement, medications)
  - lifestyle_modifications (diet, exercise, stress)
  - monitoring_plan
- action_plan (endocrine focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Endocrinology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "endocrinology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "endocrinology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating endocrinology report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/pulmonology")
async def generate_pulmonology_report(request: SpecialistReportRequest):
    """Generate pulmonology specialist report"""
    try:
        analysis = await load_analysis(request.analysis_id)
        config = analysis.get("report_config", {})
        
        # Gather comprehensive data
        all_data = await gather_comprehensive_data(request.user_id or analysis["user_id"], config)
        
        # Extract pulmonary patterns
        pulm_data = await extract_pulmonary_patterns(all_data)
        
        # Build pulmonology context
        context = f"""Generate a comprehensive pulmonology report.

PULMONARY DATA:
{pulm_data}

RESPIRATORY SYMPTOMS OF INTEREST:
- Cough (productive/dry, timing)
- Shortness of breath (at rest/exertion)
- Wheezing
- Chest tightness
- Sputum production
- Hemoptysis
- Exercise tolerance
- Sleep apnea symptoms

ENVIRONMENTAL FACTORS:
- Smoking history
- Occupational exposures
- Allergens
- Air quality"""

        system_prompt = """Generate a pulmonology specialist report. Include both general medical sections AND pulmonary-specific analysis.

Return JSON format with:
- executive_summary (pulmonary focus)
- patient_story (respiratory timeline)
- medical_analysis (pulmonary assessment)
- pulmonology_specific section with:
  - breathing_pattern_analysis
  - suspected_conditions (asthma, COPD, etc)
  - recommended_tests (PFTs, chest CT, sleep study)
  - inhaler_recommendations
  - oxygen_assessment
  - pulmonary_rehab_candidacy
  - environmental_modifications
- action_plan (pulmonary focused)
- billing_optimization"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Pulmonology report generation failed. Please retry.",
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        await save_specialist_report(report_id, request, "pulmonology", report_data)
        
        return {
            "report_id": report_id,
            "report_type": "pulmonology",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating pulmonology report: {e}")
        return {"error": str(e), "status": "error"}

# ================== TIME-BASED REPORT ENDPOINTS ==================

@app.post("/api/report/30-day")
async def generate_30_day_report(request: TimePeriodReportRequest):
    """Generate 30-day aggregate health report"""
    try:
        # Set up 30-day time range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=30)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data for the period
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Group data by week
        weekly_data = {}
        for i in range(4):
            week_start = start_date + timedelta(days=i*7)
            week_end = week_start + timedelta(days=7)
            week_key = f"Week {i+1}"
            weekly_data[week_key] = {
                "quick_scans": 0,
                "deep_dives": 0,
                "symptoms": {},
                "severity_avg": 0,
                "notable_events": []
            }
        
        # Process data into weekly buckets
        for scan in all_data.get("quick_scans", []):
            scan_date = datetime.fromisoformat(scan["created_at"].replace('Z', '+00:00'))
            week_num = (scan_date - start_date).days // 7
            if 0 <= week_num < 4:
                week_key = f"Week {week_num + 1}"
                weekly_data[week_key]["quick_scans"] += 1
                
                # Track symptoms
                symptoms = scan.get("form_data", {}).get("symptoms", "Unknown")
                if symptoms not in weekly_data[week_key]["symptoms"]:
                    weekly_data[week_key]["symptoms"][symptoms] = 0
                weekly_data[week_key]["symptoms"][symptoms] += 1
        
        # Calculate symptom frequencies
        symptom_freq = count_symptoms_by_frequency(all_data)
        
        # Extract patterns
        patterns = []
        for scan in all_data.get("quick_scans", []):
            if scan.get("analysis_result", {}).get("primaryCondition"):
                patterns.append({
                    "date": scan["created_at"][:10],
                    "condition": scan["analysis_result"]["primaryCondition"],
                    "severity": scan.get("form_data", {}).get("painLevel", 5)
                })
        
        context = f"""Generate a 30-day comprehensive health report.

TIME PERIOD: {start_date.strftime('%B %d')} to {end_date.strftime('%B %d, %Y')}

ACTIVITY SUMMARY:
- Total Quick Scans: {len(all_data.get('quick_scans', []))}
- Total Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- LLM Chat Sessions: {len(all_data.get('llm_summaries', []))}

WEEKLY BREAKDOWN:
{json.dumps(weekly_data, indent=2)}

TOP SYMPTOMS (by frequency):
{json.dumps(symptom_freq[:10], indent=2)}

PATTERN DATA:
{json.dumps(patterns[:20], indent=2)}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a 30-day aggregate health report. This report should synthesize ALL health data from the past 30 days.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Comprehensive 30-day health overview",
    "key_findings": ["major insights from the period"],
    "patterns_identified": ["seems to pop up when patterns"],
    "action_items": ["recommendations based on patterns"]
  },
  "period_overview": {
    "total_health_interactions": 0,
    "most_active_week": "Week X",
    "primary_concerns": ["top 3-5 health issues"],
    "improvement_areas": ["symptoms that improved"],
    "worsening_areas": ["symptoms that worsened"],
    "stable_conditions": ["unchanged patterns"]
  },
  "pattern_analysis": {
    "temporal_patterns": {
      "time_of_day": ["morning symptoms", "evening symptoms"],
      "day_of_week": ["weekday vs weekend patterns"],
      "weekly_trends": ["week-over-week changes"]
    },
    "correlation_patterns": {
      "symptom_triggers": ["X seems to pop up when Y"],
      "environmental_factors": ["weather, stress, activity correlations"],
      "comorbidity_patterns": ["symptoms that occur together"]
    },
    "severity_analysis": {
      "average_severity": 0,
      "severity_trend": "improving/worsening/stable",
      "high_severity_events": ["dates and details of severe symptoms"]
    }
  },
  "detailed_findings": {
    "by_body_system": {
      "neurological": ["headaches, dizziness findings"],
      "cardiovascular": ["chest pain, palpitations findings"],
      "respiratory": ["breathing issues findings"],
      "gastrointestinal": ["digestive findings"],
      "musculoskeletal": ["pain, mobility findings"]
    },
    "by_symptom_type": {
      "pain": {"frequency": 0, "average_severity": 0, "locations": []},
      "fatigue": {"frequency": 0, "patterns": []},
      "other_symptoms": {}
    }
  },
  "predictive_insights": {
    "emerging_patterns": ["patterns that are developing"],
    "risk_indicators": ["concerning trends"],
    "preventive_opportunities": ["ways to prevent issues"]
  },
  "recommendations": {
    "immediate_actions": ["urgent items if any"],
    "lifestyle_modifications": ["based on patterns"],
    "monitoring_priorities": ["what to track closely"],
    "specialist_consultations": ["if patterns suggest need"],
    "follow_up_timeline": "suggested next steps"
  },
  "data_quality_metrics": {
    "data_completeness": "percentage of days with data",
    "consistency_score": "how consistent tracking has been",
    "areas_needing_data": ["what's missing"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=4000
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "30-day report generation failed. Please retry.",
                    "key_findings": [],
                    "patterns_identified": [],
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "30_day_summary",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 90,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "time_range": config["time_range"]
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "30_day_summary",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating 30-day report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/annual")
async def generate_annual_report(request: TimePeriodReportRequest):
    """Generate annual aggregate health report"""
    try:
        # Set up annual time range
        year = datetime.now().year
        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        config = {
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        # Gather ALL data for the year
        all_data = await gather_comprehensive_data(request.user_id, config)
        
        # Group data by month
        monthly_data = await group_data_by_month(all_data)
        
        # Calculate yearly metrics
        total_interactions = sum(m["total_interactions"] for m in monthly_data.values())
        
        # Analyze seasonal patterns
        seasonal_patterns = analyze_seasonal_patterns(all_data)
        
        # Get top conditions throughout the year
        all_conditions = []
        for scan in all_data.get("quick_scans", []):
            condition = scan.get("analysis_result", {}).get("primaryCondition")
            if condition:
                all_conditions.append(condition)
        
        # Count condition frequencies
        condition_counts = {}
        for condition in all_conditions:
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        top_conditions = sorted(condition_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        context = f"""Generate a comprehensive annual health report for {year}.

YEARLY STATISTICS:
- Total Health Interactions: {total_interactions}
- Quick Scans: {len(all_data.get('quick_scans', []))}
- Deep Dives: {len(all_data.get('deep_dives', []))}
- Symptom Tracking Entries: {len(all_data.get('symptom_tracking', []))}
- Months with Data: {len(monthly_data)}

MONTHLY BREAKDOWN:
{json.dumps(monthly_data, indent=2)}

TOP CONDITIONS (by frequency):
{json.dumps(top_conditions, indent=2)}

SEASONAL PATTERNS:
{json.dumps(seasonal_patterns, indent=2)}

TRACKING DATA:
{json.dumps([{"metric": t["metric"], "points": len(t["data_points"])} for t in all_data.get("tracking_data", [])], indent=2)}

WEARABLES DATA: {json.dumps(all_data.get('wearables', {}), indent=2) if request.include_wearables else 'Not included'}"""

        system_prompt = """Generate a comprehensive annual health report. This report should provide deep insights into health patterns over the entire year.

Return JSON format:
{
  "executive_summary": {
    "one_page_summary": "Complete year in health overview",
    "key_findings": ["major health insights from the year"],
    "health_journey": "narrative of health changes through the year",
    "action_items": ["priorities for next year"]
  },
  "yearly_metrics": {
    "total_health_interactions": 0,
    "engagement_score": "high/medium/low based on consistency",
    "most_active_months": ["top 3 months"],
    "health_complexity_score": "simple/moderate/complex"
  },
  "health_evolution": {
    "conditions_resolved": ["issues that went away"],
    "new_conditions": ["new health issues that appeared"],
    "chronic_conditions": ["ongoing issues throughout year"],
    "improvement_trajectory": {
      "overall_trend": "improving/stable/declining",
      "specific_improvements": ["what got better"],
      "specific_declines": ["what got worse"]
    }
  },
  "pattern_insights": {
    "seasonal_health": {
      "winter": ["winter-specific patterns"],
      "spring": ["spring-specific patterns"],
      "summer": ["summer-specific patterns"],
      "fall": ["fall-specific patterns"]
    },
    "monthly_patterns": {
      "best_months": ["healthiest months and why"],
      "challenging_months": ["difficult months and why"],
      "turning_points": ["key moments of change"]
    },
    "long_term_correlations": ["X seems to pop up when Y over months"]
  },
  "body_system_review": {
    "neurological": {
      "year_summary": "overview",
      "frequency_trend": "increasing/stable/decreasing",
      "severity_trend": "better/same/worse"
    },
    "cardiovascular": {},
    "respiratory": {},
    "gastrointestinal": {},
    "musculoskeletal": {},
    "mental_health": {}
  },
  "preventive_health_assessment": {
    "screening_recommendations": ["based on age and risk factors"],
    "vaccination_reminders": ["flu, covid, others"],
    "lifestyle_risk_factors": ["identified risks"],
    "protective_factors": ["positive health behaviors"]
  },
  "data_driven_recommendations": {
    "top_3_priorities": ["most important focus areas"],
    "specialist_referrals": ["based on year's data"],
    "lifestyle_modifications": ["evidence-based suggestions"],
    "monitoring_plan": ["what to track in coming year"],
    "goal_setting": ["SMART goals for health"]
  },
  "year_ahead_outlook": {
    "predicted_challenges": ["based on patterns"],
    "opportunities": ["for health improvement"],
    "milestones": ["health goals to achieve"]
  }
}"""

        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            temperature=0.3,
            max_tokens=5000  # Larger for comprehensive annual report
        )
        
        report_data = extract_json_from_response(llm_response.get("content", llm_response.get("raw_content", "")))
        
        if not report_data:
            report_data = {
                "executive_summary": {
                    "one_page_summary": "Annual report generation failed. Please retry.",
                    "key_findings": [],
                    "health_journey": "Unable to generate",
                    "action_items": ["Regenerate report"]
                }
            }
        
        # Save report
        report_id = str(uuid.uuid4())
        report_record = {
            "id": report_id,
            "user_id": request.user_id,
            "report_type": "annual_comprehensive",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "executive_summary": report_data["executive_summary"]["one_page_summary"],
            "confidence_score": 92,
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "year": year,
            "time_range": config["time_range"]
        }
        
        await safe_insert_report(report_record)
        
        return {
            "report_id": report_id,
            "report_type": "annual_comprehensive",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report_data": report_data,
            "year": year,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating annual report: {e}")
        return {"error": str(e), "status": "error"}

# ================== DOCTOR COLLABORATION ENDPOINTS ==================

@app.put("/api/report/{report_id}/doctor-notes")
async def add_doctor_notes(report_id: str, request: DoctorNotesRequest):
    """Add doctor notes to a report"""
    try:
        # Verify report exists
        report_check = supabase.table("medical_reports")\
            .select("id")\
            .eq("id", report_id)\
            .execute()
        
        if not report_check.data:
            return {"error": "Report not found", "status": "error"}
        
        # Create doctor notes record
        notes_data = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "doctor_npi": request.doctor_npi,
            "specialty": request.specialty,
            "notes": request.notes,
            "sections_reviewed": request.sections_reviewed,
            "diagnosis_added": request.diagnosis,
            "plan_modifications": request.plan_modifications,
            "follow_up_instructions": request.follow_up_instructions,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("report_doctor_notes").insert(notes_data).execute()
        
        # Update report to mark as reviewed
        supabase.table("medical_reports").update({
            "doctor_reviewed": True,
            "last_modified": datetime.now(timezone.utc).isoformat()
        }).eq("id", report_id).execute()
        
        return {
            "notes_id": notes_data["id"],
            "report_id": report_id,
            "status": "success",
            "message": "Doctor notes added successfully"
        }
        
    except Exception as e:
        print(f"Error adding doctor notes: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/{report_id}/share")
async def share_report(report_id: str, request: ShareReportRequest):
    """Share report with another doctor"""
    try:
        # Verify report exists
        report_check = supabase.table("medical_reports")\
            .select("id, user_id")\
            .eq("id", report_id)\
            .execute()
        
        if not report_check.data:
            return {"error": "Report not found", "status": "error"}
        
        # Create share record
        share_data = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "shared_by_npi": request.shared_by_npi,
            "shared_with_npi": request.recipient_npi,
            "access_level": request.access_level,
            "share_notes": request.notes,
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=request.expiration_days)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("report_shares").insert(share_data).execute()
        
        # Generate share link
        share_link = f"{request.base_url}/shared-report/{share_data['id']}"
        
        return {
            "share_id": share_data["id"],
            "share_link": share_link,
            "expires_at": share_data["expires_at"],
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error sharing report: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/report/{report_id}/rate")
async def rate_report(report_id: str, request: RateReportRequest):
    """Rate a report's usefulness"""
    try:
        # Check if doctor already rated this report
        existing = supabase.table("report_ratings")\
            .select("id")\
            .eq("report_id", report_id)\
            .eq("doctor_npi", request.doctor_npi)\
            .execute()
        
        if existing.data:
            # Update existing rating
            supabase.table("report_ratings").update({
                "usefulness_score": request.usefulness_score,
                "accuracy_score": request.accuracy_score,
                "time_saved_minutes": request.time_saved,
                "would_recommend": request.would_recommend,
                "feedback_text": request.feedback,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", existing.data[0]["id"]).execute()
            
            rating_id = existing.data[0]["id"]
        else:
            # Create new rating
            rating_data = {
                "id": str(uuid.uuid4()),
                "report_id": report_id,
                "doctor_npi": request.doctor_npi,
                "usefulness_score": request.usefulness_score,
                "accuracy_score": request.accuracy_score,
                "time_saved_minutes": request.time_saved,
                "would_recommend": request.would_recommend,
                "feedback_text": request.feedback,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            response = supabase.table("report_ratings").insert(rating_data).execute()
            rating_id = rating_data["id"]
        
        # Calculate average ratings
        avg_usefulness = await get_average_rating(report_id, "usefulness_score")
        avg_accuracy = await get_average_rating(report_id, "accuracy_score")
        
        return {
            "rating_id": rating_id,
            "report_id": report_id,
            "average_usefulness": avg_usefulness,
            "average_accuracy": avg_accuracy,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error rating report: {e}")
        return {"error": str(e), "status": "error"}

# ================== POPULATION HEALTH ENDPOINTS ==================

@app.get("/api/population-health/alerts")
async def get_outbreak_alerts(geographic_area: Optional[str] = None):
    """Get current outbreak alerts for population health monitoring"""
    try:
        # Base query for active outbreaks
        query = supabase.table("outbreak_tracking")\
            .select("*")\
            .eq("status", "active")
        
        # Filter by geographic area if provided
        if geographic_area:
            query = query.eq("geographic_area", geographic_area)
        
        # Order by case count and trend
        response = query.order("case_count", desc=True).execute()
        
        outbreaks = response.data or []
        
        # Analyze patterns across all reports for emerging threats
        # This would normally aggregate data across all users in the area
        emerging_patterns = {
            "respiratory_syndrome": {
                "case_count": len([o for o in outbreaks if "cough" in o.get("symptom_cluster", "").lower()]),
                "trend": "increasing" if len(outbreaks) > 5 else "stable"
            },
            "gastrointestinal_syndrome": {
                "case_count": len([o for o in outbreaks if "nausea" in o.get("symptom_cluster", "").lower() or "diarrhea" in o.get("symptom_cluster", "").lower()]),
                "trend": "stable"
            }
        }
        
        # Format alerts
        alerts = []
        for outbreak in outbreaks:
            alerts.append({
                "id": outbreak["id"],
                "symptom_cluster": outbreak["symptom_cluster"],
                "geographic_area": outbreak["geographic_area"],
                "case_count": outbreak["case_count"],
                "trend": outbreak["trend"],
                "first_detected": outbreak["first_detected"],
                "cdc_alert_id": outbreak.get("cdc_alert_id"),
                "severity": "high" if outbreak["case_count"] > 50 else "medium" if outbreak["case_count"] > 20 else "low"
            })
        
        return {
            "active_alerts": alerts,
            "total_active": len(alerts),
            "emerging_patterns": emerging_patterns,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "geographic_scope": geographic_area or "all_areas",
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching outbreak alerts: {e}")
        return {"error": str(e), "status": "error"}

# Additional Report Management Endpoints
@app.get("/api/reports")
async def get_user_reports(user_id: str):
    """Get all reports for a user"""
    try:
        response = supabase.table("medical_reports")\
            .select("id, report_type, created_at, executive_summary, confidence_score")\
            .eq("user_id", user_id)\
            .order("created_at.desc")\
            .execute()
        
        reports = response.data or []
        
        # Format for frontend - return array directly (frontend expects array, not object)
        formatted_reports = []
        for report in reports:
            formatted_reports.append({
                "id": report["id"],
                "type": report["report_type"],
                "title": report["report_type"].replace("_", " ").title(),
                "summary": report["executive_summary"][:150] + "..." if len(report.get("executive_summary", "")) > 150 else report.get("executive_summary", ""),
                "confidence": report.get("confidence_score", 0),
                "created_at": report["created_at"],
                "generated_date": report["created_at"]
            })
        
        # Return array directly for frontend compatibility
        return formatted_reports
        
    except Exception as e:
        print(f"Error fetching user reports: {e}")
        # Return empty array on error to prevent frontend crashes
        return []

@app.post("/api/reports/{report_id}/access")
async def mark_report_accessed(report_id: str):
    """Mark report as accessed (for analytics)"""
    try:
        # Update last_accessed timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        
        # This could update a last_accessed field if you want to track it
        # For now, just return success since the field doesn't exist yet
        
        return {
            "report_id": report_id,
            "accessed_at": current_time,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error marking report accessed: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/reports/{report_id}")
async def get_report_by_id(report_id: str):
    """Get a specific report by ID"""
    try:
        response = supabase.table("medical_reports")\
            .select("*")\
            .eq("id", report_id)\
            .execute()
        
        if not response.data:
            return {"error": "Report not found", "status": "error"}
        
        report = response.data[0]
        
        return {
            "report_id": report["id"],
            "report_type": report["report_type"],
            "generated_at": report["created_at"],
            "report_data": report["report_data"],
            "confidence_score": report.get("confidence_score", 0),
            "model_used": report.get("model_used", ""),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching report: {e}")
        return {"error": str(e), "status": "error"}

# ================== TRACKING ENDPOINTS ==================

class TrackingSuggestRequest(BaseModel):
    source_type: str  # 'quick_scan' or 'deep_dive'
    source_id: str
    user_id: str

@app.post("/api/tracking/suggest")
async def suggest_tracking(request: TrackingSuggestRequest):
    """Analyze a scan/dive and suggest what to track"""
    try:
        # Fetch the source data
        if request.source_type == "quick_scan":
            response = supabase.table("quick_scans").select("*").eq("id", request.source_id).execute()
            if not response.data:
                return {"error": "Quick scan not found", "status": "error"}
            
            source_data = response.data[0]
            analysis = source_data.get("analysis_result", {})
            body_part = source_data.get("body_part", "")
            form_data = source_data.get("form_data", {})
            
        elif request.source_type == "deep_dive":
            response = supabase.table("deep_dive_sessions").select("*").eq("id", request.source_id).execute()
            if not response.data:
                return {"error": "Deep dive not found", "status": "error"}
            
            source_data = response.data[0]
            analysis = source_data.get("final_analysis", {})
            body_part = source_data.get("body_part", "")
            form_data = source_data.get("form_data", {})
        else:
            return {"error": "Invalid source type", "status": "error"}
        
        # Create prompt for AI to analyze what to track
        system_prompt = """You are analyzing medical scan data to suggest ONE most important metric to track long-term.

        Consider:
        1. The primary condition identified
        2. Severity and urgency levels
        3. Symptoms that would benefit from tracking
        4. What metric would provide the most insight over time
        
        Choose tracking type:
        - severity: Track pain/symptom intensity (1-10 scale)
        - frequency: Track occurrences per day/week
        - duration: Track how long symptoms last
        - occurrence: Simple yes/no tracking
        
        Return JSON with this structure:
        {
            "metric_name": "Headache Severity",
            "metric_description": "Track daily headache pain levels to identify patterns",
            "y_axis_label": "Pain Level (1-10)",
            "y_axis_type": "numeric",
            "y_axis_min": 0,
            "y_axis_max": 10,
            "tracking_type": "severity",
            "symptom_keywords": ["headache", "head pain", "migraine"],
            "ai_reasoning": "Tracking severity will help identify triggers and treatment effectiveness",
            "confidence_score": 0.85,
            "suggested_questions": ["Rate your headache pain from 1-10", "Any specific triggers today?"]
        }"""
        
        user_message = f"""Analyze this health data and suggest the SINGLE MOST IMPORTANT metric to track:
        
        Body Part: {body_part}
        Primary Condition: {analysis.get('primaryCondition', 'Unknown')}
        Symptoms: {', '.join(analysis.get('symptoms', []))}
        Urgency: {analysis.get('urgency', 'unknown')}
        User Reported: {form_data.get('symptoms', '')}
        Pain Level: {form_data.get('painLevel', 'N/A')}/10
        
        What ONE metric would be most valuable to track over time?"""
        
        # Call AI for suggestion
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            model="tngtech/deepseek-r1t-chimera:free",
            user_id=request.user_id,
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract suggestion from response
        suggestion = extract_json_from_response(llm_response.get("content", ""))
        if not suggestion:
            return {"error": "Failed to generate tracking suggestion", "status": "error"}
        
        # Save suggestion to database
        suggestion_id = str(uuid.uuid4())
        suggestion_data = {
            "id": suggestion_id,
            "user_id": request.user_id,
            "source_type": request.source_type,
            "source_id": request.source_id,
            "suggestions": [suggestion],  # Array for future multi-suggestion support
            "model_used": "tngtech/deepseek-r1t-chimera:free",
            "confidence_scores": [suggestion.get("confidence_score", 0.5)],
            "reasoning": suggestion.get("ai_reasoning", ""),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("tracking_suggestions").insert(suggestion_data).execute()
        
        return {
            "suggestion_id": suggestion_id,
            "suggestion": suggestion,
            "source_type": request.source_type,
            "source_id": request.source_id,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating tracking suggestion: {e}")
        return {"error": str(e), "status": "error"}

class TrackingConfigureRequest(BaseModel):
    suggestion_id: str
    user_id: str
    metric_name: str  # User can edit
    y_axis_label: str  # User can edit
    show_on_homepage: bool = True

@app.post("/api/tracking/configure")
async def configure_tracking(request: TrackingConfigureRequest):
    """Create or update a tracking configuration"""
    try:
        # Fetch the suggestion
        response = supabase.table("tracking_suggestions").select("*").eq("id", request.suggestion_id).execute()
        if not response.data:
            return {"error": "Suggestion not found", "status": "error"}
        
        suggestion_data = response.data[0]
        suggestion = suggestion_data["suggestions"][0]  # Get first suggestion
        
        # Create tracking configuration
        config_id = str(uuid.uuid4())
        config_data = {
            "id": config_id,
            "user_id": request.user_id,
            "source_type": suggestion_data["source_type"],
            "source_id": suggestion_data["source_id"],
            "metric_name": request.metric_name,
            "metric_description": suggestion.get("metric_description", ""),
            "x_axis_label": "Date",
            "y_axis_label": request.y_axis_label,
            "y_axis_type": suggestion.get("y_axis_type", "numeric"),
            "y_axis_min": suggestion.get("y_axis_min", 0),
            "y_axis_max": suggestion.get("y_axis_max", 10),
            "tracking_type": suggestion.get("tracking_type", "severity"),
            "symptom_keywords": suggestion.get("symptom_keywords", []),
            "body_parts": [suggestion_data.get("body_part", "")],
            "ai_suggested_questions": suggestion.get("suggested_questions", []),
            "ai_reasoning": suggestion.get("ai_reasoning", ""),
            "confidence_score": suggestion.get("confidence_score", 0.5),
            "status": "approved",  # Auto-approve when user configures
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "show_on_homepage": request.show_on_homepage,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("tracking_configurations").insert(config_data).execute()
        
        # Mark suggestion as actioned
        supabase.table("tracking_suggestions").update({
            "actioned_at": datetime.now(timezone.utc).isoformat(),
            "action_taken": "approved_some"
        }).eq("id", request.suggestion_id).execute()
        
        return {
            "config_id": config_id,
            "configuration": config_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error configuring tracking: {e}")
        return {"error": str(e), "status": "error"}

@app.post("/api/tracking/approve/{suggestion_id}")
async def approve_tracking_suggestion(suggestion_id: str, user_id: str = None):
    """Quick approve a suggestion without modification"""
    try:
        # Fetch the suggestion
        response = supabase.table("tracking_suggestions").select("*").eq("id", suggestion_id).execute()
        if not response.data:
            return {"error": "Suggestion not found", "status": "error"}
        
        suggestion_data = response.data[0]
        suggestion = suggestion_data["suggestions"][0]
        
        # Create tracking configuration with default values
        config_id = str(uuid.uuid4())
        config_data = {
            "id": config_id,
            "user_id": suggestion_data["user_id"],
            "source_type": suggestion_data["source_type"],
            "source_id": suggestion_data["source_id"],
            "metric_name": suggestion.get("metric_name", ""),
            "metric_description": suggestion.get("metric_description", ""),
            "x_axis_label": "Date",
            "y_axis_label": suggestion.get("y_axis_label", ""),
            "y_axis_type": suggestion.get("y_axis_type", "numeric"),
            "y_axis_min": suggestion.get("y_axis_min", 0),
            "y_axis_max": suggestion.get("y_axis_max", 10),
            "tracking_type": suggestion.get("tracking_type", "severity"),
            "symptom_keywords": suggestion.get("symptom_keywords", []),
            "ai_suggested_questions": suggestion.get("suggested_questions", []),
            "ai_reasoning": suggestion.get("ai_reasoning", ""),
            "confidence_score": suggestion.get("confidence_score", 0.5),
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "show_on_homepage": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("tracking_configurations").insert(config_data).execute()
        
        # Mark suggestion as actioned
        supabase.table("tracking_suggestions").update({
            "actioned_at": datetime.now(timezone.utc).isoformat(),
            "action_taken": "approved_all"
        }).eq("id", suggestion_id).execute()
        
        return {
            "config_id": config_id,
            "configuration": config_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error approving suggestion: {e}")
        return {"error": str(e), "status": "error"}

class TrackingDataPointRequest(BaseModel):
    configuration_id: str
    user_id: str
    value: float
    notes: Optional[str] = None
    recorded_at: Optional[str] = None  # ISO timestamp, defaults to now

@app.post("/api/tracking/data")
async def add_tracking_data_point(request: TrackingDataPointRequest):
    """Add a data point for tracking"""
    try:
        # Verify configuration exists and belongs to user
        response = supabase.table("tracking_configurations").select("*").eq("id", request.configuration_id).eq("user_id", request.user_id).execute()
        if not response.data:
            return {"error": "Configuration not found", "status": "error"}
        
        config = response.data[0]
        
        # Create data point
        data_point = {
            "id": str(uuid.uuid4()),
            "configuration_id": request.configuration_id,
            "user_id": request.user_id,
            "value": request.value,
            "notes": request.notes,
            "source_type": "manual",
            "recorded_at": request.recorded_at or datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("tracking_data_points").insert(data_point).execute()
        
        # Update configuration stats
        supabase.table("tracking_configurations").update({
            "last_data_point": data_point["recorded_at"],
            "data_points_count": config.get("data_points_count", 0) + 1,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", request.configuration_id).execute()
        
        return {
            "data_point_id": data_point["id"],
            "value": request.value,
            "recorded_at": data_point["recorded_at"],
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error adding data point: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/tracking/dashboard")
async def get_tracking_dashboard(user_id: str):
    """Get dashboard data with mixed suggestions and active tracking"""
    try:
        # Fetch active tracking configurations
        configs_response = supabase.table("tracking_configurations")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "approved")\
            .eq("show_on_homepage", True)\
            .order("display_order")\
            .order("created_at.desc")\
            .execute()
        
        active_configs = configs_response.data or []
        
        # Fetch recent unactioned suggestions
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        suggestions_response = supabase.table("tracking_suggestions")\
            .select("*")\
            .eq("user_id", user_id)\
            .is_("actioned_at", "null")\
            .gte("created_at", cutoff_date)\
            .order("created_at.desc")\
            .limit(5)\
            .execute()
        
        suggestions = suggestions_response.data or []
        
        # Build dashboard items
        dashboard_items = []
        
        # Add active tracking cards
        for config in active_configs:
            # Get latest data point
            data_response = supabase.table("tracking_data_points")\
                .select("*")\
                .eq("configuration_id", config["id"])\
                .order("recorded_at", desc=True)\
                .limit(2)\
                .execute()
            
            data_points = data_response.data or []
            latest_value = data_points[0]["value"] if data_points else None
            previous_value = data_points[1]["value"] if len(data_points) > 1 else None
            
            # Calculate trend
            trend = None
            if latest_value is not None and previous_value is not None:
                if latest_value > previous_value:
                    trend = "increasing"
                elif latest_value < previous_value:
                    trend = "decreasing"
                else:
                    trend = "stable"
            
            dashboard_items.append({
                "type": "active",
                "id": config["id"],
                "metric_name": config["metric_name"],
                "y_axis_label": config["y_axis_label"],
                "latest_value": latest_value,
                "latest_date": data_points[0]["recorded_at"] if data_points else None,
                "trend": trend,
                "chart_type": config.get("chart_type", "line"),
                "color": config.get("color", "#3B82F6"),
                "data_points_count": config.get("data_points_count", 0)
            })
        
        # Add suggestion cards
        for suggestion in suggestions:
            suggestion_data = suggestion["suggestions"][0] if suggestion["suggestions"] else {}
            dashboard_items.append({
                "type": "suggestion",
                "id": suggestion["id"],
                "metric_name": suggestion_data.get("metric_name", "Unknown Metric"),
                "description": suggestion_data.get("metric_description", ""),
                "source_type": suggestion["source_type"],
                "confidence_score": suggestion_data.get("confidence_score", 0),
                "created_at": suggestion["created_at"]
            })
        
        return {
            "dashboard_items": dashboard_items,
            "total_active": len(active_configs),
            "total_suggestions": len(suggestions),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching dashboard: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/tracking/chart/{config_id}")
async def get_tracking_chart_data(config_id: str, days: int = 30):
    """Get chart data for a specific tracking configuration"""
    try:
        # Fetch configuration
        config_response = supabase.table("tracking_configurations").select("*").eq("id", config_id).execute()
        if not config_response.data:
            return {"error": "Configuration not found", "status": "error"}
        
        config = config_response.data[0]
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Fetch data points
        data_response = supabase.table("tracking_data_points")\
            .select("*")\
            .eq("configuration_id", config_id)\
            .gte("recorded_at", start_date.isoformat())\
            .lte("recorded_at", end_date.isoformat())\
            .order("recorded_at")\
            .execute()
        
        data_points = data_response.data or []
        
        # Format for charting
        chart_data = {
            "config": {
                "metric_name": config["metric_name"],
                "x_axis_label": config["x_axis_label"],
                "y_axis_label": config["y_axis_label"],
                "y_axis_min": config.get("y_axis_min", 0),
                "y_axis_max": config.get("y_axis_max", 10),
                "chart_type": config.get("chart_type", "line"),
                "color": config.get("color", "#3B82F6")
            },
            "data": [
                {
                    "x": dp["recorded_at"],
                    "y": dp["value"],
                    "notes": dp.get("notes", "")
                }
                for dp in data_points
            ],
            "statistics": {
                "average": sum(dp["value"] for dp in data_points) / len(data_points) if data_points else 0,
                "min": min(dp["value"] for dp in data_points) if data_points else 0,
                "max": max(dp["value"] for dp in data_points) if data_points else 0,
                "count": len(data_points)
            }
        }
        
        return {
            "chart_data": chart_data,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching chart data: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/tracking/past-scans")
async def get_past_scans_for_tracking(user_id: str, limit: int = 20):
    """Get past quick scans that can be used to start tracking"""
    try:
        # Fetch recent quick scans
        response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at.desc")\
            .limit(limit)\
            .execute()
        
        scans = response.data or []
        
        # Check which ones already have tracking
        scan_ids = [scan["id"] for scan in scans]
        existing_tracking = supabase.table("tracking_configurations")\
            .select("source_id")\
            .eq("source_type", "quick_scan")\
            .in_("source_id", scan_ids)\
            .execute()
        
        tracked_ids = {t["source_id"] for t in existing_tracking.data or []}
        
        # Format scan data
        past_scans = []
        for scan in scans:
            analysis = scan.get("analysis_result", {})
            past_scans.append({
                "id": scan["id"],
                "date": scan["created_at"],
                "body_part": scan["body_part"],
                "primary_condition": analysis.get("primaryCondition", "Unknown"),
                "symptoms": analysis.get("symptoms", [])[:3],  # First 3 symptoms
                "urgency": analysis.get("urgency", scan.get("urgency_level", "unknown")),
                "has_tracking": scan["id"] in tracked_ids
            })
        
        return {
            "past_scans": past_scans,
            "total": len(past_scans),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching past scans: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/api/tracking/past-dives")
async def get_past_dives_for_tracking(user_id: str, limit: int = 20):
    """Get past deep dives that can be used to start tracking"""
    try:
        # Fetch completed deep dives
        response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .eq("user_id", user_id)\
            .eq("status", "completed")\
            .order("created_at.desc")\
            .limit(limit)\
            .execute()
        
        dives = response.data or []
        
        # Check which ones already have tracking
        dive_ids = [dive["id"] for dive in dives]
        existing_tracking = supabase.table("tracking_configurations")\
            .select("source_id")\
            .eq("source_type", "deep_dive")\
            .in_("source_id", dive_ids)\
            .execute()
        
        tracked_ids = {t["source_id"] for t in existing_tracking.data or []}
        
        # Format dive data
        past_dives = []
        for dive in dives:
            analysis = dive.get("final_analysis", {})
            past_dives.append({
                "id": dive["id"],
                "date": dive["completed_at"] or dive["created_at"],
                "body_part": dive["body_part"],
                "primary_condition": analysis.get("primaryCondition", "Unknown"),
                "symptoms": analysis.get("symptoms", [])[:3],
                "confidence": analysis.get("confidence", dive.get("final_confidence", 0)),
                "questions_asked": len(dive.get("questions", [])),
                "has_tracking": dive["id"] in tracked_ids
            })
        
        return {
            "past_dives": past_dives,
            "total": len(past_dives),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching past dives: {e}")
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
            },
            "health_story": "POST /api/health-story",
            "reports": {
                "analyze": "POST /api/report/analyze",
                "comprehensive": "POST /api/report/comprehensive",
                "urgent_triage": "POST /api/report/urgent-triage",
                "photo_progression": "POST /api/report/photo-progression",
                "symptom_timeline": "POST /api/report/symptom-timeline",
                "specialist": "POST /api/report/specialist",
                "annual_summary": "POST /api/report/annual-summary",
                # NEW SPECIALIST ENDPOINTS
                "cardiology": "POST /api/report/cardiology",
                "neurology": "POST /api/report/neurology",
                "psychiatry": "POST /api/report/psychiatry",
                "dermatology": "POST /api/report/dermatology",
                "gastroenterology": "POST /api/report/gastroenterology",
                "endocrinology": "POST /api/report/endocrinology",
                "pulmonology": "POST /api/report/pulmonology",
                # TIME-BASED REPORTS
                "30_day": "POST /api/report/30-day",
                "annual": "POST /api/report/annual",
                # DOCTOR COLLABORATION
                "add_doctor_notes": "PUT /api/report/{report_id}/doctor-notes",
                "share_report": "POST /api/report/{report_id}/share",
                "rate_report": "POST /api/report/{report_id}/rate",
                # POPULATION HEALTH
                "outbreak_alerts": "GET /api/population-health/alerts",
                # EXISTING
                "list_user_reports": "GET /api/reports?user_id=USER_ID",
                "get_report": "GET /api/reports/{report_id}",
                "mark_accessed": "POST /api/reports/{report_id}/access"
            },
            "tracking": {
                "suggest": "POST /api/tracking/suggest",
                "configure": "POST /api/tracking/configure",
                "approve": "POST /api/tracking/approve/{suggestion_id}",
                "update_config": "PUT /api/tracking/config/{config_id}",
                "add_data_point": "POST /api/tracking/data",
                "get_dashboard": "GET /api/tracking/dashboard",
                "get_chart_data": "GET /api/tracking/chart/{config_id}",
                "get_history": "GET /api/tracking/history",
                "get_past_scans": "GET /api/tracking/past-scans",
                "get_past_dives": "GET /api/tracking/past-dives"
            }
        }
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("\n" + "="*60)
    print("ORACLE AI SERVER - READY!")
    print("="*60)
    print(f"Server: http://localhost:{port}")
    print(f"Chat: POST http://localhost:{port}/api/chat")
    print(f"Health: GET http://localhost:{port}/api/health")
    print("Using: DeepSeek AI (Free)")
    print("="*60)
    print("\nYour AI Oracle is ready to help!\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
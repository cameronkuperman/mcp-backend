"""Data gathering utilities for reports and health stories"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from supabase_client import supabase
# Removed circular import - get_user_medical_data will be handled differently

async def get_user_medical_data(user_id: str) -> Optional[Dict]:
    """Get user's medical profile data"""
    try:
        response = supabase.table("medical")\
            .select("*")\
            .eq("id", user_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {"user_id": user_id, "note": "No medical data found"}
    except Exception as e:
        print(f"Error fetching medical data: {e}")
        return {"user_id": user_id, "error": str(e)}

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
        
        # Get Quick Scans - with string conversion for user_id
        scan_response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .execute()
        data["quick_scans"] = scan_response.data if scan_response.data else []
        
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
        "oracle_chats": []
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

def has_emergency_indicators(request) -> bool:
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
    
    # Format into string for LLM
    pattern_text = "Cardiac-Related History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Cardiac symptoms')}\n"
    
    return pattern_text if relevant_data else "No cardiac-specific patterns found."

async def extract_neuro_patterns(data: dict) -> str:
    """Extract neurology-specific patterns from data"""
    neuro_symptoms = ["headache", "migraine", "dizziness", "numbness", "tingling", "vision", "seizure", "memory"]
    
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
    
    for dive in data.get("deep_dives", []):
        dive_str = str(dive).lower()
        if any(symptom in dive_str for symptom in neuro_symptoms):
            relevant_data.append({
                "date": dive["created_at"],
                "body_part": dive["body_part"],
                "final_analysis": dive.get("final_analysis", {})
            })
    
    # Format into string for LLM
    pattern_text = "Neurological History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Neurological symptoms')}\n"
    
    return pattern_text if relevant_data else "No neurological patterns found."

async def extract_mental_health_patterns(data: dict) -> str:
    """Extract mental health patterns from data"""
    psych_keywords = ["anxiety", "depression", "stress", "mood", "sleep", "panic", "worry", "mental"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in psych_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "analysis": scan.get("analysis_result", {})
            })
    
    # Format into string for LLM
    pattern_text = "Mental Health History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Mental health concerns')}\n"
    
    return pattern_text if relevant_data else "No mental health patterns found."

async def extract_dermatology_patterns(data: dict, photo_data: dict) -> str:
    """Extract dermatology patterns including photo data"""
    derm_keywords = ["rash", "skin", "itching", "lesion", "mole", "spot", "eczema", "psoriasis"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in derm_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "body_part": scan.get("body_part"),
                "analysis": scan.get("analysis_result", {})
            })
    
    # Format into string for LLM
    pattern_text = "Dermatological History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Skin condition')} on {item.get('body_part', 'unspecified area')}\n"
    
    if photo_data:
        pattern_text += f"\nPhoto documentation available: {len(photo_data)} images\n"
    
    return pattern_text if relevant_data else "No dermatological patterns found."

async def extract_gi_patterns(data: dict) -> str:
    """Extract GI patterns from data"""
    gi_keywords = ["stomach", "abdominal", "nausea", "diarrhea", "constipation", "bloating", "vomiting", "bowel"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in gi_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "severity": scan.get("form_data", {}).get("painLevel"),
                "analysis": scan.get("analysis_result", {})
            })
    
    # Format into string for LLM
    pattern_text = "Gastrointestinal History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'GI symptoms')} (severity: {item.get('severity', 'unknown')}/10)\n"
    
    return pattern_text if relevant_data else "No GI patterns found."

async def extract_endocrine_patterns(data: dict) -> str:
    """Extract endocrine patterns from data"""
    endo_keywords = ["fatigue", "weight", "thyroid", "diabetes", "energy", "temperature", "hormone", "metabolism"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in endo_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "analysis": scan.get("analysis_result", {})
            })
    
    # Format into string for LLM
    pattern_text = "Endocrine/Metabolic History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Endocrine symptoms')}\n"
    
    return pattern_text if relevant_data else "No endocrine patterns found."

async def extract_pulmonary_patterns(data: dict) -> str:
    """Extract pulmonary patterns from data"""
    pulm_keywords = ["breathing", "cough", "wheeze", "asthma", "shortness", "chest", "lung", "respiratory"]
    
    relevant_data = []
    for scan in data.get("quick_scans", []):
        form_data_str = str(scan.get("form_data", {})).lower()
        if any(keyword in form_data_str for keyword in pulm_keywords):
            relevant_data.append({
                "date": scan["created_at"],
                "symptoms": scan.get("form_data", {}).get("symptoms"),
                "body_part": scan.get("body_part"),
                "analysis": scan.get("analysis_result", {})
            })
    
    # Format into string for LLM
    pattern_text = "Pulmonary/Respiratory History:\n"
    for item in sorted(relevant_data, key=lambda x: x["date"]):
        pattern_text += f"- {item['date'][:10]}: {item.get('symptoms', 'Respiratory symptoms')}\n"
    
    return pattern_text if relevant_data else "No pulmonary patterns found."

async def gather_photo_data(user_id: str, config: dict):
    """Placeholder for photo data gathering"""
    # This would integrate with your photo storage system
    # For now, return empty list
    return []

async def gather_user_health_data(user_id: str) -> Dict[str, Any]:
    """
    Gather comprehensive health data for analysis generation
    Returns structured data for AI processing
    """
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())  # Monday of current week
    month_ago = now - timedelta(days=30)
    
    data = {
        "oracle_sessions": {"total_sessions": 0, "recent_topics": []},
        "quick_scans": {"total_scans": 0, "recent_scans": []},
        "deep_dives": {"total_dives": 0, "recent_dives": []},
        "body_parts": [],
        "recent_symptoms": [],
        "symptom_patterns": {},
        "body_part_frequency": {},
        "tracking_frequency": "unknown",
        "notes_count": 0
    }
    
    try:
        # Get Oracle chat messages through conversations
        conv_response = supabase.table("conversations")\
            .select("id")\
            .eq("user_id", user_id)\
            .gte("updated_at", month_ago.isoformat())\
            .execute()
        
        oracle_messages = []
        if conv_response.data:
            conv_ids = [c['id'] for c in conv_response.data]
            # Get messages from these conversations
            msg_response = supabase.table("messages")\
                .select("content, created_at")\
                .in_("conversation_id", conv_ids)\
                .order("created_at.desc")\
                .limit(50)\
                .execute()
            oracle_messages = msg_response.data if msg_response.data else []
        
        if oracle_messages:
            data["oracle_sessions"]["total_sessions"] = len(oracle_messages)
            # Extract topics from recent messages
            for msg in oracle_messages[:10]:  # Last 10 messages
                content = msg.get("content", "").lower()
                if len(content) > 20:  # Only meaningful messages
                    data["oracle_sessions"]["recent_topics"].append(content[:100])
        
        # Get Quick Scans
        scans_response = supabase.table("quick_scans")\
            .select("body_part, form_data, created_at")\
            .eq("user_id", user_id)\
            .gte("created_at", month_ago.isoformat())\
            .order("created_at.desc")\
            .execute()
        
        if scans_response.data:
            data["quick_scans"]["total_scans"] = len(scans_response.data)
            body_parts = []
            symptoms = []
            
            for scan in scans_response.data:
                body_part = scan.get("body_part", "").lower()
                if body_part:
                    body_parts.append(body_part)
                    data["body_part_frequency"][body_part] = data["body_part_frequency"].get(body_part, 0) + 1
                
                form_data = scan.get("form_data", {})
                if isinstance(form_data, dict):
                    scan_symptoms = form_data.get("symptoms", "").lower().split(",")
                    for symptom in scan_symptoms:
                        symptom = symptom.strip()
                        if symptom:
                            symptoms.append(symptom)
                            data["symptom_patterns"][symptom] = data["symptom_patterns"].get(symptom, 0) + 1
            
            data["body_parts"] = list(set(body_parts))
            data["recent_symptoms"] = list(set(symptoms))
        
        # Get Deep Dives
        dives_response = supabase.table("deep_dive_sessions")\
            .select("body_part, status, created_at")\
            .eq("user_id", user_id)\
            .eq("status", "completed")\
            .gte("created_at", month_ago.isoformat())\
            .execute()
        
        if dives_response.data:
            data["deep_dives"]["total_dives"] = len(dives_response.data)
        
        # Get symptom tracking frequency
        tracking_response = supabase.table("symptom_tracking")\
            .select("created_at")\
            .eq("user_id", user_id)\
            .gte("created_at", week_start.isoformat())\
            .execute()
        
        if tracking_response.data:
            tracking_days = len(set(entry["created_at"][:10] for entry in tracking_response.data))
            if tracking_days >= 5:
                data["tracking_frequency"] = "daily"
            elif tracking_days >= 3:
                data["tracking_frequency"] = "frequent"
            elif tracking_days >= 1:
                data["tracking_frequency"] = "occasional"
            else:
                data["tracking_frequency"] = "rare"
        
        # Get health notes count
        notes_response = supabase.table("health_notes")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if notes_response.data:
            data["notes_count"] = len(notes_response.data)
        
    except Exception as e:
        print(f"Error gathering health data: {e}")
    
    return data
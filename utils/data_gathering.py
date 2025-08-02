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

async def gather_selected_data(
    user_id: str, 
    quick_scan_ids: Optional[List[str]] = None, 
    deep_dive_ids: Optional[List[str]] = None, 
    photo_session_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Gather only specific selected interactions for specialist reports
    
    Args:
        user_id: User ID for verification
        quick_scan_ids: List of specific quick scan IDs to fetch
        deep_dive_ids: List of specific deep dive session IDs to fetch
        photo_session_ids: List of specific photo session IDs to fetch
        
    Returns:
        Dictionary with selected data matching the structure of gather_comprehensive_data
    """
    data = {
        "quick_scans": [],
        "deep_dives": [],
        "photo_analyses": [],
        "symptom_tracking": [],
        "tracking_data": [],
        "llm_summaries": [],
        "wearables": {}
    }
    
    try:
        # Get specific quick scans
        if quick_scan_ids:
            scans_result = supabase.table("quick_scans")\
                .select("*")\
                .in_("id", quick_scan_ids)\
                .eq("user_id", user_id)\
                .order("created_at")\
                .execute()
            data["quick_scans"] = scans_result.data or []
            
            # Get dates for symptom tracking correlation
            scan_dates = [scan["created_at"][:10] for scan in data["quick_scans"]]
            
            # Get symptom tracking entries from same dates
            if scan_dates:
                for date in scan_dates:
                    symptoms_result = supabase.table("symptom_tracking")\
                        .select("*")\
                        .eq("user_id", user_id)\
                        .gte("created_at", f"{date}T00:00:00")\
                        .lte("created_at", f"{date}T23:59:59")\
                        .order("created_at")\
                        .execute()
                    data["symptom_tracking"].extend(symptoms_result.data or [])
        
        # Get specific deep dives
        if deep_dive_ids:
            dives_result = supabase.table("deep_dive_sessions")\
                .select("*")\
                .in_("id", deep_dive_ids)\
                .eq("user_id", user_id)\
                .eq("status", "completed")\
                .order("created_at")\
                .execute()
            data["deep_dives"] = dives_result.data or []
        
        # Get photo analyses for specific sessions
        if photo_session_ids:
            photo_result = supabase.table("photo_analyses")\
                .select("*")\
                .in_("session_id", photo_session_ids)\
                .order("created_at.desc")\
                .execute()
            data["photo_analyses"] = photo_result.data or []
        
        # Get any LLM summaries from the same dates
        all_dates = set()
        for scan in data["quick_scans"]:
            all_dates.add(scan["created_at"][:10])
        for dive in data["deep_dives"]:
            all_dates.add(dive["created_at"][:10])
            
        if all_dates:
            for date in all_dates:
                chat_result = supabase.table("oracle_chats")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .gte("created_at", f"{date}T00:00:00")\
                    .lte("created_at", f"{date}T23:59:59")\
                    .order("created_at")\
                    .execute()
                data["llm_summaries"].extend(chat_result.data or [])
        
        # Remove duplicates from symptom_tracking and llm_summaries
        seen_symptoms = set()
        unique_symptoms = []
        for symptom in data["symptom_tracking"]:
            symptom_id = symptom.get("id")
            if symptom_id and symptom_id not in seen_symptoms:
                seen_symptoms.add(symptom_id)
                unique_symptoms.append(symptom)
        data["symptom_tracking"] = unique_symptoms
        
        seen_chats = set()
        unique_chats = []
        for chat in data["llm_summaries"]:
            chat_id = chat.get("id")
            if chat_id and chat_id not in seen_chats:
                seen_chats.add(chat_id)
                unique_chats.append(chat)
        data["llm_summaries"] = unique_chats
        
    except Exception as e:
        print(f"Error in gather_selected_data: {e}")
        
    return data

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
        
        # Get story notes count
        notes_response = supabase.table("story_notes")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if notes_response.data:
            data["notes_count"] = len(notes_response.data)
        
    except Exception as e:
        print(f"Error gathering health data: {e}")
    
    return data


async def get_symptom_logs(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get symptom logs for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .gte("occurrence_date", start_date.isoformat())\
            .lte("occurrence_date", end_date.isoformat())\
            .order("occurrence_date", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting symptom logs: {e}")
        return []


async def get_sleep_data(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get sleep data for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get from symptom tracking where type is sleep-related
        response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .ilike("symptom_name", "%sleep%")\
            .gte("occurrence_date", start_date.isoformat())\
            .lte("occurrence_date", end_date.isoformat())\
            .order("occurrence_date", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting sleep data: {e}")
        return []


async def get_mood_data(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get mood data for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get mood-related symptoms
        response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .or_("symptom_name.ilike.%mood%,symptom_name.ilike.%anxiety%,symptom_name.ilike.%depression%")\
            .gte("occurrence_date", start_date.isoformat())\
            .lte("occurrence_date", end_date.isoformat())\
            .order("occurrence_date", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting mood data: {e}")
        return []


async def get_medication_logs(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get medication logs for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get medication-related tracking
        response = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .ilike("symptom_name", "%medication%")\
            .gte("occurrence_date", start_date.isoformat())\
            .lte("occurrence_date", end_date.isoformat())\
            .order("occurrence_date", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting medication logs: {e}")
        return []


async def get_quick_scan_history(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get quick scan history for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        response = supabase.table("quick_scans")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_date.isoformat())\
            .lte("created_at", end_date.isoformat())\
            .order("created_at", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting quick scan history: {e}")
        return []


async def get_deep_dive_sessions(user_id: str, days: int) -> List[Dict[str, Any]]:
    """Get deep dive sessions for specified number of days"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        response = supabase.table("deep_dive_sessions")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .gte("created_at", start_date.isoformat())\
            .lte("created_at", end_date.isoformat())\
            .order("created_at", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"Error getting deep dive sessions: {e}")
        return []


async def gather_prediction_data(user_id: str, prediction_type: str) -> Dict[str, Any]:
    """
    Gathers comprehensive data for AI predictions based on type
    
    Time windows:
    - immediate: 14 days of recent data
    - seasonal: 90 days to capture seasonal patterns
    - longterm: All available data for trajectory analysis
    - patterns: 90 days for pattern recognition
    - questions: 30 days for recent patterns
    """
    try:
        # Determine time window based on prediction type
        time_windows = {
            "immediate": 14,
            "seasonal": 90,
            "longterm": 365,  # 1 year or all data
            "patterns": 90,
            "questions": 30,
            "dashboard": 14
        }
        
        days = time_windows.get(prediction_type, 30)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Gather all data sources
        data = {
            "user_id": user_id,
            "prediction_type": prediction_type,
            "time_window": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "current_date": end_date.isoformat(),
            "day_of_week": end_date.strftime("%A"),
            "season": get_current_season(),
            "medical_profile": await get_user_medical_data(user_id)
        }
        
        # Get symptom logs with proper structure
        symptom_logs = await get_symptom_logs(user_id, days)
        data["symptom_tracking"] = {
            "total_entries": len(symptom_logs),
            "entries": symptom_logs,
            "symptom_frequency": calculate_symptom_frequency(symptom_logs),
            "severity_trends": calculate_severity_trends(symptom_logs)
        }
        
        # Get quick scans with analysis
        quick_scans = await get_quick_scan_history(user_id, days)
        data["quick_scans"] = {
            "total_scans": len(quick_scans),
            "scans": quick_scans,
            "body_part_frequency": calculate_body_part_frequency(quick_scans),
            "urgency_distribution": calculate_urgency_distribution(quick_scans)
        }
        
        # Get deep dive sessions
        deep_dives = await get_deep_dive_sessions(user_id, days)
        data["deep_dives"] = {
            "total_sessions": len(deep_dives),
            "completed_sessions": [d for d in deep_dives if d.get("status") == "completed"],
            "sessions": deep_dives
        }
        
        # Get sleep data
        sleep_data = await get_sleep_data(user_id, days)
        data["sleep_patterns"] = {
            "entries": sleep_data,
            "average_hours": calculate_average_sleep_hours(sleep_data),
            "quality_trend": calculate_sleep_quality_trend(sleep_data)
        }
        
        # Get mood data
        mood_data = await get_mood_data(user_id, days)
        data["mood_patterns"] = {
            "entries": mood_data,
            "average_mood": calculate_average_mood(mood_data),
            "stress_levels": extract_stress_levels(mood_data)
        }
        
        # Get medication data
        medication_logs = await get_medication_logs(user_id, days)
        data["medication_adherence"] = {
            "logs": medication_logs,
            "compliance_rate": calculate_medication_compliance(medication_logs)
        }
        
        # For long-term predictions, get additional historical data
        if prediction_type == "longterm":
            data["historical_patterns"] = await get_historical_patterns(user_id)
            data["chronic_conditions"] = await identify_chronic_conditions(user_id)
            data["risk_factors"] = await calculate_risk_factors(user_id)
        
        # For seasonal predictions, add season-specific data
        if prediction_type == "seasonal":
            data["seasonal_history"] = await get_seasonal_history(user_id)
            data["upcoming_season"] = get_upcoming_season()
            data["weather_sensitivity"] = await check_weather_sensitivity(user_id)
        
        # Calculate data quality score
        data["data_quality"] = calculate_data_quality_score(data)
        
        return data
        
    except Exception as e:
        print(f"Error gathering prediction data: {e}")
        return {
            "error": str(e),
            "user_id": user_id,
            "prediction_type": prediction_type
        }


def get_current_season() -> str:
    """Get the current season based on date"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"


def get_upcoming_season() -> Dict[str, str]:
    """Get the upcoming season and transition date"""
    now = datetime.now()
    year = now.year
    
    # Season transitions (approximate)
    transitions = {
        "spring": datetime(year, 3, 20),
        "summer": datetime(year, 6, 21),
        "fall": datetime(year, 9, 23),
        "winter": datetime(year, 12, 21)
    }
    
    # Find next transition
    for season, date in transitions.items():
        if now < date:
            return {
                "season": season,
                "transition_date": date.isoformat(),
                "days_until": (date - now).days
            }
    
    # If we're past winter, next is spring of next year
    return {
        "season": "spring",
        "transition_date": datetime(year + 1, 3, 20).isoformat(),
        "days_until": (datetime(year + 1, 3, 20) - now).days
    }


def calculate_symptom_frequency(symptom_logs: List[Dict]) -> Dict[str, int]:
    """Calculate frequency of each symptom"""
    frequency = {}
    for log in symptom_logs:
        symptom = log.get("symptom_name", "unknown")
        frequency[symptom] = frequency.get(symptom, 0) + 1
    return frequency


def calculate_severity_trends(symptom_logs: List[Dict]) -> Dict[str, Any]:
    """Calculate severity trends over time"""
    if not symptom_logs:
        return {"average": 0, "trend": "stable", "recent_average": 0}
    
    severities = [log.get("severity", 5) for log in symptom_logs if log.get("severity")]
    if not severities:
        return {"average": 0, "trend": "stable", "recent_average": 0}
    
    average = sum(severities) / len(severities)
    recent = severities[-7:] if len(severities) > 7 else severities
    recent_avg = sum(recent) / len(recent)
    
    trend = "increasing" if recent_avg > average + 0.5 else "decreasing" if recent_avg < average - 0.5 else "stable"
    
    return {
        "average": round(average, 1),
        "trend": trend,
        "recent_average": round(recent_avg, 1),
        "max_severity": max(severities),
        "min_severity": min(severities)
    }


def calculate_body_part_frequency(quick_scans: List[Dict]) -> Dict[str, int]:
    """Calculate frequency of body parts in quick scans"""
    frequency = {}
    for scan in quick_scans:
        body_part = scan.get("body_part", "unknown")
        frequency[body_part] = frequency.get(body_part, 0) + 1
    return frequency


def calculate_urgency_distribution(quick_scans: List[Dict]) -> Dict[str, int]:
    """Calculate distribution of urgency levels"""
    distribution = {"low": 0, "medium": 0, "high": 0}
    for scan in quick_scans:
        urgency = scan.get("urgency_level", "low")
        if urgency in distribution:
            distribution[urgency] += 1
    return distribution


def calculate_average_sleep_hours(sleep_data: List[Dict]) -> float:
    """Calculate average sleep hours"""
    if not sleep_data:
        return 0
    
    total_hours = 0
    count = 0
    
    for entry in sleep_data:
        # Try to extract hours from various possible fields
        hours = entry.get("hours", 0) or entry.get("duration", 0) or 0
        if hours > 0:
            total_hours += hours
            count += 1
    
    return round(total_hours / count, 1) if count > 0 else 0


def calculate_sleep_quality_trend(sleep_data: List[Dict]) -> str:
    """Determine sleep quality trend"""
    if not sleep_data:
        return "unknown"
    
    # Extract quality scores
    qualities = []
    for entry in sleep_data:
        quality = entry.get("quality") or entry.get("severity")
        if quality:
            qualities.append(quality)
    
    if not qualities:
        return "unknown"
    
    # Compare recent to overall
    recent = qualities[-7:] if len(qualities) > 7 else qualities
    avg_quality = sum(qualities) / len(qualities)
    recent_avg = sum(recent) / len(recent)
    
    if recent_avg > avg_quality + 0.5:
        return "improving"
    elif recent_avg < avg_quality - 0.5:
        return "declining"
    else:
        return "stable"


def calculate_average_mood(mood_data: List[Dict]) -> float:
    """Calculate average mood score"""
    if not mood_data:
        return 5.0
    
    moods = []
    for entry in mood_data:
        # Try various fields that might contain mood data
        mood = entry.get("mood_score") or entry.get("severity") or entry.get("value")
        if mood:
            moods.append(mood)
    
    return round(sum(moods) / len(moods), 1) if moods else 5.0


def extract_stress_levels(mood_data: List[Dict]) -> List[int]:
    """Extract stress levels from mood data"""
    stress_levels = []
    for entry in mood_data:
        # Look for stress-related entries
        if "stress" in entry.get("symptom_name", "").lower():
            level = entry.get("severity") or entry.get("value") or 5
            stress_levels.append(level)
    return stress_levels


def calculate_medication_compliance(medication_logs: List[Dict]) -> float:
    """Calculate medication compliance percentage"""
    if not medication_logs:
        return 100.0
    
    taken = sum(1 for log in medication_logs if log.get("taken", True))
    return round((taken / len(medication_logs)) * 100, 1)


async def get_historical_patterns(user_id: str) -> Dict[str, Any]:
    """Get historical health patterns for long-term analysis"""
    try:
        # Get all symptom tracking data
        all_symptoms = supabase.table("symptom_tracking")\
            .select("*")\
            .eq("user_id", str(user_id))\
            .order("occurrence_date", desc=False)\
            .execute()
        
        if not all_symptoms.data:
            return {}
        
        # Analyze patterns
        patterns = {
            "total_tracked_days": len(set(s["occurrence_date"] for s in all_symptoms.data)),
            "most_common_symptoms": {},
            "seasonal_patterns": {},
            "chronic_symptoms": []
        }
        
        # Count symptom occurrences
        symptom_counts = {}
        for symptom in all_symptoms.data:
            name = symptom.get("symptom_name", "unknown")
            symptom_counts[name] = symptom_counts.get(name, 0) + 1
        
        # Find chronic symptoms (appearing more than 10 times)
        patterns["chronic_symptoms"] = [s for s, count in symptom_counts.items() if count > 10]
        patterns["most_common_symptoms"] = dict(sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        
        return patterns
        
    except Exception as e:
        print(f"Error getting historical patterns: {e}")
        return {}


async def identify_chronic_conditions(user_id: str) -> List[str]:
    """Identify potential chronic conditions based on patterns"""
    patterns = await get_historical_patterns(user_id)
    chronic_symptoms = patterns.get("chronic_symptoms", [])
    
    conditions = []
    
    # Simple pattern matching for common chronic conditions
    if any("migraine" in s.lower() or "headache" in s.lower() for s in chronic_symptoms):
        conditions.append("chronic_migraines")
    
    if any("anxiety" in s.lower() or "stress" in s.lower() for s in chronic_symptoms):
        conditions.append("anxiety_disorder")
    
    if any("sleep" in s.lower() or "insomnia" in s.lower() for s in chronic_symptoms):
        conditions.append("sleep_disorder")
    
    return conditions


async def calculate_risk_factors(user_id: str) -> Dict[str, Any]:
    """Calculate health risk factors based on medical profile and patterns"""
    medical_data = await get_user_medical_data(user_id)
    
    risk_factors = {
        "cardiovascular": [],
        "metabolic": [],
        "mental_health": []
    }
    
    if medical_data:
        # Check family history
        family_history = medical_data.get("family_history", [])
        if isinstance(family_history, list):
            for condition in family_history:
                if "heart" in str(condition).lower() or "cardiac" in str(condition).lower():
                    risk_factors["cardiovascular"].append("family_history")
                if "diabetes" in str(condition).lower():
                    risk_factors["metabolic"].append("family_history")
        
        # Check lifestyle factors
        if medical_data.get("lifestyle_smoking_status") == "current":
            risk_factors["cardiovascular"].append("smoking")
        
        if medical_data.get("lifestyle_exercise_frequency") in ["never", "rarely"]:
            risk_factors["cardiovascular"].append("sedentary_lifestyle")
            risk_factors["metabolic"].append("sedentary_lifestyle")
        
        if medical_data.get("lifestyle_stress_level") in ["high", "very_high"]:
            risk_factors["mental_health"].append("chronic_stress")
            risk_factors["cardiovascular"].append("chronic_stress")
    
    return risk_factors


async def get_seasonal_history(user_id: str) -> Dict[str, List[str]]:
    """Get historical symptoms by season"""
    try:
        # Get all symptom data
        all_symptoms = supabase.table("symptom_tracking")\
            .select("symptom_name, occurrence_date")\
            .eq("user_id", str(user_id))\
            .execute()
        
        seasonal_symptoms = {
            "winter": [],
            "spring": [],
            "summer": [],
            "fall": []
        }
        
        for symptom in all_symptoms.data:
            date = datetime.fromisoformat(symptom["occurrence_date"])
            month = date.month
            
            if month in [12, 1, 2]:
                season = "winter"
            elif month in [3, 4, 5]:
                season = "spring"
            elif month in [6, 7, 8]:
                season = "summer"
            else:
                season = "fall"
            
            seasonal_symptoms[season].append(symptom["symptom_name"])
        
        # Count frequencies
        for season in seasonal_symptoms:
            symptom_counts = {}
            for symptom in seasonal_symptoms[season]:
                symptom_counts[symptom] = symptom_counts.get(symptom, 0) + 1
            # Keep top 5 symptoms per season
            seasonal_symptoms[season] = [s for s, _ in sorted(symptom_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
        
        return seasonal_symptoms
        
    except Exception as e:
        print(f"Error getting seasonal history: {e}")
        return {"winter": [], "spring": [], "summer": [], "fall": []}


async def check_weather_sensitivity(user_id: str) -> Dict[str, Any]:
    """Check for weather-related symptom patterns"""
    # This is a simplified version - in production you might correlate with actual weather data
    weather_keywords = ["pressure", "weather", "storm", "rain", "humidity", "temperature"]
    
    try:
        symptoms = supabase.table("symptom_tracking")\
            .select("symptom_name, notes")\
            .eq("user_id", str(user_id))\
            .execute()
        
        weather_related = 0
        total = len(symptoms.data)
        
        for symptom in symptoms.data:
            text = f"{symptom.get('symptom_name', '')} {symptom.get('notes', '')}".lower()
            if any(keyword in text for keyword in weather_keywords):
                weather_related += 1
        
        sensitivity_score = (weather_related / total * 100) if total > 0 else 0
        
        return {
            "is_sensitive": sensitivity_score > 10,
            "sensitivity_score": round(sensitivity_score, 1),
            "weather_related_symptoms": weather_related
        }
        
    except Exception as e:
        print(f"Error checking weather sensitivity: {e}")
        return {"is_sensitive": False, "sensitivity_score": 0, "weather_related_symptoms": 0}


def calculate_data_quality_score(data: Dict[str, Any]) -> int:
    """Calculate data quality score 0-100"""
    score = 0
    
    # Check various data sources
    if data.get("symptom_tracking", {}).get("total_entries", 0) >= 10:
        score += 20
    
    if data.get("quick_scans", {}).get("total_scans", 0) >= 5:
        score += 20
    
    if data.get("deep_dives", {}).get("completed_sessions"):
        score += 15
    
    if data.get("sleep_patterns", {}).get("average_hours", 0) > 0:
        score += 15
    
    if data.get("mood_patterns", {}).get("entries"):
        score += 15
    
    if data.get("medication_adherence", {}).get("compliance_rate", 100) < 100:
        score += 15  # They're tracking medications
    
    return min(score, 100)
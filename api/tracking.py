"""Tracking API endpoints"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import uuid

from models.requests import (
    TrackingSuggestRequest,
    TrackingConfigureRequest,
    TrackingDataPointRequest
)
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response

router = APIRouter(prefix="/api/tracking", tags=["tracking"])

@router.post("/suggest")
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

@router.post("/configure")
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

@router.post("/approve/{suggestion_id}")
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

@router.post("/data")
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

@router.get("/dashboard")
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

@router.get("/chart/{config_id}")
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
            "labels": [dp["recorded_at"][:10] for dp in data_points],  # Date only
            "datasets": [{
                "label": config["metric_name"],
                "data": [dp["value"] for dp in data_points],
                "backgroundColor": config.get("color", "#3B82F6") + "20",  # 20% opacity
                "borderColor": config.get("color", "#3B82F6"),
                "fill": True
            }]
        }
        
        # Calculate statistics
        values = [dp["value"] for dp in data_points]
        stats = {
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "avg": sum(values) / len(values) if values else None,
            "count": len(values)
        }
        
        return {
            "configuration": config,
            "chart_data": chart_data,
            "statistics": stats,
            "data_points": data_points,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching chart data: {e}")
        return {"error": str(e), "status": "error"}

@router.get("/configurations")
async def get_tracking_configurations(user_id: str):
    """Get all tracking configurations for a user"""
    try:
        response = supabase.table("tracking_configurations")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {
            "configurations": response.data or [],
            "total": len(response.data or []),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching configurations: {e}")
        return {"error": str(e), "status": "error"}

@router.get("/data-points/{config_id}")
async def get_tracking_data_points(config_id: str, limit: int = 100):
    """Get data points for a specific configuration"""
    try:
        response = supabase.table("tracking_data_points")\
            .select("*")\
            .eq("configuration_id", config_id)\
            .order("recorded_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return {
            "data_points": response.data or [],
            "total": len(response.data or []),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error fetching data points: {e}")
        return {"error": str(e), "status": "error"}

@router.get("/past-scans")
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

@router.get("/past-dives")
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
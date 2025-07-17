"""Population Health API endpoints"""
from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Optional

from supabase_client import supabase

router = APIRouter(prefix="/api", tags=["population-health"])

@router.get("/population-health/alerts")
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

@router.get("/reports")
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

@router.post("/reports/{report_id}/access")
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

@router.get("/reports/{report_id}")
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
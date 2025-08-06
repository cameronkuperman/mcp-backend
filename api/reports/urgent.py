"""Urgent Report API endpoints"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import json
import uuid

from models.requests import UrgentTriageRequest
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import gather_report_data, safe_insert_report

router = APIRouter(prefix="/api/report", tags=["reports-urgent"])

@router.post("/urgent-triage")
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
            model="google/gemini-2.5-flash",
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
            "model_used": "google/gemini-2.5-flash"
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
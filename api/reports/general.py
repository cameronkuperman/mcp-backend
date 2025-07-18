"""General Report API endpoints"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
import json
import uuid

from models.requests import (
    ReportAnalyzeRequest,
    ComprehensiveReportRequest,
    SymptomTimelineRequest,
    PhotoProgressionRequest,
    DoctorNotesRequest,
    ShareReportRequest,
    RateReportRequest
)
from supabase_client import supabase
from business_logic import call_llm
from utils.json_parser import extract_json_from_response
from utils.data_gathering import (
    gather_report_data,
    safe_insert_report,
    has_emergency_indicators,
    determine_time_range
)

router = APIRouter(prefix="/api/report", tags=["reports-general"])

@router.get("/list/{user_id}")
async def list_user_reports(user_id: str):
    """List all reports for a user"""
    try:
        # Get reports from last 90 days by default
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        
        response = supabase.table("medical_reports")\
            .select("*")\
            .eq("user_id", user_id)\
            .gte("created_at", cutoff_date)\
            .order("created_at", desc=True)\
            .execute()
        
        reports = response.data or []
        
        # Ensure report_data is properly formatted
        for report in reports:
            # report_data is already a dict from JSONB, no need to parse
            if report.get("report_data") and isinstance(report["report_data"], dict):
                # Ensure all expected fields exist
                report_data = report["report_data"]
                if "executive_summary" not in report_data:
                    report_data["executive_summary"] = {
                        "one_page_summary": report.get("executive_summary", "No summary available"),
                        "chief_complaints": [],
                        "key_findings": [],
                        "urgency_indicators": [],
                        "action_items": []
                    }
            else:
                # Create minimal structure if report_data is missing
                report["report_data"] = {
                    "executive_summary": {
                        "one_page_summary": report.get("executive_summary", "Report data unavailable"),
                        "chief_complaints": [],
                        "key_findings": ["Report data needs to be regenerated"],
                        "urgency_indicators": [],
                        "action_items": ["Contact support if this persists"]
                    }
                }
        
        return {
            "reports": reports,
            "count": len(reports),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error listing reports: {e}")
        return {"error": str(e), "reports": [], "status": "error"}

@router.get("/{report_id}")
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
        
        # Ensure report_data is properly formatted
        if report.get("report_data") and isinstance(report["report_data"], dict):
            # Ensure all expected fields exist
            report_data = report["report_data"]
            if "executive_summary" not in report_data:
                report_data["executive_summary"] = {
                    "one_page_summary": report.get("executive_summary", "No summary available"),
                    "chief_complaints": [],
                    "key_findings": [],
                    "urgency_indicators": [],
                    "action_items": []
                }
        else:
            # Create minimal structure if report_data is missing
            report["report_data"] = {
                "executive_summary": {
                    "one_page_summary": report.get("executive_summary", "Report data unavailable"),
                    "chief_complaints": [],
                    "key_findings": ["Report data needs to be regenerated"],
                    "urgency_indicators": [],
                    "action_items": ["Contact support if this persists"]
                }
            }
        
        # Update access tracking
        supabase.table("medical_reports")\
            .update({"last_accessed": datetime.now(timezone.utc).isoformat()})\
            .eq("id", report_id)\
            .execute()
        
        return {
            "report": report,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error getting report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/analyze")
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

@router.post("/comprehensive")
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

@router.post("/symptom-timeline")
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

@router.post("/photo-progression")
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
        
        # Note: This is a placeholder as photo analysis would require additional setup
        # In production, this would integrate with image analysis APIs
        
        report_data = {
            "executive_summary": {
                "one_page_summary": "Photo progression analysis tracks visual changes over time.",
                "key_findings": ["Visual tracking helps identify subtle changes"],
                "recommendations": ["Continue photo documentation", "Compare photos at regular intervals"]
            },
            "photo_analysis": {
                "total_photos": 0,
                "date_range": config.get("time_range", {}),
                "changes_identified": [],
                "progression_rate": "Unable to determine without photos"
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
            "confidence_score": 70,
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

@router.put("/{report_id}/doctor-notes")
async def add_doctor_notes(report_id: str, request: DoctorNotesRequest):
    """Allow doctors to add notes to a report"""
    try:
        # Verify report exists
        report_response = supabase.table("medical_reports").select("*").eq("id", report_id).execute()
        if not report_response.data:
            return {"error": "Report not found", "status": "error"}
        
        # Add doctor notes
        doctor_note = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "doctor_npi": request.doctor_npi,
            "specialty": request.specialty,
            "notes": request.notes,
            "sections_reviewed": request.sections_reviewed,
            "diagnosis": request.diagnosis,
            "plan_modifications": request.plan_modifications,
            "follow_up_instructions": request.follow_up_instructions,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("doctor_notes").insert(doctor_note).execute()
        
        # Update report to indicate doctor review
        supabase.table("medical_reports").update({
            "doctor_reviewed": True,
            "last_doctor_review": datetime.now(timezone.utc).isoformat(),
            "reviewing_doctor_npi": request.doctor_npi
        }).eq("id", report_id).execute()
        
        return {
            "note_id": doctor_note["id"],
            "report_id": report_id,
            "status": "success",
            "message": "Doctor notes added successfully"
        }
        
    except Exception as e:
        print(f"Error adding doctor notes: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/{report_id}/share")
async def share_report(report_id: str, request: ShareReportRequest):
    """Share report with another healthcare provider"""
    try:
        # Verify report exists
        report_response = supabase.table("medical_reports").select("user_id").eq("id", report_id).execute()
        if not report_response.data:
            return {"error": "Report not found", "status": "error"}
        
        # Create share record
        share_id = str(uuid.uuid4())
        expiration_date = datetime.now(timezone.utc) + timedelta(days=request.expiration_days)
        
        share_record = {
            "id": share_id,
            "report_id": report_id,
            "shared_by_npi": request.shared_by_npi,
            "recipient_npi": request.recipient_npi,
            "access_level": request.access_level,
            "expiration_date": expiration_date.isoformat(),
            "notes": request.notes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "accessed": False
        }
        
        supabase.table("report_shares").insert(share_record).execute()
        
        # Generate share link
        share_link = f"{request.base_url}/shared-report/{share_id}"
        
        return {
            "share_id": share_id,
            "share_link": share_link,
            "expiration_date": expiration_date.isoformat(),
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error sharing report: {e}")
        return {"error": str(e), "status": "error"}

@router.post("/{report_id}/rate")
async def rate_report(report_id: str, request: RateReportRequest):
    """Allow doctors to rate report usefulness"""
    try:
        # Save rating
        rating_record = {
            "id": str(uuid.uuid4()),
            "report_id": report_id,
            "doctor_npi": request.doctor_npi,
            "usefulness_score": request.usefulness_score,
            "accuracy_score": request.accuracy_score,
            "time_saved": request.time_saved,
            "would_recommend": request.would_recommend,
            "feedback": request.feedback,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table("report_ratings").insert(rating_record).execute()
        
        # Update report's average rating
        all_ratings = supabase.table("report_ratings")\
            .select("usefulness_score, accuracy_score")\
            .eq("report_id", report_id)\
            .execute()
        
        if all_ratings.data:
            avg_usefulness = sum(r["usefulness_score"] for r in all_ratings.data) / len(all_ratings.data)
            avg_accuracy = sum(r["accuracy_score"] for r in all_ratings.data) / len(all_ratings.data)
            
            supabase.table("medical_reports").update({
                "average_rating": (avg_usefulness + avg_accuracy) / 2,
                "rating_count": len(all_ratings.data)
            }).eq("id", report_id).execute()
        
        return {
            "rating_id": rating_record["id"],
            "report_id": report_id,
            "status": "success",
            "message": "Thank you for rating this report"
        }
        
    except Exception as e:
        print(f"Error rating report: {e}")
        return {"error": str(e), "status": "error"}
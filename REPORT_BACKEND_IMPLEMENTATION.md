# Report Generation Backend Implementation

Add these endpoints to `run_oracle.py` following existing patterns.

## 1. Add Request/Response Models

```python
# Add to imports
from typing import List, Dict, Optional, Literal
from datetime import datetime, timezone, timedelta

# Add these Pydantic models after existing models

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
```

## 2. Helper Functions

```python
# Add these helper functions

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
```

## 3. Report Analysis Endpoint

```python
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
```

## 4. Comprehensive Report Endpoint

```python
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
        
        supabase.table("medical_reports").insert(report_record).execute()
        
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
```

## 5. Urgent Triage Report Endpoint

```python
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
        
        supabase.table("medical_reports").insert(report_record).execute()
        
        return {
            "report_id": report_id,
            "report_type": "urgent_triage",
            "triage_summary": triage_summary,
            "status": "success"
        }
        
    except Exception as e:
        print(f"Error generating urgent triage: {e}")
        return {"error": str(e), "status": "error"}
```

## 6. Add Remaining Endpoints

Follow the same pattern for:
- `/api/report/photo-progression`
- `/api/report/symptom-timeline`
- `/api/report/specialist`
- `/api/report/annual-summary`

Each follows the same structure:
1. Load analysis from database
2. Gather relevant data based on report type
3. Create specialized prompt for that report type
4. Call LLM with appropriate model
5. Parse response with `extract_json_from_response`
6. Save to medical_reports table
7. Return formatted response

## 7. Update Root Endpoint

```python
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
                "annual_summary": "POST /api/report/annual-summary"
            }
        }
    }
```

## Testing

```bash
# Test report analysis
curl -X POST http://localhost:8000/api/report/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-id",
    "context": {
      "purpose": "symptom_specific",
      "symptom_focus": "recurring headaches"
    }
  }'

# Then use the recommended endpoint with analysis_id
curl -X POST http://localhost:8000/api/report/comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "returned-analysis-id",
    "user_id": "test-user-id"
  }'
```
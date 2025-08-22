"""
Master Timeline Module - Chronological health event aggregation
Combines all health data sources into a unified timeline
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from supabase_client import supabase
from business_logic import call_llm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence/timeline", tags=["timeline"])

class TimelineDataPoint(BaseModel):
    date: str
    severity: int  # 0-10
    symptom: str
    notes: Optional[str] = None

class AIConsultation(BaseModel):
    id: str
    date: str
    type: str  # 'quick_scan' | 'deep_dive'
    bodyPart: str
    severity: str

class PhotoSession(BaseModel):
    id: str
    date: str
    photoCount: int
    improvement: Optional[float] = None
    bodyPart: str

class DoctorRecommendation(BaseModel):
    date: str
    urgency: str  # 'low' | 'medium' | 'high'
    reason: str

class TimelineResponse(BaseModel):
    timeRange: str
    dataPoints: List[TimelineDataPoint]
    aiConsultations: List[AIConsultation]
    photoSessions: List[PhotoSession]
    doctorRecommendations: List[DoctorRecommendation]

@router.get("/{user_id}")
async def get_master_timeline(user_id: str, time_range: str = "30D"):
    """
    Get comprehensive health timeline with all events
    """
    try:
        logger.info(f"Generating master timeline for user {user_id}, range: {time_range}")
        
        # Parse time range
        range_map = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365, "ALL": 3650}
        days = range_map.get(time_range, 30)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days) if time_range != "ALL" else datetime(2020, 1, 1)
        
        # Fetch symptom tracking data
        symptoms = supabase.table("symptom_tracking").select("*").eq(
            "user_id", user_id
        ).gte("recorded_at", start_date.isoformat()).order("recorded_at", desc=False).execute()
        
        # Fetch AI consultations (oracle chats)
        chats = supabase.table("oracle_chats").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).order("created_at", desc=False).execute()
        
        # Fetch quick scans
        scans = supabase.table("quick_scans").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).order("created_at", desc=False).execute()
        
        # Fetch deep dive sessions
        deep_dives = supabase.table("deep_dive_sessions").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).order("created_at", desc=False).execute()
        
        # Fetch photo analysis sessions
        photos = supabase.table("photo_analysis_sessions").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).order("created_at", desc=False).execute()
        
        # Process symptom data points with LLM enhancement
        data_points = []
        for symptom in (symptoms.data or []):
            data_points.append(TimelineDataPoint(
                date=symptom.get('recorded_at', ''),
                severity=symptom.get('severity', 5),
                symptom=symptom.get('symptom_name', 'Unknown symptom'),
                notes=symptom.get('notes')
            ))
        
        # Process AI consultations
        ai_consultations = []
        
        # Add quick scans
        for scan in (scans.data or []):
            ai_consultations.append(AIConsultation(
                id=scan.get('id', ''),
                date=scan.get('created_at', ''),
                type='quick_scan',
                bodyPart=scan.get('body_part', 'general'),
                severity=scan.get('urgency_level', 'medium')
            ))
        
        # Add deep dives
        for dive in (deep_dives.data or []):
            ai_consultations.append(AIConsultation(
                id=dive.get('id', ''),
                date=dive.get('created_at', ''),
                type='deep_dive',
                bodyPart=dive.get('body_part', 'general'),
                severity=dive.get('final_analysis', {}).get('urgency', 'medium')
            ))
        
        # Process photo sessions
        photo_sessions = []
        for photo in (photos.data or []):
            photo_sessions.append(PhotoSession(
                id=photo.get('id', ''),
                date=photo.get('created_at', ''),
                photoCount=len(photo.get('photo_urls', [])),
                improvement=photo.get('improvement_score'),
                bodyPart=photo.get('body_part', 'general')
            ))
        
        # Generate doctor recommendations using LLM based on data
        doctor_recommendations = await generate_doctor_recommendations(
            user_id, symptoms.data, scans.data, deep_dives.data
        )
        
        response = TimelineResponse(
            timeRange=time_range,
            dataPoints=data_points,
            aiConsultations=ai_consultations,
            photoSessions=photo_sessions,
            doctorRecommendations=doctor_recommendations
        )
        
        logger.info(f"Generated timeline with {len(data_points)} data points, {len(ai_consultations)} consultations")
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate timeline: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate timeline: {str(e)}")

async def generate_doctor_recommendations(user_id: str, symptoms: List, scans: List, deep_dives: List) -> List[DoctorRecommendation]:
    """
    Use LLM to generate doctor visit recommendations based on health data
    """
    if not symptoms and not scans and not deep_dives:
        return []
    
    # Prepare context for LLM
    context = "Recent health data:\n"
    
    if symptoms:
        recent_symptoms = symptoms[-10:]  # Last 10 symptoms
        context += "Symptoms:\n"
        for s in recent_symptoms:
            context += f"- {s.get('symptom_name')}: severity {s.get('severity')}/10\n"
    
    if scans:
        recent_scans = scans[-5:]  # Last 5 scans
        context += "\nQuick Scans:\n"
        for s in recent_scans:
            context += f"- {s.get('body_part')}: {s.get('urgency_level')} urgency\n"
    
    if deep_dives:
        recent_dives = deep_dives[-3:]  # Last 3 deep dives
        context += "\nDeep Dive Results:\n"
        for d in recent_dives:
            analysis = d.get('final_analysis', {})
            context += f"- {d.get('body_part')}: {analysis.get('urgency', 'unknown')} urgency\n"
    
    # Generate recommendations using LLM
    system_prompt = """You are a medical triage advisor. Based on health data, recommend if/when to see a doctor.

Return ONLY a JSON array of recommendations.
Only recommend doctor visits for concerning patterns.
Be conservative - don't over-recommend visits."""

    user_prompt = f"""{context}

Based on this data, generate doctor visit recommendations.
Return JSON array with this structure:
[
  {{
    "date": "YYYY-MM-DD",
    "urgency": "low|medium|high",
    "reason": "Brief reason for recommendation"
  }}
]

Only include recommendations if there are concerning symptoms.
Maximum 3 recommendations."""

    try:
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-5-mini",
            user_id=user_id,
            temperature=0.3,
            max_tokens=512
        )
        
        # Parse response
        if isinstance(llm_response.get("content"), list):
            recommendations_data = llm_response["content"]
        else:
            content = llm_response.get("raw_content", llm_response.get("content", ""))
            # Extract JSON array
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx != -1 and end_idx > start_idx:
                import json
                recommendations_data = json.loads(content[start_idx:end_idx])
            else:
                return []
        
        # Convert to response objects
        recommendations = []
        for rec in recommendations_data[:3]:  # Max 3
            if isinstance(rec, dict):
                recommendations.append(DoctorRecommendation(
                    date=rec.get('date', datetime.now().strftime('%Y-%m-%d')),
                    urgency=rec.get('urgency', 'low'),
                    reason=rec.get('reason', 'Regular checkup recommended')
                ))
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Failed to generate doctor recommendations: {e}")
        return []
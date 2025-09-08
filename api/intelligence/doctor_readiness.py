"""
Doctor Readiness Score Module - LLM-based assessment of medical visit preparedness
Evaluates data completeness and generates readiness score
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pydantic import BaseModel
import logging

from supabase_client import supabase
from business_logic import call_llm
from utils.data_gathering import gather_user_health_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence/doctor-readiness", tags=["doctor_readiness"])

class DoctorReadinessResponse(BaseModel):
    score: int  # 0-100
    missingData: List[str]
    availableData: Dict[str, bool]
    reportSections: List[str]

@router.get("/{user_id}")
async def get_doctor_readiness_score(user_id: str):
    """
    Generate Doctor Readiness Score using LLM analysis
    Assesses how prepared the user is for a medical consultation
    """
    try:
        logger.info(f"Generating doctor readiness score for user {user_id}")
        
        # Check data availability across all sources
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Check symptoms
        symptoms = supabase.table("symptom_tracking").select("id").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).limit(1).execute()
        has_symptoms = bool(symptoms.data)
        
        # Check timeline (oracle chats)
        chats = supabase.table("conversations").select("id").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).limit(1).execute()
        has_timeline = bool(chats.data)
        
        # Check patterns (insights)
        insights = supabase.table("health_insights").select("id").eq(
            "user_id", user_id
        ).limit(1).execute()
        has_patterns = bool(insights.data)
        
        # Check photos
        photos = supabase.table("photo_analysis_sessions").select("id").eq(
            "user_id", user_id
        ).limit(1).execute()
        has_photos = bool(photos.data)
        
        # Check AI analysis (quick scans + deep dives)
        scans = supabase.table("quick_scans").select("id").eq(
            "user_id", user_id
        ).limit(1).execute()
        deep_dives = supabase.table("deep_dive_sessions").select("id").eq(
            "user_id", user_id
        ).limit(1).execute()
        has_ai_analysis = bool(scans.data or deep_dives.data)
        
        # Check medications (from medical profile)
        medical = supabase.table("medical").select("medications").eq(
            "id", user_id
        ).execute()
        has_medications = bool(medical.data and medical.data[0].get('medications'))
        
        # Check vitals (if tracked)
        vitals = supabase.table("vitals").select("id").eq(
            "user_id", user_id
        ).limit(1).execute() if False else None  # Vitals table might not exist
        has_vitals = bool(vitals and vitals.data) if vitals else False
        
        # Gather comprehensive data for LLM analysis
        health_data = await gather_user_health_data(user_id)
        
        # Prepare LLM prompt
        system_prompt = """You are a medical consultation preparedness analyst. 
Evaluate how ready a patient is to have a productive doctor's visit based on their health data.

Generate a readiness score and identify what information would help the consultation.

Consider these factors for scoring:
- Symptom documentation (25 points max)
- Timeline/history (20 points max)  
- Identified patterns (15 points max)
- Photo evidence (10 points max)
- Medications list (15 points max)
- Vitals data (10 points max)
- AI consultations (5 points max)

Return ONLY valid JSON with exact structure."""

        user_prompt = f"""Evaluate doctor visit readiness based on this data availability:

AVAILABLE DATA:
- Symptoms tracked: {has_symptoms} (30 days of data)
- Health timeline: {has_timeline} (consultation history)
- Patterns identified: {has_patterns} (AI-generated insights)
- Photos documented: {has_photos}
- AI analysis done: {has_ai_analysis} (quick scans/deep dives)
- Medications listed: {has_medications}
- Vitals tracked: {has_vitals}

HEALTH DATA SUMMARY:
{str(health_data)[:2000]}

Generate readiness assessment with this EXACT JSON structure:
{{
  "score": [0-100 based on data completeness and quality],
  "missingData": [
    "List of missing data types that would help",
    "Maximum 5 items",
    "Be specific about what's needed"
  ],
  "availableData": {{
    "symptoms": {str(has_symptoms).lower()},
    "timeline": {str(has_timeline).lower()},
    "patterns": {str(has_patterns).lower()},
    "photos": {str(has_photos).lower()},
    "aiAnalysis": {str(has_ai_analysis).lower()},
    "medications": {str(has_medications).lower()},
    "vitals": {str(has_vitals).lower()}
  }},
  "reportSections": [
    "List sections that can be generated for doctor",
    "Based on available data",
    "E.g., 'Symptom Timeline', 'Pattern Analysis', 'Medication History'"
  ]
}}

Score interpretation:
- 80-100: Excellent preparation, comprehensive data
- 60-79: Good preparation, most key data available
- 40-59: Fair preparation, some important data missing
- 20-39: Poor preparation, significant gaps
- 0-19: Minimal data, need to track more"""

        # Call LLM for analysis
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-5-mini",
            user_id=user_id,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response
        if isinstance(llm_response.get("content"), dict):
            readiness_data = llm_response["content"]
        else:
            # Extract JSON from string
            import json
            content = llm_response.get("raw_content", llm_response.get("content", ""))
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                readiness_data = json.loads(json_str)
            else:
                # Fallback calculation if LLM fails
                base_score = 0
                if has_symptoms: base_score += 25
                if has_timeline: base_score += 20
                if has_patterns: base_score += 15
                if has_photos: base_score += 10
                if has_medications: base_score += 15
                if has_vitals: base_score += 10
                if has_ai_analysis: base_score += 5
                
                readiness_data = {
                    'score': base_score,
                    'missingData': [],
                    'availableData': {
                        'symptoms': has_symptoms,
                        'timeline': has_timeline,
                        'patterns': has_patterns,
                        'photos': has_photos,
                        'aiAnalysis': has_ai_analysis,
                        'medications': has_medications,
                        'vitals': has_vitals
                    },
                    'reportSections': []
                }
                
                # Add missing data items
                if not has_symptoms: readiness_data['missingData'].append('Symptom tracking data')
                if not has_timeline: readiness_data['missingData'].append('Health consultation history')
                if not has_medications: readiness_data['missingData'].append('Current medications list')
                if not has_patterns: readiness_data['missingData'].append('Pattern analysis insights')
                if not has_vitals: readiness_data['missingData'].append('Vital signs data')
                
                # Add report sections
                if has_symptoms: readiness_data['reportSections'].append('Symptom Timeline')
                if has_patterns: readiness_data['reportSections'].append('Pattern Analysis')
                if has_medications: readiness_data['reportSections'].append('Medication History')
                if has_ai_analysis: readiness_data['reportSections'].append('AI Health Assessment')
        
        # Create response
        response = DoctorReadinessResponse(
            score=max(0, min(100, int(readiness_data.get('score', 50)))),
            missingData=readiness_data.get('missingData', [])[:5],
            availableData=readiness_data.get('availableData', {}),
            reportSections=readiness_data.get('reportSections', [])
        )
        
        logger.info(f"Generated doctor readiness score: {response.score}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate doctor readiness: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate doctor readiness: {str(e)}")
"""
Body Systems Health Module - LLM-based system health evaluation
Analyzes health of different body systems from first principles
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pydantic import BaseModel
import logging
import json

from supabase_client import supabase
from business_logic import call_llm
from utils.data_gathering import gather_user_health_data

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence/body-systems", tags=["body_systems"])

class SystemHealth(BaseModel):
    health: int  # 0-100
    issues: List[str]
    trend: str  # 'improving' | 'declining' | 'stable'
    lastUpdated: str

class BodySystemsResponse(BaseModel):
    head: SystemHealth
    chest: SystemHealth
    digestive: SystemHealth
    arms: SystemHealth
    legs: SystemHealth
    skin: SystemHealth
    mental: SystemHealth

@router.get("/{user_id}")
async def get_body_systems_health(user_id: str):
    """
    Generate Body Systems Health scores using LLM analysis
    Evaluates each body system's health from symptom patterns
    """
    try:
        logger.info(f"Generating body systems health for user {user_id}")
        
        # Gather comprehensive health data
        health_data = await gather_user_health_data(user_id)
        
        # Get recent symptoms and consultations
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Fetch symptom tracking data
        symptoms = supabase.table("symptom_tracking").select("*").eq(
            "user_id", user_id
        ).gte("recorded_at", start_date.isoformat()).execute()
        
        # Fetch recent consultations
        consultations = supabase.table("oracle_chats").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).limit(20).execute()
        
        # Fetch quick scans
        scans = supabase.table("quick_scans").select("*").eq(
            "user_id", user_id
        ).gte("created_at", start_date.isoformat()).execute()
        
        # Check if user has any data
        has_data = bool(symptoms.data or consultations.data or scans.data)
        
        if not has_data:
            # Return default healthy state if no data
            default_system = SystemHealth(
                health=75,
                issues=[],
                trend="stable",
                lastUpdated=datetime.utcnow().isoformat()
            )
            return BodySystemsResponse(
                head=default_system,
                chest=default_system,
                digestive=default_system,
                arms=default_system,
                legs=default_system,
                skin=default_system,
                mental=default_system
            )
        
        # Prepare context for LLM
        symptoms_summary = "\n".join([
            f"- {s.get('symptom_name', 'Unknown')}: severity {s.get('severity', '?')}/10 on {s.get('recorded_at', '')}"
            for s in (symptoms.data or [])[:30]
        ])
        
        consultations_summary = "\n".join([
            f"- {c.get('created_at', '')}: {c.get('message', '')[:100]}"
            for c in (consultations.data or [])[:10]
        ])
        
        scans_summary = "\n".join([
            f"- {s.get('body_part', 'Unknown')}: {s.get('urgency_level', '?')} urgency, {s.get('summary', '')[:100]}"
            for s in (scans.data or [])[:10]
        ])
        
        # Prepare LLM prompt
        system_prompt = """You are a body systems health analyst. Evaluate the health of each body system based on symptoms and consultations.

IMPORTANT: Return ONLY valid JSON with exact structure.
Analyze symptoms and map them to appropriate body systems.
Generate realistic health scores based on severity and frequency of issues.

System mapping guidelines:
- HEAD: headaches, migraines, dizziness, vision, hearing, cognitive issues
- CHEST: heart, lungs, breathing, chest pain, cardiovascular symptoms
- DIGESTIVE: stomach, intestines, nausea, appetite, digestion issues
- ARMS: shoulder, elbow, wrist, hand pain or weakness
- LEGS: hip, knee, ankle, foot pain, mobility issues
- SKIN: rashes, itching, dryness, wounds, skin conditions
- MENTAL: anxiety, depression, stress, mood, sleep issues

Score interpretation:
- 90-100: Excellent, no significant issues
- 70-89: Good, minor issues well-managed
- 50-69: Fair, moderate issues needing attention
- 30-49: Poor, significant issues affecting function
- 0-29: Critical, severe issues requiring immediate care"""

        user_prompt = f"""Analyze this health data and evaluate each body system:

RECENT SYMPTOMS (last 30 days):
{symptoms_summary or "No symptoms recorded"}

RECENT CONSULTATIONS:
{consultations_summary or "No consultations"}

RECENT SCANS:
{scans_summary or "No scans"}

Generate body systems health scores with this EXACT JSON structure:
{{
  "head": {{
    "health": [0-100 based on head-related symptoms],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "chest": {{
    "health": [0-100 based on chest/cardio/respiratory],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "digestive": {{
    "health": [0-100 based on digestive symptoms],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "arms": {{
    "health": [0-100 based on arm/shoulder issues],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "legs": {{
    "health": [0-100 based on leg/mobility issues],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "skin": {{
    "health": [0-100 based on skin conditions],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }},
  "mental": {{
    "health": [0-100 based on mental/emotional health],
    "issues": ["List specific issues found, max 3"],
    "trend": "improving|declining|stable",
    "lastUpdated": "{datetime.utcnow().isoformat()}"
  }}
}}

If no issues are found for a system, give it a high health score (85-95).
Base trends on comparing recent vs older data when available.
Be specific about issues found in the data."""

        # Call LLM for analysis
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-5-mini",  # Fast model for structured analysis
            user_id=user_id,
            temperature=0.3,
            max_tokens=2048
        )
        
        # Parse response
        if isinstance(llm_response.get("content"), dict):
            systems_data = llm_response["content"]
        else:
            # Extract JSON from string
            content = llm_response.get("raw_content", llm_response.get("content", ""))
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                systems_data = json.loads(json_str)
            else:
                raise ValueError("Failed to parse LLM response")
        
        # Validate and create response
        def validate_system(system_data):
            return SystemHealth(
                health=max(0, min(100, int(system_data.get('health', 75)))),
                issues=system_data.get('issues', [])[:3],  # Max 3 issues
                trend=system_data.get('trend', 'stable'),
                lastUpdated=system_data.get('lastUpdated', datetime.utcnow().isoformat())
            )
        
        response = BodySystemsResponse(
            head=validate_system(systems_data.get('head', {})),
            chest=validate_system(systems_data.get('chest', {})),
            digestive=validate_system(systems_data.get('digestive', {})),
            arms=validate_system(systems_data.get('arms', {})),
            legs=validate_system(systems_data.get('legs', {})),
            skin=validate_system(systems_data.get('skin', {})),
            mental=validate_system(systems_data.get('mental', {}))
        )
        
        logger.info(f"Generated body systems health for user {user_id}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate body systems health: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate body systems health: {str(e)}")
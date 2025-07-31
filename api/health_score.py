"""Health Score API endpoint - AI-driven health scoring with personalized actions"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
import json
import os
from typing import Dict, Any, List

from supabase_client import supabase
from business_logic import call_llm
from utils.data_gathering import get_health_story_data, get_user_medical_data
from utils.json_parser import extract_json_from_response

router = APIRouter(prefix="/api", tags=["health-score"])

async def calculate_health_score_with_ai(user_id: str) -> Dict[str, Any]:
    """
    Use AI to analyze health data and generate a score with personalized actions
    """
    try:
        # Gather recent health data (last 7 days)
        health_data = await get_health_story_data(user_id, {"start": 7, "end": 0})
        medical_profile = await get_user_medical_data(user_id)
        
        # Get current time for contextual actions
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour
        day_of_week = current_time.strftime("%A")
        
        # Build context for AI
        context = {
            "current_time": current_time.strftime("%H:%M"),
            "day_of_week": day_of_week,
            "medical_profile": medical_profile if isinstance(medical_profile, dict) else {},
            "recent_symptoms": [],
            "sleep_quality": "unknown",
            "stress_level": "unknown",
            "tracking_consistency": 0
        }
        
        # Extract key metrics from health data
        if health_data.get("symptom_tracking"):
            symptoms = []
            for entry in health_data["symptom_tracking"][-7:]:  # Last week
                if entry.get("symptoms"):
                    symptoms.extend(entry["symptoms"])
            context["recent_symptoms"] = list(set(symptoms))[:10]  # Top 10 unique
            context["tracking_consistency"] = min(len(health_data["symptom_tracking"]), 7)
        
        if health_data.get("quick_scans"):
            # Calculate average confidence from recent scans
            confidences = []
            for scan in health_data["quick_scans"][-5:]:
                if scan.get("confidence_score"):
                    confidences.append(scan["confidence_score"])
            if confidences:
                context["scan_confidence_avg"] = sum(confidences) / len(confidences)
        
        # Count oracle chats as engagement metric
        if health_data.get("oracle_chats"):
            context["engagement_level"] = len(health_data["oracle_chats"])
        
        # System prompt for health scoring
        system_prompt = """You are a health scoring AI that analyzes user data to calculate a wellness score.

SCORING RULES:
- Everyone starts at base score 80 (good baseline health)
- Score ranges from 0-100
- Consider: symptoms frequency, tracking consistency, engagement level
- Higher tracking consistency = better score
- Frequent symptoms = lower score
- Good engagement = slight boost

ACTION RULES:
- Generate EXACTLY 3 specific, actionable items for TODAY
- Base actions on current time of day and user patterns
- Use simple, clear language
- Each action should be achievable within the day
- Choose appropriate emoji icons

CRITICAL: Return ONLY valid JSON with this exact structure:
{
    "score": 76,
    "reasoning": "Brief explanation of score",
    "actions": [
        {"icon": "💧", "text": "Increase water intake by 500ml today"},
        {"icon": "🧘", "text": "10-minute meditation before bed"},
        {"icon": "🚶", "text": "Take a 15-minute walk after lunch"}
    ]
}"""

        user_prompt = f"""Analyze this health data and calculate a wellness score:

Current Context:
- Time: {context['current_time']} on {context['day_of_week']}
- Recent Symptoms: {', '.join(context['recent_symptoms']) if context['recent_symptoms'] else 'None reported'}
- Tracking Consistency: {context['tracking_consistency']}/7 days
- Engagement Level: {context.get('engagement_level', 0)} health conversations
- Scan Confidence: {context.get('scan_confidence_avg', 'No scans')}%

Medical Profile Available: {'Yes' if context['medical_profile'] else 'No'}

Calculate the health score and provide 3 personalized actions for today."""

        # Call LLM with Kimi K2
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="moonshotai/kimi-k2",
            user_id=user_id,
            temperature=0.3,
            max_tokens=512
        )
        
        # Extract and parse the response
        content = llm_response.get("content", "")
        
        # Try to extract JSON
        result = extract_json_from_response(content)
        
        if not result or not isinstance(result, dict):
            # Fallback response
            return {
                "score": 80,
                "reasoning": "Starting baseline health score",
                "actions": [
                    {"icon": "💧", "text": "Drink 8 glasses of water today"},
                    {"icon": "🚶", "text": "Take a 20-minute walk"},
                    {"icon": "😴", "text": "Aim for 8 hours of sleep tonight"}
                ]
            }
        
        # Validate score is in range
        score = result.get("score", 80)
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            score = 80
        
        return {
            "score": int(score),
            "reasoning": result.get("reasoning", "Health score calculated based on recent data"),
            "actions": result.get("actions", [])[:3]  # Ensure max 3 actions
        }
        
    except Exception as e:
        print(f"Error calculating health score: {e}")
        # Return sensible defaults on error
        return {
            "score": 80,
            "reasoning": "Unable to calculate personalized score",
            "actions": [
                {"icon": "💧", "text": "Stay hydrated throughout the day"},
                {"icon": "🏃", "text": "Get 30 minutes of physical activity"},
                {"icon": "🧘", "text": "Practice stress reduction techniques"}
            ]
        }

@router.get("/health-score/{user_id}")
async def get_health_score(user_id: str, force_refresh: bool = False):
    """
    Get or calculate user's health score with personalized daily actions
    """
    try:
        # Check cache first (unless force refresh)
        if not force_refresh:
            # Look for cached score from today
            cache_result = supabase.table("health_scores").select("*").eq(
                "user_id", user_id
            ).gte(
                "created_at", datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
            ).order("created_at", desc=True).limit(1).execute()
            
            if cache_result.data and len(cache_result.data) > 0:
                cached = cache_result.data[0]
                # Return cached result
                return {
                    "score": cached.get("score", 80),
                    "actions": cached.get("actions", []),
                    "reasoning": cached.get("reasoning", ""),
                    "generated_at": cached.get("created_at"),
                    "expires_at": cached.get("expires_at"),
                    "cached": True
                }
        
        # Calculate new score
        score_data = await calculate_health_score_with_ai(user_id)
        
        # Prepare expiration (24 hours from now)
        generated_at = datetime.now(timezone.utc)
        expires_at = generated_at + timedelta(hours=24)
        
        # Store in cache
        try:
            cache_data = {
                "user_id": user_id,
                "score": score_data["score"],
                "actions": score_data["actions"],
                "reasoning": score_data.get("reasoning", ""),
                "created_at": generated_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "week_of": generated_at.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            }
            
            supabase.table("health_scores").insert(cache_data).execute()
        except Exception as cache_error:
            print(f"Failed to cache health score: {cache_error}")
            # Continue even if caching fails
        
        # Return result
        return {
            "score": score_data["score"],
            "actions": score_data["actions"],
            "reasoning": score_data.get("reasoning", ""),
            "generated_at": generated_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "cached": False
        }
        
    except Exception as e:
        print(f"Error in health score endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/health-score/{user_id}/cache")
async def clear_health_score_cache(user_id: str):
    """
    Clear cached health scores for a user (useful for testing or manual refresh)
    """
    try:
        result = supabase.table("health_scores").delete().eq("user_id", user_id).execute()
        return {
            "status": "success",
            "message": f"Cleared health score cache for user {user_id}",
            "deleted_count": len(result.data) if result.data else 0
        }
    except Exception as e:
        print(f"Error clearing health score cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
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
- Generate EXACTLY 3 wellness tips tailored to the user's data
- CRITICAL: Each action must be 2-10 words maximum
- Mix general wellness advice with personalized recommendations
- If user has specific symptoms/patterns, address them directly
- Consider their tracking consistency and recent health data
- Focus on real-world activities: exercise, hydration, nutrition, sleep, stress management
- Consider time of day for relevance (morning vs evening tips)
- Make them specific and actionable
- Use encouraging, positive language

GOOD EXAMPLES (General):
- "Take a 20-minute walk in fresh air"
- "Drink a glass of water every hour until dinner"
- "Try 5 minutes of deep breathing before bed"
- "Add a serving of vegetables to your next meal"
- "Stand up and stretch for 2 minutes"
- "Get 15 minutes of sunlight today"
- "Replace one sugary drink with water"
- "Do 10 squats during your next break"

GOOD EXAMPLES (Personalized - based on user data):
- "Track headaches after coffee" (if user reports headaches)
- "Sleep by 10pm tonight" (if poor sleep patterns)
- "Avoid screens before bed" (if sleep issues)
- "Try yoga for back pain" (if back pain reported)
- "Check blood pressure after meals" (if BP concerns)
- "Walk after high-stress meetings" (if stress patterns)

BAD EXAMPLES (don't use these):
- "Track your symptoms in the app"
- "Log your sleep hours"
- "Update your medical profile"
- "Check your health insights"

CRITICAL: Return ONLY valid JSON with this exact structure:
{
    "score": 76,
    "reasoning": "Brief explanation of score",
    "actions": [
        {"icon": "💧", "text": "Drink 8 glasses of water throughout the day"},
        {"icon": "🚶", "text": "Take a 20-minute walk after lunch"},
        {"icon": "🧘", "text": "Practice 10 minutes of meditation before bed"}
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

Calculate the health score and provide 3 general wellness tips that would benefit anyone's daily health routine. Make them appropriate for the current time of day."""

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
                    {"icon": "🚶", "text": "Take a 20-minute walk in fresh air"},
                    {"icon": "😴", "text": "Wind down 30 minutes before bedtime"}
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
                {"icon": "💧", "text": "Drink a glass of water every 2 hours"},
                {"icon": "🏃", "text": "Go for a 30-minute walk today"},
                {"icon": "🧘", "text": "Take 5 deep breaths when feeling stressed"}
            ]
        }

@router.get("/health-score/{user_id}")
async def get_health_score(user_id: str, force_refresh: bool = False):
    """
    Get or calculate user's health score with personalized weekly actions
    """
    try:
        # Calculate current week's Monday
        today = datetime.now(timezone.utc)
        days_since_monday = today.weekday()
        current_monday = today - timedelta(days=days_since_monday)
        current_monday = current_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate previous week's Monday
        previous_monday = current_monday - timedelta(days=7)
        
        # Check for existing score this week (unless force refresh)
        if not force_refresh:
            # Look for score from current week
            cache_result = supabase.table("health_scores").select("*").eq(
                "user_id", user_id
            ).eq(
                "week_of", current_monday.isoformat()
            ).order("created_at", desc=True).limit(1).execute()
            
            if cache_result.data and len(cache_result.data) > 0:
                cached = cache_result.data[0]
                
                # Get previous week's score for comparison
                prev_result = supabase.table("health_scores").select("score").eq(
                    "user_id", user_id
                ).eq(
                    "week_of", previous_monday.isoformat()
                ).order("created_at", desc=True).limit(1).execute()
                
                previous_score = prev_result.data[0]["score"] if prev_result.data else None
                
                # Calculate trend
                trend = None
                if previous_score is not None:
                    if cached["score"] > previous_score:
                        trend = "up"
                    elif cached["score"] < previous_score:
                        trend = "down"
                    else:
                        trend = "same"
                
                # Return cached result with comparison
                return {
                    "score": cached.get("score", 80),
                    "previous_score": previous_score,
                    "trend": trend,
                    "actions": cached.get("actions", []),
                    "reasoning": cached.get("reasoning", ""),
                    "generated_at": cached.get("created_at"),
                    "week_of": cached.get("week_of"),
                    "cached": True
                }
        
        # Calculate new score
        score_data = await calculate_health_score_with_ai(user_id)
        
        # Prepare dates
        generated_at = datetime.now(timezone.utc)
        # Expires at end of current week (Sunday 23:59:59)
        days_until_sunday = 6 - generated_at.weekday()
        expires_at = generated_at + timedelta(days=days_until_sunday)
        expires_at = expires_at.replace(hour=23, minute=59, second=59)
        
        # Store in database
        try:
            cache_data = {
                "user_id": user_id,
                "score": score_data["score"],
                "actions": score_data["actions"],
                "reasoning": score_data.get("reasoning", ""),
                "created_at": generated_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "week_of": current_monday.isoformat()
            }
            
            supabase.table("health_scores").insert(cache_data).execute()
        except Exception as cache_error:
            print(f"Failed to save health score: {cache_error}")
            # Continue even if saving fails
        
        # Get previous week's score for comparison
        prev_result = supabase.table("health_scores").select("score").eq(
            "user_id", user_id
        ).eq(
            "week_of", previous_monday.isoformat()
        ).order("created_at", desc=True).limit(1).execute()
        
        previous_score = prev_result.data[0]["score"] if prev_result.data else None
        
        # Calculate trend
        trend = None
        if previous_score is not None:
            if score_data["score"] > previous_score:
                trend = "up"
            elif score_data["score"] < previous_score:
                trend = "down"
            else:
                trend = "same"
        
        # Return result with comparison
        return {
            "score": score_data["score"],
            "previous_score": previous_score,
            "trend": trend,
            "actions": score_data["actions"],
            "reasoning": score_data.get("reasoning", ""),
            "generated_at": generated_at.isoformat(),
            "week_of": current_monday.isoformat(),
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
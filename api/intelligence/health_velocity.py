"""
Health Velocity Score Module - LLM-generated health trajectory analysis
Analyzes health momentum and provides actionable recommendations
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging
import json

from supabase_client import supabase
from business_logic import call_llm
from utils.context_builder import get_enhanced_llm_context_time_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intelligence/health-velocity", tags=["health_velocity"])

class HealthVelocityResponse(BaseModel):
    score: int  # 0-100
    trend: str  # 'improving' | 'declining' | 'stable'
    momentum: float  # % change from last period
    sparkline: List[int]  # Last 7 data points
    recommendations: List[Dict[str, str]]

@router.get("/{user_id}")
async def get_health_velocity(user_id: str, time_range: str = "7D"):
    """
    Generate Health Velocity Score using LLM analysis
    Evaluates health trajectory and momentum from first principles
    """
    try:
        # Validate user has medical profile (required for intelligence features)
        from supabase_client import supabase
        medical_check = supabase.table('medical').select('id').eq('id', user_id).execute()
        if not medical_check.data:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=403,
                detail="Medical profile required for intelligence features. Please complete your health profile first."
            )
        
        logger.info(f"Generating health velocity for user {user_id}, range: {time_range}")
        
        # Parse time range
        days_map = {"7D": 7, "30D": 30, "90D": 90, "1Y": 365}
        days = days_map.get(time_range, 7)
        
        # Get current period data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        current_period = await get_enhanced_llm_context_time_range(
            user_id, start_date, end_date, f"current {days} days"
        )
        
        # Get previous period for comparison
        prev_end = start_date
        prev_start = prev_end - timedelta(days=days)
        previous_period = await get_enhanced_llm_context_time_range(
            user_id, prev_start, prev_end, f"previous {days} days"
        )
        
        # Get daily snapshot for sparkline (last 7 days)
        sparkline_data = []
        for i in range(7):
            day_date = end_date - timedelta(days=6-i)
            day_context = await get_enhanced_llm_context_time_range(
                user_id, day_date, day_date + timedelta(days=1), f"day {i+1}"
            )
            sparkline_data.append(day_context[:500])  # Brief summary for each day
        
        # Check if user has any data
        if not current_period or "No previous health interactions" in current_period:
            logger.warning(f"No health data found for user {user_id}")
            return HealthVelocityResponse(
                score=50,
                trend="stable",
                momentum=0.0,
                sparkline=[50] * 7,
                recommendations=[
                    {"action": "Start tracking symptoms daily", "impact": "+15 points", "icon": ""},
                    {"action": "Log your health patterns", "impact": "+10 points", "icon": ""}
                ]
            )
        
        # Prepare LLM prompt for velocity analysis
        system_prompt = """You are a health trajectory analyst. Calculate a Health Velocity Score based on health patterns.

IMPORTANT: Return ONLY valid JSON with exact structure.
Analyze the trajectory of health over time, considering:
1. Symptom frequency and severity changes
2. Consistency of tracking
3. Intervention effectiveness
4. Overall health momentum

Score interpretation:
- 0-30: Significant decline, urgent attention needed
- 31-50: Declining trend, intervention recommended  
- 51-70: Stable with room for improvement
- 71-85: Positive trajectory, good progress
- 86-100: Excellent momentum, optimal health path"""

        user_prompt = f"""Analyze health velocity for time range: {time_range}

CURRENT PERIOD ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}):
{current_period[:2000]}

PREVIOUS PERIOD ({prev_start.strftime('%Y-%m-%d')} to {prev_end.strftime('%Y-%m-%d')}):
{previous_period[:2000]}

DAILY SNAPSHOTS (last 7 days for sparkline):
Day 1: {sparkline_data[0]}
Day 2: {sparkline_data[1]}
Day 3: {sparkline_data[2]}
Day 4: {sparkline_data[3]}
Day 5: {sparkline_data[4]}
Day 6: {sparkline_data[5]}
Day 7 (today): {sparkline_data[6]}

Generate a Health Velocity Score with this EXACT JSON structure:
{{
  "score": [0-100 integer based on overall health trajectory],
  "trend": "improving|declining|stable",
  "momentum": [percentage change from previous period, e.g., 15.5 for +15.5%],
  "sparkline": [Array of 7 integers 0-100, one for each day's health score],
  "recommendations": [
    {{
      "action": "[Specific action to improve velocity]",
      "impact": "[Estimated point increase, e.g., '+8 points']",
      "icon": ""
    }},
    {{
      "action": "[Second recommendation]",
      "impact": "[Impact estimate]",
      "icon": ""
    }},
    {{
      "action": "[Third recommendation]",
      "impact": "[Impact estimate]",
      "icon": ""
    }}
  ]
}}

Base the score on:
1. Are symptoms improving or worsening?
2. Is tracking consistency improving?
3. Are interventions working?
4. What's the overall health momentum?

Generate realistic sparkline values showing daily variation.
Make recommendations specific and actionable based on the data."""

        # Call LLM for analysis
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-5-mini",  # Fast model for quick analysis
            user_id=user_id,
            temperature=0.3,
            max_tokens=1024
        )
        
        # Parse response
        if isinstance(llm_response.get("content"), dict):
            velocity_data = llm_response["content"]
        else:
            # Extract JSON from string
            content = llm_response.get("raw_content", llm_response.get("content", ""))
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                velocity_data = json.loads(json_str)
            else:
                raise ValueError("Failed to parse LLM response")
        
        # Validate and clean the response
        response = HealthVelocityResponse(
            score=max(0, min(100, int(velocity_data.get('score', 50)))),
            trend=velocity_data.get('trend', 'stable'),
            momentum=float(velocity_data.get('momentum', 0)),
            sparkline=velocity_data.get('sparkline', [50] * 7)[:7],  # Ensure exactly 7 points
            recommendations=velocity_data.get('recommendations', [])[:3]  # Max 3 recommendations
        )
        
        # Cache the result (optional)
        cache_key = f"velocity_{user_id}_{time_range}"
        cache_data = {
            'user_id': user_id,
            'cache_key': cache_key,
            'data': response.dict(),
            'generated_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        
        try:
            # Store in a cache table if it exists
            supabase.table('intelligence_cache').upsert(cache_data).execute()
        except:
            pass  # Cache is optional
        
        logger.info(f"Generated velocity score: {response.score} with trend: {response.trend}")
        return response
        
    except Exception as e:
        logger.error(f"Failed to generate health velocity: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate health velocity: {str(e)}")
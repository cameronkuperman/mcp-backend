"""
Weekly Health Brief Module - Comprehensive narrative health summary
Generates personalized, story-driven weekly health intelligence reports
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging
import json

from supabase_client import supabase
from business_logic import call_llm
from utils.data_gathering import get_health_story_data, gather_user_health_data
from utils.context_builder import get_enhanced_llm_context_time_range

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health-brief", tags=["weekly_brief"])

class GenerateBriefRequest(BaseModel):
    user_id: str
    week_of: Optional[str] = None  # ISO date of Monday
    force_regenerate: bool = False

class WeeklyHealthBrief(BaseModel):
    id: str
    user_id: str
    week_of: str
    greeting: Dict[str, Any]
    main_story: Dict[str, Any]
    discoveries: Dict[str, Any]
    experiments: Dict[str, Any]
    spotlight: Dict[str, Any]
    week_stats: Dict[str, Any]
    looking_ahead: Dict[str, Any]
    created_at: str
    last_opened_at: Optional[str] = None

def get_monday_of_week(date_str: Optional[str] = None) -> date:
    """Get Monday of the specified week or current week"""
    if date_str:
        target_date = datetime.fromisoformat(date_str).date()
    else:
        target_date = date.today()
    
    days_since_monday = target_date.weekday()
    return target_date - timedelta(days=days_since_monday)

@router.post("/generate")
async def generate_weekly_brief(request: GenerateBriefRequest):
    """
    Generate a comprehensive weekly health brief with narrative storytelling
    Uses LLM to create all components from first principles
    """
    try:
        logger.info(f"Generating weekly brief for user {request.user_id}")
        week_monday = get_monday_of_week(request.week_of)
        week_sunday = week_monday + timedelta(days=6)
        
        # Check for existing brief unless force regenerate
        if not request.force_regenerate:
            existing = supabase.table('weekly_health_briefs').select('*').eq(
                'user_id', request.user_id
            ).eq('week_of', week_monday.isoformat()).execute()
            
            if existing.data:
                logger.info(f"Returning cached brief for week of {week_monday}")
                # Update last opened timestamp
                supabase.table('weekly_health_briefs').update({
                    'last_opened_at': datetime.utcnow().isoformat()
                }).eq('id', existing.data[0]['id']).execute()
                
                return existing.data[0]
        
        # Gather comprehensive data for the week
        week_data = await get_enhanced_llm_context_time_range(
            request.user_id, 
            week_monday, 
            week_sunday,
            "weekly brief generation"
        )
        
        # Get previous week for comparison
        prev_monday = week_monday - timedelta(days=7)
        prev_sunday = week_monday - timedelta(days=1)
        prev_week_data = await get_enhanced_llm_context_time_range(
            request.user_id,
            prev_monday,
            prev_sunday,
            "previous week comparison"
        )
        
        # Get existing insights/predictions if available
        insights = supabase.table('health_insights').select('*').eq(
            'user_id', request.user_id
        ).eq('week_of', week_monday.isoformat()).execute()
        
        predictions = supabase.table('health_predictions').select('*').eq(
            'user_id', request.user_id
        ).eq('week_of', week_monday.isoformat()).execute()
        
        shadow_patterns = supabase.table('shadow_patterns').select('*').eq(
            'user_id', request.user_id
        ).eq('week_of', week_monday.isoformat()).execute()
        
        # Prepare comprehensive prompt for brief generation
        system_prompt = """You are a health storyteller creating a personalized weekly health brief. 
Generate a comprehensive, engaging narrative that makes health data meaningful and actionable.

IMPORTANT: Return ONLY valid JSON with the exact structure specified.
Create a compelling narrative that feels personal, not generic.
Use storytelling techniques to make patterns memorable.
Balance warmth with medical insight.

The brief should feel like it was written by a caring health advisor who knows the user well."""

        user_prompt = f"""Create a comprehensive weekly health brief for Week {week_monday.strftime('%U')} ({week_monday.strftime('%B %d')} - {week_sunday.strftime('%B %d, %Y')}).

THIS WEEK'S DATA:
{week_data[:3000]}

PREVIOUS WEEK FOR COMPARISON:
{prev_week_data[:2000]}

EXISTING INSIGHTS THIS WEEK:
{json.dumps([{'type': i['insight_type'], 'title': i['title'], 'description': i['description']} for i in (insights.data or [])[:3]], indent=2)}

PREDICTIONS:
{json.dumps([{'event': p['event_description'], 'probability': p['probability']} for p in (predictions.data or [])[:3]], indent=2)}

SHADOW PATTERNS (things no longer tracked):
{json.dumps([{'name': s['pattern_name'], 'significance': s['significance']} for s in (shadow_patterns.data or [])[:3]], indent=2)}

Generate a complete weekly brief with this EXACT JSON structure:
{{
  "greeting": {{
    "title": "Week [number]: [Compelling title about the week's theme]",
    "subtitle": "[Encouraging or insightful subtitle that sets the tone]",
    "readTime": "[X] min read",
    "generatedAt": "{datetime.utcnow().isoformat()}"
  }},
  
  "mainStory": {{
    "headline": "[Captivating headline about the week's main health story]",
    "narrative": "[500-800 word narrative that weaves together the week's health journey. Tell a story about patterns, changes, victories, and challenges. Make it personal and engaging, not a dry report. Include specific days, symptoms, and insights woven into a cohesive narrative.]",
    "weekHighlights": [
      {{
        "day": "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday",
        "event": "[What happened that day]",
        "impact": "positive|trigger|symptom",
        "detail": "[Brief detail about significance]"
      }}
    ],
    "inlineInsights": [
      {{
        "triggerText": "[Key phrase from the narrative]",
        "expansion": "[Deeper explanation or context]"
      }}
    ]
  }},
  
  "discoveries": {{
    "primaryPattern": {{
      "title": "[Main pattern discovered this week]",
      "description": "[2-3 sentences explaining the pattern and its implications]",
      "confidence": [0-100],
      "evidence": "[What data supports this pattern]"
    }},
    "secondaryPatterns": [
      {{
        "pattern": "[Pattern description]",
        "frequency": "[How often it occurred]",
        "actionable": true|false
      }}
    ],
    "comparisonToLastWeek": {{
      "overall": "[+X% improvement|-X% decline|stable]",
      "wins": ["[Specific improvement 1]", "[Specific improvement 2]"],
      "challenges": ["[Ongoing challenge 1]", "[New challenge 2]"]
    }}
  }},
  
  "experiments": {{
    "title": "This Week's Health Experiments",
    "recommendations": [
      {{
        "priority": "high|medium|low",
        "experiment": "[Specific experiment to try]",
        "rationale": "[Why this could help based on patterns]",
        "howTo": "[Step-by-step instructions]",
        "trackingMetric": "[What to measure for success]"
      }}
    ],
    "weeklyChecklist": [
      {{
        "id": "[unique-id]",
        "task": "[Specific task]",
        "completed": false
      }}
    ]
  }},
  
  "spotlight": {{
    "title": "[Educational topic relevant to user's patterns]",
    "content": "[200-300 words of educational content related to a pattern or symptom from the week]",
    "learnMore": {{
      "teaser": "[One sentence teaser for additional content]",
      "fullContent": "[Additional 200-300 words of deeper dive content]"
    }}
  }},
  
  "weekStats": {{
    "symptomFreeDays": [number],
    "bestDay": "[Day with least symptoms/best health]",
    "worstDay": "[Day with most challenges]",
    "trendsUp": ["[Improving metric 1]", "[Improving metric 2]"],
    "trendsDown": ["[Declining metric 1]", "[Declining metric 2]"],
    "aiConsultations": [number],
    "photosAnalyzed": [number]
  }},
  
  "lookingAhead": {{
    "prediction": "[Most likely pattern for next week based on data]",
    "watchFor": "[Key thing to monitor]",
    "encouragement": "[Personalized motivational message]"
  }}
}}

Make this brief feel like it was written specifically for this user, with genuine care and insight."""

        # Generate the comprehensive brief using LLM
        llm_response = await call_llm(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="x-ai/grok-4",  # Use Grok for maximum narrative quality
            user_id=request.user_id,
            temperature=0.7,  # Higher for creative storytelling
            max_tokens=4096
        )
        
        # Parse the response
        if isinstance(llm_response.get("content"), dict):
            brief_data = llm_response["content"]
        else:
            # Extract JSON from string response
            content = llm_response.get("raw_content", llm_response.get("content", ""))
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                brief_data = json.loads(json_str)
            else:
                raise ValueError("Failed to parse LLM response as JSON")
        
        # Store the brief in database
        stored_brief = supabase.table('weekly_health_briefs').insert({
            'user_id': request.user_id,
            'week_of': week_monday.isoformat(),
            'greeting': brief_data.get('greeting', {}),
            'main_story': brief_data.get('mainStory', {}),
            'discoveries': brief_data.get('discoveries', {}),
            'experiments': brief_data.get('experiments', {}),
            'spotlight': brief_data.get('spotlight', {}),
            'week_stats': brief_data.get('weekStats', {}),
            'looking_ahead': brief_data.get('lookingAhead', {}),
            'created_at': datetime.utcnow().isoformat(),
            'last_opened_at': datetime.utcnow().isoformat()
        }).execute()
        
        if stored_brief.data:
            logger.info(f"Successfully generated and stored weekly brief for user {request.user_id}")
            return stored_brief.data[0]
        else:
            raise HTTPException(status_code=500, detail="Failed to store weekly brief")
            
    except Exception as e:
        logger.error(f"Failed to generate weekly brief: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate weekly brief: {str(e)}")

@router.get("/{user_id}/current")
async def get_current_week_brief(user_id: str):
    """Get the current week's health brief"""
    try:
        current_monday = get_monday_of_week()
        
        result = supabase.table('weekly_health_briefs').select('*').eq(
            'user_id', user_id
        ).eq('week_of', current_monday.isoformat()).execute()
        
        if result.data:
            # Update last opened timestamp
            supabase.table('weekly_health_briefs').update({
                'last_opened_at': datetime.utcnow().isoformat()
            }).eq('id', result.data[0]['id']).execute()
            
            return result.data[0]
        else:
            return {
                'status': 'not_found',
                'message': 'No brief generated for current week',
                'week_of': current_monday.isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get current brief: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve current brief")

@router.get("/{user_id}/history")
async def get_brief_history(user_id: str, limit: int = 4, offset: int = 0):
    """Get historical weekly briefs"""
    try:
        result = supabase.table('weekly_health_briefs').select('*').eq(
            'user_id', user_id
        ).order('week_of', desc=True).range(offset, offset + limit - 1).execute()
        
        return {
            'status': 'success',
            'briefs': result.data or [],
            'total': len(result.data) if result.data else 0,
            'limit': limit,
            'offset': offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get brief history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve brief history")

@router.delete("/{user_id}/week/{week_of}")
async def delete_weekly_brief(user_id: str, week_of: str):
    """Delete a specific week's brief (for regeneration)"""
    try:
        result = supabase.table('weekly_health_briefs').delete().eq(
            'user_id', user_id
        ).eq('week_of', week_of).execute()
        
        return {
            'status': 'success',
            'message': f'Brief for week {week_of} deleted',
            'deleted': bool(result.data)
        }
        
    except Exception as e:
        logger.error(f"Failed to delete brief: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete brief")
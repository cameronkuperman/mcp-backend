"""
Health Analysis Module - AI-powered health intelligence features
Handles insights, predictions, shadow patterns, and strategic moves
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from pydantic import BaseModel
import json
import logging
import asyncio

# Initialize logger
logger = logging.getLogger(__name__)
from supabase import create_client, Client
import os

# Import our AI service (to be created)
# HealthAnalyzer removed - now using standard call_llm pattern
from utils.data_gathering import gather_user_health_data
from models.requests import HealthAnalysisRequest, RefreshAnalysisRequest

router = APIRouter(prefix="/api", tags=["health_analysis"])

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Analyzer no longer needed - using call_llm directly

# Request/Response Models
class GenerateAnalysisRequest(BaseModel):
    user_id: str
    force_refresh: bool = False
    include_predictions: bool = True
    include_patterns: bool = True
    include_strategies: bool = True

class AnalysisResponse(BaseModel):
    status: str
    story_id: Optional[str]
    insights: List[Dict]
    predictions: List[Dict]
    shadow_patterns: List[Dict]
    strategies: List[Dict]
    week_of: str
    generated_at: str

class ShareRequest(BaseModel):
    user_id: str
    story_ids: List[str]
    recipient_email: Optional[str] = None
    expires_in_days: int = 30

class ExportRequest(BaseModel):
    user_id: str
    story_ids: List[str]
    include_analysis: bool = True
    include_notes: bool = True
    export_format: str = "pdf"

def get_current_week_monday() -> date:
    """Get Monday of the current week"""
    today = date.today()
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)

async def check_refresh_limit(user_id: str) -> Dict:
    """Check if user has refresh attempts remaining"""
    week_of = get_current_week_monday()
    
    # Check existing refresh count
    result = supabase.table('user_refresh_limits').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of.isoformat()).execute()
    
    if result.data:
        refresh_data = result.data[0]
        return {
            'can_refresh': refresh_data['refresh_count'] < 10,
            'refreshes_used': refresh_data['refresh_count'],
            'refreshes_remaining': 10 - refresh_data['refresh_count']
        }
    else:
        # First refresh this week
        return {
            'can_refresh': True,
            'refreshes_used': 0,
            'refreshes_remaining': 10
        }

async def increment_refresh_count(user_id: str):
    """Increment the user's refresh count for the week"""
    week_of = get_current_week_monday()
    
    # Try to update existing record
    result = supabase.table('user_refresh_limits').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of.isoformat()).execute()
    
    if result.data:
        # Update existing
        supabase.table('user_refresh_limits').update({
            'refresh_count': result.data[0]['refresh_count'] + 1,
            'last_refresh_at': datetime.utcnow().isoformat()
        }).eq('id', result.data[0]['id']).execute()
    else:
        # Create new
        supabase.table('user_refresh_limits').insert({
            'user_id': user_id,
            'week_of': week_of.isoformat(),
            'refresh_count': 1,
            'last_refresh_at': datetime.utcnow().isoformat()
        }).execute()

@router.post("/generate-weekly-analysis")
async def generate_weekly_analysis(request: GenerateAnalysisRequest, background_tasks: BackgroundTasks):
    """
    Generate complete weekly health analysis including insights, predictions, patterns, and strategies
    """
    try:
        logger.info(f"Starting weekly analysis generation for user: {request.user_id}")
        week_of = get_current_week_monday()
        
        # Check if analysis already exists for this week
        if not request.force_refresh:
            existing = supabase.table('health_insights').select('id').eq(
                'user_id', request.user_id
            ).eq('week_of', week_of.isoformat()).limit(1).execute()
            
            if existing.data:
                # Return existing analysis
                return await get_health_analysis(request.user_id)
        
        # Check refresh limit if forcing refresh
        if request.force_refresh:
            limit_check = await check_refresh_limit(request.user_id)
            if not limit_check['can_refresh']:
                raise HTTPException(
                    status_code=429,
                    detail={
                        'message': 'Weekly refresh limit reached',
                        'refreshes_used': limit_check['refreshes_used'],
                        'refreshes_remaining': 0
                    }
                )
            await increment_refresh_count(request.user_id)
        
        # Log generation start
        log_id = supabase.table('analysis_generation_log').insert({
            'user_id': request.user_id,
            'generation_type': 'manual_refresh' if request.force_refresh else 'weekly_auto',
            'status': 'started',
            'week_of': week_of.isoformat(),
            'model_used': 'google/gemini-2.5-pro'
        }).execute().data[0]['id']
        
        start_time = datetime.utcnow()
        
        # Gather user health data
        health_data = await gather_user_health_data(request.user_id)
        
        # Get or generate the weekly story
        story_result = supabase.table('health_stories').select('*').eq(
            'user_id', request.user_id
        ).gte('created_at', week_of.isoformat()).order('created_at.desc').limit(1).execute()
        
        if not story_result.data:
            raise HTTPException(
                status_code=404,
                detail="No health story found for this week. Please generate a story first."
            )
        
        story = story_result.data[0]
        logger.info(f"Found story ID: {story.get('id')} for user: {request.user_id}")
        
        # Generate all analysis components in parallel
        tasks = []
        
        # Get the story content - the field is called 'story_text' in the database
        story_content = story.get('story_text') or ""
        
        if not story_content:
            raise HTTPException(
                status_code=400,
                detail="Health story has no content. Please generate a story first."
            )
        
        # Always generate insights
        tasks.append(analyzer.generate_insights(story_content, health_data, request.user_id))
        
        if request.include_predictions:
            tasks.append(analyzer.generate_predictions(story_content, health_data, request.user_id))
        
        if request.include_patterns:
            tasks.append(analyzer.detect_shadow_patterns(health_data, request.user_id))
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        insights = results[0] if not isinstance(results[0], Exception) else []
        predictions = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
        shadow_patterns = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else []
        
        logger.info(f"Generated {len(insights)} insights, {len(predictions)} predictions, {len(shadow_patterns)} shadow patterns")
        
        # Generate strategies based on all components
        strategies = []
        if request.include_strategies:
            strategies = await analyzer.generate_strategies(
                insights, predictions, shadow_patterns, request.user_id
            )
        
        # Store all results in database
        # Store insights
        if insights:
            for insight in insights:
                try:
                    # Convert user_id to UUID if needed
                    user_id_for_insert = request.user_id
                    if isinstance(request.user_id, str) and not request.user_id.startswith('{'):
                        # Try to convert to UUID format
                        try:
                            import uuid
                            uuid.UUID(request.user_id)
                            user_id_for_insert = request.user_id
                        except:
                            # If not a valid UUID, keep as is - let DB handle it
                            logger.warning(f"User ID {request.user_id} is not a valid UUID")
                            user_id_for_insert = request.user_id
                    
                    supabase.table('health_insights').insert({
                        'user_id': user_id_for_insert,
                        'story_id': story['id'],
                        'insight_type': insight['type'],
                        'title': insight['title'],
                        'description': insight['description'],
                        'confidence': insight['confidence'],
                        'week_of': week_of.isoformat(),
                        'metadata': insight.get('metadata', {}),
                        'generation_method': 'weekly'
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to insert insight: {str(e)}")
                    logger.error(f"User ID: {request.user_id}, Story ID: {story['id']}")
                    logger.error(f"Insight data: {insight}")
        
        # Store predictions
        if predictions:
            for pred in predictions:
                try:
                    supabase.table('health_predictions').insert({
                        'user_id': request.user_id,
                        'story_id': story['id'],
                        'event_description': pred['event'],
                        'probability': pred['probability'],
                        'timeframe': pred['timeframe'],
                        'preventable': pred.get('preventable', False),
                        'reasoning': pred.get('reasoning', ''),
                        'suggested_actions': pred.get('actions', []),
                        'week_of': week_of.isoformat(),
                        'generation_method': 'weekly'
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to insert prediction: {str(e)}")
                    logger.error(f"Prediction data: {pred}")
        
        # Store shadow patterns
        if shadow_patterns:
            for pattern in shadow_patterns:
                try:
                    supabase.table('shadow_patterns').insert({
                        'user_id': request.user_id,
                        'pattern_name': pattern['name'],
                        'pattern_category': pattern.get('category', 'other'),
                        'last_seen_description': pattern['last_seen'],
                        'significance': pattern['significance'],
                        'last_mentioned_date': pattern.get('last_date'),
                        'days_missing': pattern.get('days_missing', 0),
                        'week_of': week_of.isoformat(),
                        'generation_method': 'weekly'
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to insert shadow pattern: {str(e)}")
                    logger.error(f"Pattern data: {pattern}")
        
        # Store strategies
        if strategies:
            for strategy in strategies:
                supabase.table('strategic_moves').insert({
                    'user_id': request.user_id,
                    'strategy': strategy['strategy'],
                    'strategy_type': strategy['type'],
                    'priority': strategy['priority'],
                    'rationale': strategy.get('rationale', ''),
                    'expected_outcome': strategy.get('outcome', ''),
                    'week_of': week_of.isoformat(),
                    'generation_method': 'weekly'
                }).execute()
        
        # Update generation log
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        supabase.table('analysis_generation_log').update({
            'status': 'completed',
            'insights_count': len(insights),
            'predictions_count': len(predictions),
            'patterns_count': len(shadow_patterns),
            'strategies_count': len(strategies),
            'processing_time_ms': processing_time,
            'completed_at': datetime.utcnow().isoformat()
        }).eq('id', log_id).execute()
        
        return AnalysisResponse(
            status='success',
            story_id=story['id'],
            insights=insights,
            predictions=predictions,
            shadow_patterns=shadow_patterns,
            strategies=strategies,
            week_of=week_of.isoformat(),
            generated_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Analysis generation failed: {str(e)}")
        # Update log with failure
        if 'log_id' in locals():
            supabase.table('analysis_generation_log').update({
                'status': 'failed',
                'error_message': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }).eq('id', log_id).execute()
        raise HTTPException(status_code=500, detail=f"Analysis generation failed: {str(e)}")

@router.get("/health-analysis/{user_id}")
async def get_health_analysis(user_id: str, week_of: Optional[str] = None):
    """
    Retrieve the health analysis for a specific week
    """
    try:
        if not week_of:
            week_of = get_current_week_monday().isoformat()
        
        # Fetch all components
        insights = supabase.table('health_insights').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of).order('confidence.desc').execute()
        
        predictions = supabase.table('health_predictions').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of).order('probability.desc').execute()
        
        shadow_patterns = supabase.table('shadow_patterns').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of).order('significance').execute()
        
        strategies = supabase.table('strategic_moves').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of).order('priority.desc').execute()
        
        # Get story ID if available
        story_id = None
        if insights.data:
            story_id = insights.data[0].get('story_id')
        
        return AnalysisResponse(
            status='success',
            story_id=story_id,
            insights=insights.data or [],
            predictions=predictions.data or [],
            shadow_patterns=shadow_patterns.data or [],
            strategies=strategies.data or [],
            week_of=week_of,
            generated_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logging.error(f"Failed to retrieve analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis: {str(e)}")

@router.post("/refresh-analysis")
async def refresh_analysis(request: RefreshAnalysisRequest):
    """
    Manually refresh the analysis with rate limiting
    """
    # This is essentially the same as generate with force_refresh=True
    gen_request = GenerateAnalysisRequest(
        user_id=request.user_id,
        force_refresh=True,
        include_predictions=request.include_predictions,
        include_patterns=request.include_patterns,
        include_strategies=request.include_strategies
    )
    
    return await generate_weekly_analysis(gen_request, BackgroundTasks())

@router.put("/strategic-moves/{move_id}/status")
async def update_strategy_status(move_id: str, status: str, user_id: str):
    """
    Update the completion status of a strategic move
    """
    valid_statuses = ['pending', 'in_progress', 'completed', 'skipped']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    update_data = {'completion_status': status}
    if status == 'completed':
        update_data['completed_at'] = datetime.utcnow().isoformat()
    
    result = supabase.table('strategic_moves').update(update_data).eq(
        'id', move_id
    ).eq('user_id', user_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Strategic move not found")
    
    return {'status': 'success', 'move': result.data[0]}

@router.post("/trigger-weekly-generation")
async def trigger_weekly_generation_manual(user_id: Optional[str] = None):
    """
    Manually trigger weekly generation for testing
    """
    logger.info(f"TRIGGER ENDPOINT HIT! User ID: {user_id}")
    try:
        from services.background_jobs import trigger_weekly_generation_manual as trigger_job
        
        if user_id:
            # Generate for specific user
            result = await trigger_job([user_id])
        else:
            # Generate for all users
            result = await trigger_job()
        
        return {
            'status': 'success',
            'message': 'Weekly generation triggered',
            'result': result
        }
    except Exception as e:
        logging.error(f"Manual trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Trigger failed: {str(e)}")

@router.post("/generate-insights/{user_id}")
async def generate_insights_only(user_id: str, force_refresh: bool = False):
    """
    Generate key health insights using standard call_llm pattern
    Analyzes full history vs past week to identify patterns
    """
    try:
        logger.info(f"Generating insights for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        generation_start = datetime.now()
        
        # Check cache unless force refresh
        if not force_refresh:
            existing_insights = supabase.table('health_insights').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_insights.data and len(existing_insights.data) > 0:
                logger.info(f"Returning cached insights for user {user_id}")
                return {
                    'status': 'cached',
                    'data': existing_insights.data,
                    'count': len(existing_insights.data),
                    'metadata': {
                        'generated_at': existing_insights.data[0]['created_at'],
                        'week_of': week_of.isoformat(),
                        'cached': True,
                        'model_used': existing_insights.data[0].get('metadata', {}).get('model_used', 'unknown')
                    }
                }
        
        # Clear old insights if force refresh
        if force_refresh:
            supabase.table('health_insights').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import context builders
        from utils.context_builder import get_enhanced_llm_context, get_enhanced_llm_context_time_range
        from business_logic import call_llm
        import json
        
        # Get full context and past week context
        full_context = await get_enhanced_llm_context(user_id, None, "full health history")
        
        # Get past week context (Monday to Sunday)
        past_week_start = week_of - timedelta(days=7)
        past_week_end = week_of - timedelta(days=1)
        past_week_context = await get_enhanced_llm_context_time_range(
            user_id, past_week_start, past_week_end, "past week"
        )
        
        # Check if user has any data
        if not full_context or "No previous health interactions" in full_context:
            logger.warning(f"No health data found for user {user_id}")
            return {
                'status': 'no_data',
                'data': [],
                'count': 0,
                'message': 'Start tracking your health to get insights',
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat()
                }
            }
        
        # Prepare prompt for insights generation
        system_prompt = """You are a health intelligence analyst. Generate actionable health insights based on patterns in the user's data.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no explanations or text outside JSON
2. Generate 4-6 specific insights based on the actual data
3. Focus on patterns, changes, and actionable recommendations
4. Each insight must have: type (positive/warning/neutral), title (max 10 words), description (2-3 sentences), confidence (0-100)
5. Base insights on comparing full history with recent week patterns

JSON Format:
{
  "insights": [
    {
      "type": "positive|warning|neutral",
      "title": "Brief specific title",
      "description": "2-3 sentences explaining the insight and recommendation",
      "confidence": 85
    }
  ]
}"""

        user_prompt = f"""Analyze this health data and generate 4-6 key insights:

FULL HEALTH HISTORY (baseline patterns):
{full_context[:2000]}

PAST WEEK SPECIFICALLY ({past_week_start.strftime('%Y-%m-%d')} to {past_week_end.strftime('%Y-%m-%d')}):
{past_week_context[:1500]}

Compare the past week to the overall patterns. Focus on:
1. New or worsening symptoms
2. Improvements or positive changes
3. Missing data that was previously tracked
4. Patterns that need attention
5. Actionable next steps

Generate insights as JSON only."""

        # Call LLM using standard pattern
        try:
            llm_response = await call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="moonshotai/kimi-k2",
                user_id=user_id,
                temperature=0.3,
                max_tokens=2048
            )
            
            # Parse response
            if isinstance(llm_response.get("content"), dict):
                insights_data = llm_response["content"]
            else:
                # Extract JSON from string
                content = llm_response.get("raw_content", llm_response.get("content", ""))
                # Find JSON in response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    insights_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            
            # Extract insights array
            insights = insights_data.get('insights', [])
            
            # Store insights in database
            stored_insights = []
            for insight in insights:
                if isinstance(insight, dict) and all(key in insight for key in ['type', 'title', 'description', 'confidence']):
                    try:
                        # Validate user_id format
                        import uuid
                        try:
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            user_id_for_insert = user_id
                        
                        result = supabase.table('health_insights').insert({
                            'user_id': user_id_for_insert,
                            'story_id': None,  # No longer required after migration
                            'insight_type': insight['type'],
                            'title': insight['title'][:100],  # Ensure title fits
                            'description': insight['description'][:500],  # Ensure description fits
                            'confidence': max(0, min(100, int(insight.get('confidence', 70)))),
                            'week_of': week_of.isoformat(),
                            'metadata': {
                                'is_standalone': True,
                                'model_used': 'moonshotai/kimi-k2',
                                'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                            },
                            'generation_method': 'on_demand'
                        }).execute()
                        
                        if result.data:
                            stored_insights.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store insight: {str(db_error)}")
            
            # Calculate average confidence
            avg_confidence = sum(i.get('confidence', 70) for i in insights) / len(insights) if insights else 70
            
            logger.info(f"Successfully generated {len(stored_insights)} insights for user {user_id}")
            return {
                'status': 'success',
                'data': stored_insights,
                'count': len(stored_insights),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'model_used': 'moonshotai/kimi-k2',
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000),
                    'cached': False,
                    'confidence_avg': int(avg_confidence),
                    'context_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
                    'comparison_period': f"{past_week_start.strftime('%Y-%m-%d')} to {past_week_end.strftime('%Y-%m-%d')}"
                }
            }
            
        except Exception as llm_error:
            logger.error(f"LLM call failed for insights: {str(llm_error)}")
            # Return minimal fallback
            return {
                'status': 'error',
                'data': [],
                'count': 0,
                'error': str(llm_error),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                }
            }
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'data': [],
            'count': 0,
            'error': str(e),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat() if 'week_of' in locals() else None
            }
        }

@router.post("/generate-predictions/{user_id}")
async def generate_predictions_only(user_id: str, force_refresh: bool = False):
    """
    Generate health predictions using standard call_llm pattern
    Analyzes patterns to predict likely future health events
    """
    try:
        logger.info(f"Generating predictions for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        generation_start = datetime.now()
        
        # Check cache unless force refresh
        if not force_refresh:
            existing_predictions = supabase.table('health_predictions').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_predictions.data and len(existing_predictions.data) > 0:
                logger.info(f"Returning cached predictions for user {user_id}")
                return {
                    'status': 'cached',
                    'data': existing_predictions.data,
                    'count': len(existing_predictions.data),
                    'metadata': {
                        'generated_at': existing_predictions.data[0]['created_at'],
                        'week_of': week_of.isoformat(),
                        'cached': True,
                        'model_used': existing_predictions.data[0].get('metadata', {}).get('model_used', 'unknown')
                    }
                }
        
        # Clear old predictions if force refresh
        if force_refresh:
            supabase.table('health_predictions').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import context builders
        from utils.context_builder import get_enhanced_llm_context, get_enhanced_llm_context_time_range
        from business_logic import call_llm
        import json
        
        # Get full context and past week context
        full_context = await get_enhanced_llm_context(user_id, None, "full health history")
        
        # Get past 2 weeks for trend analysis
        two_weeks_ago = datetime.now() - timedelta(days=14)
        recent_context = await get_enhanced_llm_context_time_range(
            user_id, two_weeks_ago, datetime.now(), "recent trends"
        )
        
        # Check if user has any data
        if not full_context or "No previous health interactions" in full_context:
            logger.warning(f"No health data found for user {user_id}")
            return {
                'status': 'no_data',
                'data': [],
                'count': 0,
                'message': 'Need health history to generate predictions',
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat()
                }
            }
        
        # Check if we have a story for this week (optional enhancement)
        story_id = None
        story_result = supabase.table('health_stories').select('id').eq(
            'user_id', user_id
        ).gte('created_at', week_of.isoformat()).order('created_at.desc').limit(1).execute()
        if story_result.data:
            story_id = story_result.data[0]['id']
        
        # Prepare prompt for predictions generation
        system_prompt = """You are a health prediction specialist. Generate predictions about likely future health events based on patterns.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no explanations or text outside JSON
2. Generate 3-5 specific predictions based on observed patterns
3. Each prediction must be actionable and time-bound
4. Base predictions on trends, patterns, and risk factors in the data
5. Include preventable events and their prevention strategies

JSON Format:
{
  "predictions": [
    {
      "event": "Description of predicted health event",
      "probability": 75,
      "timeframe": "Next 7 days|Next 2 weeks|Next month",
      "preventable": true,
      "reasoning": "Why this is likely based on patterns",
      "actions": ["Specific action 1", "Specific action 2"]
    }
  ]
}"""

        user_prompt = f"""Analyze health patterns and generate predictions:

FULL HEALTH HISTORY (all patterns):
{full_context[:2000]}

RECENT 2 WEEKS TRENDS:
{recent_context[:1500]}

Based on these patterns, predict 3-5 likely health events that could occur in the coming days/weeks.

Consider:
1. Symptom escalation patterns (mild → severe)
2. Cyclical patterns (weekly/monthly recurrence)
3. Environmental triggers mentioned
4. Medication adherence patterns
5. Lifestyle factors that increase risk
6. Early warning signs present

Focus on:
- Events that are >50% likely based on patterns
- Both negative risks AND positive outcomes
- Actionable predictions the user can influence

Generate predictions as JSON only."""

        # Call LLM using standard pattern
        try:
            llm_response = await call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="moonshotai/kimi-k2",
                user_id=user_id,
                temperature=0.4,  # Slightly higher for creative predictions
                max_tokens=2048
            )
            
            # Parse response
            if isinstance(llm_response.get("content"), dict):
                predictions_data = llm_response["content"]
            else:
                # Extract JSON from string
                content = llm_response.get("raw_content", llm_response.get("content", ""))
                # Find JSON in response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    predictions_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            
            # Extract predictions array
            predictions = predictions_data.get('predictions', [])
            
            # Store predictions in database
            stored_predictions = []
            for pred in predictions:
                if isinstance(pred, dict) and all(key in pred for key in ['event', 'probability', 'timeframe']):
                    try:
                        # Validate user_id format
                        import uuid
                        try:
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            user_id_for_insert = user_id
                        
                        result = supabase.table('health_predictions').insert({
                            'user_id': user_id_for_insert,
                            'story_id': story_id,  # Can be None
                            'event_description': pred['event'][:500],
                            'probability': max(0, min(100, int(pred.get('probability', 70)))),
                            'timeframe': pred['timeframe'][:50],
                            'preventable': bool(pred.get('preventable', False)),
                            'reasoning': pred.get('reasoning', '')[:500],
                            'suggested_actions': pred.get('actions', [])[:5],  # Max 5 actions
                            'week_of': week_of.isoformat(),
                            'metadata': {
                                'model_used': 'moonshotai/kimi-k2',
                                'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                            },
                            'generation_method': 'on_demand'
                        }).execute()
                        
                        if result.data:
                            stored_predictions.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store prediction: {str(db_error)}")
            
            # Calculate average probability
            avg_probability = sum(p.get('probability', 70) for p in predictions) / len(predictions) if predictions else 70
            
            logger.info(f"Successfully generated {len(stored_predictions)} predictions for user {user_id}")
            return {
                'status': 'success',
                'data': stored_predictions,
                'count': len(stored_predictions),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'model_used': 'moonshotai/kimi-k2',
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000),
                    'cached': False,
                    'probability_avg': int(avg_probability),
                    'context_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
                    'analysis_period': f"Last 14 days ending {datetime.now().strftime('%Y-%m-%d')}"
                }
            }
            
        except Exception as llm_error:
            logger.error(f"LLM call failed for predictions: {str(llm_error)}")
            return {
                'status': 'error',
                'data': [],
                'count': 0,
                'error': str(llm_error),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                }
            }
        
    except Exception as e:
        logger.error(f"Failed to generate predictions: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'data': [],
            'count': 0,
            'error': str(e),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat() if 'week_of' in locals() else None
            }
        }

@router.post("/generate-shadow-patterns/{user_id}")
async def generate_shadow_patterns_only(user_id: str, force_refresh: bool = False):
    """
    Generate shadow patterns (missing behaviors) using standard call_llm pattern
    Compares full history vs current week to detect what's no longer being tracked
    """
    try:
        logger.info(f"Generating shadow patterns for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        generation_start = datetime.now()
        
        # Check cache unless force refresh
        if not force_refresh:
            existing_patterns = supabase.table('shadow_patterns').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_patterns.data and len(existing_patterns.data) > 0:
                logger.info(f"Returning cached shadow patterns for user {user_id}")
                return {
                    'status': 'cached',
                    'data': existing_patterns.data,
                    'count': len(existing_patterns.data),
                    'metadata': {
                        'generated_at': existing_patterns.data[0]['created_at'],
                        'week_of': week_of.isoformat(),
                        'cached': True,
                        'model_used': existing_patterns.data[0].get('metadata', {}).get('model_used', 'unknown')
                    }
                }
        
        # Clear old patterns if force refresh
        if force_refresh:
            supabase.table('shadow_patterns').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import context builders
        from utils.context_builder import get_enhanced_llm_context, get_enhanced_llm_context_time_range
        from business_logic import call_llm
        import json
        
        # Get full historical context (all time)
        full_context = await get_enhanced_llm_context(user_id, None, "full health history")
        
        # Get current week context (Monday to today)
        current_week_start = week_of
        current_week_end = datetime.now()
        current_week_context = await get_enhanced_llm_context_time_range(
            user_id, current_week_start, current_week_end, "current week"
        )
        
        # Check if user has any data
        if not full_context or "No previous health interactions" in full_context:
            logger.warning(f"No health data found for user {user_id}")
            return {
                'status': 'no_data',
                'data': [],
                'count': 0,
                'message': 'Need health history to detect missing patterns',
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat()
                }
            }
        
        # Prepare prompt for shadow pattern detection
        system_prompt = """You are a health pattern analyst specializing in detecting missing behaviors and forgotten health tracking.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no explanations or text outside JSON
2. Identify 3-5 things that were tracked historically but are MISSING from the current week
3. Only report patterns that appeared MULTIPLE times historically but are ABSENT now
4. Each pattern must have: name, category, last_seen, significance (high/medium/low), last_date, days_missing
5. Focus on health-relevant missing patterns, not trivial details

JSON Format:
{
  "patterns": [
    {
      "name": "Brief pattern name",
      "category": "symptom|treatment|wellness|medication|other",
      "last_seen": "Description of when/how it was last mentioned",
      "significance": "high|medium|low",
      "last_date": "YYYY-MM-DD",
      "days_missing": 7
    }
  ]
}"""

        user_prompt = f"""Analyze what health topics are MISSING from the current week compared to historical patterns:

FULL HEALTH HISTORY (all time - shows usual patterns):
{full_context[:2500]}

CURRENT WEEK ONLY ({current_week_start.strftime('%Y-%m-%d')} to {current_week_end.strftime('%Y-%m-%d')}):
{current_week_context[:1500]}

Identify 3-5 significant things that:
1. Were mentioned MULTIPLE times in history
2. Are COMPLETELY ABSENT this week
3. Could be important for health tracking

Examples to look for:
- Symptoms that stopped being reported (headaches, pain, fatigue)
- Medications no longer mentioned
- Wellness activities that ceased (exercise, meditation)
- Body parts previously tracked but ignored now
- Treatments or therapies not mentioned anymore

Generate shadow patterns as JSON only."""

        # Call LLM using standard pattern
        try:
            llm_response = await call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="moonshotai/kimi-k2",
                user_id=user_id,
                temperature=0.3,
                max_tokens=2048
            )
            
            # Parse response
            if isinstance(llm_response.get("content"), dict):
                patterns_data = llm_response["content"]
            else:
                # Extract JSON from string
                content = llm_response.get("raw_content", llm_response.get("content", ""))
                # Find JSON in response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    patterns_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            
            # Extract patterns array
            patterns = patterns_data.get('patterns', [])
            
            # Store patterns in database
            stored_patterns = []
            for pattern in patterns:
                if isinstance(pattern, dict) and all(key in pattern for key in ['name', 'last_seen', 'significance']):
                    try:
                        # Validate user_id format
                        import uuid
                        try:
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            user_id_for_insert = user_id
                        
                        # Parse last_date if provided
                        last_date = pattern.get('last_date')
                        if last_date and isinstance(last_date, str):
                            try:
                                # Validate date format
                                datetime.strptime(last_date, '%Y-%m-%d')
                            except:
                                last_date = None
                        
                        result = supabase.table('shadow_patterns').insert({
                            'user_id': user_id_for_insert,
                            'pattern_name': pattern['name'][:100],
                            'pattern_category': pattern.get('category', 'other'),
                            'last_seen_description': pattern['last_seen'][:500],
                            'significance': pattern.get('significance', 'medium').lower(),
                            'last_mentioned_date': last_date,
                            'days_missing': max(0, int(pattern.get('days_missing', 7))),
                            'week_of': week_of.isoformat(),
                            'historical_frequency': {
                                'model_used': 'moonshotai/kimi-k2',
                                'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                            },
                            'generation_method': 'on_demand'
                        }).execute()
                        
                        if result.data:
                            stored_patterns.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store shadow pattern: {str(db_error)}")
            
            logger.info(f"Successfully generated {len(stored_patterns)} shadow patterns for user {user_id}")
            return {
                'status': 'success',
                'data': stored_patterns,
                'count': len(stored_patterns),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'model_used': 'moonshotai/kimi-k2',
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000),
                    'cached': False,
                    'context_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
                    'current_week_range': f"{current_week_start.strftime('%Y-%m-%d')} to {current_week_end.strftime('%Y-%m-%d')}"
                }
            }
            
        except Exception as llm_error:
            logger.error(f"LLM call failed for shadow patterns: {str(llm_error)}")
            return {
                'status': 'error',
                'data': [],
                'count': 0,
                'error': str(llm_error),
                'message': 'Pattern detection temporarily unavailable',
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                }
            }
        
    except Exception as e:
        logger.error(f"Failed to generate shadow patterns: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'data': [],
            'count': 0,
            'error': str(e),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat() if 'week_of' in locals() else None
            }
        }

@router.post("/generate-strategies/{user_id}")
async def generate_strategies_only(user_id: str, force_refresh: bool = False):
    """
    Generate strategic health moves using standard call_llm pattern
    Synthesizes insights, predictions, and patterns into actionable strategies
    """
    try:
        logger.info(f"Generating strategies for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        generation_start = datetime.now()
        
        # Check cache unless force refresh
        if not force_refresh:
            existing_strategies = supabase.table('strategic_moves').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('priority.desc').execute()
            
            if existing_strategies.data and len(existing_strategies.data) > 0:
                logger.info(f"Returning cached strategies for user {user_id}")
                return {
                    'status': 'cached',
                    'data': existing_strategies.data,
                    'count': len(existing_strategies.data),
                    'metadata': {
                        'generated_at': existing_strategies.data[0]['created_at'],
                        'week_of': week_of.isoformat(),
                        'cached': True,
                        'model_used': existing_strategies.data[0].get('metadata', {}).get('model_used', 'unknown')
                    }
                }
        
        # Clear old strategies if force refresh
        if force_refresh:
            supabase.table('strategic_moves').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import required modules
        from utils.context_builder import get_enhanced_llm_context, get_enhanced_llm_context_time_range
        from business_logic import call_llm
        import json
        
        # Get existing intelligence components for this week
        insights_result = supabase.table('health_insights').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        predictions_result = supabase.table('health_predictions').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        patterns_result = supabase.table('shadow_patterns').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        # Also get full context for comprehensive strategy generation
        full_context = await get_enhanced_llm_context(user_id, None, "strategic planning")
        
        # Get recent context for immediate priorities
        past_week_start = week_of - timedelta(days=7)
        recent_context = await get_enhanced_llm_context_time_range(
            user_id, past_week_start, datetime.now(), "recent priorities"
        )
        
        # Check if user has any data
        has_intelligence = bool(insights_result.data or predictions_result.data or patterns_result.data)
        has_context = bool(full_context and "No previous health interactions" not in full_context)
        
        if not has_intelligence and not has_context:
            logger.warning(f"No data found for strategic planning for user {user_id}")
            return {
                'status': 'no_data',
                'data': [],
                'count': 0,
                'message': 'Need health data or intelligence components to generate strategies',
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat()
                }
            }
        
        # Format intelligence components for prompt
        insights_summary = "No insights available"
        if insights_result.data:
            insights_summary = "\n".join([
                f"- {i['insight_type'].upper()}: {i['title']} - {i['description'][:100]}..."
                for i in insights_result.data[:5]
            ])
        
        predictions_summary = "No predictions available"
        if predictions_result.data:
            predictions_summary = "\n".join([
                f"- {p['event_description']} ({p['probability']}% in {p['timeframe']})"
                for p in predictions_result.data[:5]
            ])
        
        patterns_summary = "No shadow patterns detected"
        if patterns_result.data:
            patterns_summary = "\n".join([
                f"- {sp['pattern_name']} ({sp['significance']} - missing {sp.get('days_missing', '?')} days)"
                for sp in patterns_result.data[:5]
            ])
        
        # Prepare prompt for strategy generation
        system_prompt = """You are a strategic health advisor. Generate actionable strategies based on health intelligence.

IMPORTANT INSTRUCTIONS:
1. Return ONLY valid JSON - no explanations or text outside JSON
2. Generate 4-6 strategic moves that synthesize insights, predictions, and patterns
3. Each strategy must be specific, actionable, and time-bound
4. Prioritize strategies by impact (1=lowest, 10=highest priority)
5. Mix strategy types: discovery, pattern, prevention, optimization

JSON Format:
{
  "strategies": [
    {
      "strategy": "Specific action to take",
      "type": "discovery|pattern|prevention|optimization",
      "priority": 8,
      "rationale": "Why this strategy matters now",
      "outcome": "Expected result if implemented"
    }
  ]
}"""

        user_prompt = f"""Generate strategic health moves based on this intelligence:

CURRENT WEEK INSIGHTS:
{insights_summary}

PREDICTIONS:
{predictions_summary}

SHADOW PATTERNS (things no longer tracked):
{patterns_summary}

FULL HEALTH CONTEXT:
{full_context[:1500]}

RECENT PRIORITIES (last week):
{recent_context[:1000]}

Based on all this intelligence, generate 4-6 strategic moves that:
1. Address the most pressing predictions
2. Leverage positive insights
3. Re-engage with shadow patterns if important
4. Discover new health optimization opportunities
5. Prevent negative outcomes

Prioritize by:
- Urgency (time-sensitive issues)
- Impact (potential health benefit)
- Feasibility (easy to implement)

Generate strategies as JSON only."""

        # Call LLM using standard pattern
        try:
            llm_response = await call_llm(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="moonshotai/kimi-k2",
                user_id=user_id,
                temperature=0.5,  # Higher for creative strategies
                max_tokens=2048
            )
            
            # Parse response
            if isinstance(llm_response.get("content"), dict):
                strategies_data = llm_response["content"]
            else:
                # Extract JSON from string
                content = llm_response.get("raw_content", llm_response.get("content", ""))
                # Find JSON in response
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    strategies_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")
            
            # Extract strategies array
            strategies = strategies_data.get('strategies', [])
            
            # Store strategies in database
            stored_strategies = []
            for strategy in strategies:
                if isinstance(strategy, dict) and all(key in strategy for key in ['strategy', 'type', 'priority']):
                    try:
                        # Validate user_id format
                        import uuid
                        try:
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            user_id_for_insert = user_id
                        
                        result = supabase.table('strategic_moves').insert({
                            'user_id': user_id_for_insert,
                            'strategy': strategy['strategy'][:500],
                            'strategy_type': strategy['type'],
                            'priority': max(1, min(10, int(strategy.get('priority', 5)))),
                            'rationale': strategy.get('rationale', '')[:500],
                            'expected_outcome': strategy.get('outcome', '')[:500],
                            'week_of': week_of.isoformat(),
                            'metadata': {
                                'model_used': 'moonshotai/kimi-k2',
                                'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000),
                                'based_on': {
                                    'insights_count': len(insights_result.data or []),
                                    'predictions_count': len(predictions_result.data or []),
                                    'patterns_count': len(patterns_result.data or [])
                                }
                            },
                            'generation_method': 'on_demand'
                        }).execute()
                        
                        if result.data:
                            stored_strategies.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store strategy: {str(db_error)}")
            
            # Calculate average priority
            avg_priority = sum(s.get('priority', 5) for s in strategies) / len(strategies) if strategies else 5
            
            logger.info(f"Successfully generated {len(stored_strategies)} strategies for user {user_id}")
            return {
                'status': 'success',
                'data': stored_strategies,
                'count': len(stored_strategies),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'model_used': 'moonshotai/kimi-k2',
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000),
                    'cached': False,
                    'priority_avg': round(avg_priority, 1),
                    'context_tokens': llm_response.get('usage', {}).get('prompt_tokens', 0),
                    'intelligence_sources': {
                        'insights': len(insights_result.data or []),
                        'predictions': len(predictions_result.data or []),
                        'shadow_patterns': len(patterns_result.data or [])
                    }
                }
            }
            
        except Exception as llm_error:
            logger.error(f"LLM call failed for strategies: {str(llm_error)}")
            return {
                'status': 'error',
                'data': [],
                'count': 0,
                'error': str(llm_error),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'week_of': week_of.isoformat(),
                    'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000)
                }
            }
        
    except Exception as e:
        logger.error(f"Failed to generate strategies: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'data': [],
            'count': 0,
            'error': str(e),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat() if 'week_of' in locals() else None
            }
        }

@router.post("/generate-all-intelligence/{user_id}")
async def generate_all_intelligence(user_id: str, force_refresh: bool = False):
    """
    Generate all 4 intelligence types in one efficient call
    Returns insights, shadow patterns, predictions, and strategies
    """
    try:
        logger.info(f"Generating all intelligence for user {user_id} (force_refresh={force_refresh})")
        generation_start = datetime.now()
        week_of = get_current_week_monday()
        
        # Check if all components are already cached
        if not force_refresh:
            # Check each component
            insights_check = supabase.table('health_insights').select('id').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).limit(1).execute()
            
            patterns_check = supabase.table('shadow_patterns').select('id').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).limit(1).execute()
            
            predictions_check = supabase.table('health_predictions').select('id').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).limit(1).execute()
            
            strategies_check = supabase.table('strategic_moves').select('id').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).limit(1).execute()
            
            # If all exist, return cached data
            if all([insights_check.data, patterns_check.data, predictions_check.data, strategies_check.data]):
                logger.info(f"All intelligence components cached for user {user_id}")
                
                # Fetch all cached data
                insights = supabase.table('health_insights').select('*').eq(
                    'user_id', user_id
                ).eq('week_of', week_of.isoformat()).execute()
                
                patterns = supabase.table('shadow_patterns').select('*').eq(
                    'user_id', user_id
                ).eq('week_of', week_of.isoformat()).execute()
                
                predictions = supabase.table('health_predictions').select('*').eq(
                    'user_id', user_id
                ).eq('week_of', week_of.isoformat()).execute()
                
                strategies = supabase.table('strategic_moves').select('*').eq(
                    'user_id', user_id
                ).eq('week_of', week_of.isoformat()).order('priority.desc').execute()
                
                return {
                    'status': 'cached',
                    'data': {
                        'insights': insights.data,
                        'shadow_patterns': patterns.data,
                        'predictions': predictions.data,
                        'strategies': strategies.data
                    },
                    'counts': {
                        'insights': len(insights.data),
                        'shadow_patterns': len(patterns.data),
                        'predictions': len(predictions.data),
                        'strategies': len(strategies.data)
                    },
                    'metadata': {
                        'generated_at': insights.data[0]['created_at'] if insights.data else datetime.now().isoformat(),
                        'week_of': week_of.isoformat(),
                        'cached': True,
                        'generation_time_ms': 0
                    }
                }
        
        # Generate all components in parallel for efficiency
        results = {
            'insights': None,
            'shadow_patterns': None,
            'predictions': None,
            'strategies': None
        }
        errors = {}
        
        # Import asyncio for parallel execution
        import asyncio
        
        # Define tasks
        async def generate_insights_task():
            try:
                result = await generate_insights_only(user_id, force_refresh=True)
                return 'insights', result
            except Exception as e:
                logger.error(f"Failed to generate insights: {e}")
                return 'insights', {'status': 'error', 'error': str(e), 'data': []}
        
        async def generate_patterns_task():
            try:
                result = await generate_shadow_patterns_only(user_id, force_refresh=True)
                return 'shadow_patterns', result
            except Exception as e:
                logger.error(f"Failed to generate shadow patterns: {e}")
                return 'shadow_patterns', {'status': 'error', 'error': str(e), 'data': []}
        
        async def generate_predictions_task():
            try:
                result = await generate_predictions_only(user_id, force_refresh=True)
                return 'predictions', result
            except Exception as e:
                logger.error(f"Failed to generate predictions: {e}")
                return 'predictions', {'status': 'error', 'error': str(e), 'data': []}
        
        # Run first 3 in parallel
        tasks = [
            generate_insights_task(),
            generate_patterns_task(),
            generate_predictions_task()
        ]
        
        # Execute parallel tasks
        task_results = await asyncio.gather(*tasks)
        
        # Process results
        for component, result in task_results:
            results[component] = result
            if result.get('status') == 'error':
                errors[component] = result.get('error', 'Unknown error')
        
        # Generate strategies last (depends on other components)
        try:
            strategies_result = await generate_strategies_only(user_id, force_refresh=True)
            results['strategies'] = strategies_result
            if strategies_result.get('status') == 'error':
                errors['strategies'] = strategies_result.get('error', 'Unknown error')
        except Exception as e:
            logger.error(f"Failed to generate strategies: {e}")
            results['strategies'] = {'status': 'error', 'error': str(e), 'data': []}
            errors['strategies'] = str(e)
        
        # Compile final response
        total_generation_time = int((datetime.now() - generation_start).total_seconds() * 1000)
        
        # Determine overall status
        if len(errors) == 4:
            overall_status = 'error'
        elif len(errors) > 0:
            overall_status = 'partial'
        else:
            overall_status = 'success'
        
        return {
            'status': overall_status,
            'data': {
                'insights': results['insights'].get('data', []),
                'shadow_patterns': results['shadow_patterns'].get('data', []),
                'predictions': results['predictions'].get('data', []),
                'strategies': results['strategies'].get('data', [])
            },
            'counts': {
                'insights': results['insights'].get('count', 0),
                'shadow_patterns': results['shadow_patterns'].get('count', 0),
                'predictions': results['predictions'].get('count', 0),
                'strategies': results['strategies'].get('count', 0)
            },
            'errors': errors if errors else None,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat(),
                'cached': False,
                'generation_time_ms': total_generation_time,
                'model_used': 'moonshotai/kimi-k2',
                'component_timings': {
                    'insights': results['insights'].get('metadata', {}).get('generation_time_ms', 0),
                    'shadow_patterns': results['shadow_patterns'].get('metadata', {}).get('generation_time_ms', 0),
                    'predictions': results['predictions'].get('metadata', {}).get('generation_time_ms', 0),
                    'strategies': results['strategies'].get('metadata', {}).get('generation_time_ms', 0)
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate all intelligence: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'data': {
                'insights': [],
                'shadow_patterns': [],
                'predictions': [],
                'strategies': []
            },
            'counts': {
                'insights': 0,
                'shadow_patterns': 0,
                'predictions': 0,
                'strategies': 0
            },
            'error': str(e),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'week_of': week_of.isoformat() if 'week_of' in locals() else None,
                'generation_time_ms': int((datetime.now() - generation_start).total_seconds() * 1000) if 'generation_start' in locals() else 0
            }
        }

@router.get("/insights/{user_id}")
async def get_insights(user_id: str, week_of: Optional[str] = None):
    """
    Get key insights for a specific week
    """
    if not week_of:
        week_of = get_current_week_monday().isoformat()
    
    insights = supabase.table('health_insights').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of).order('confidence.desc').execute()
    
    return {
        'status': 'success',
        'insights': insights.data or [],
        'week_of': week_of
    }

@router.get("/predictions/{user_id}")
async def get_predictions(user_id: str, week_of: Optional[str] = None):
    """
    Get health predictions for a specific week
    """
    if not week_of:
        week_of = get_current_week_monday().isoformat()
    
    predictions = supabase.table('health_predictions').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of).order('probability.desc').execute()
    
    return {
        'status': 'success',
        'predictions': predictions.data or [],
        'week_of': week_of
    }

@router.get("/shadow-patterns/{user_id}")
async def get_shadow_patterns(user_id: str, week_of: Optional[str] = None):
    """
    Get shadow patterns (not mentioned) for a specific week
    """
    if not week_of:
        week_of = get_current_week_monday().isoformat()
    
    patterns = supabase.table('shadow_patterns').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of).order('significance').execute()
    
    return {
        'status': 'success',
        'shadow_patterns': patterns.data or [],
        'week_of': week_of
    }

@router.get("/strategies/{user_id}")
async def get_strategies(user_id: str, week_of: Optional[str] = None):
    """
    Get strategic moves for a specific week
    """
    if not week_of:
        week_of = get_current_week_monday().isoformat()
    
    strategies = supabase.table('strategic_moves').select('*').eq(
        'user_id', user_id
    ).eq('week_of', week_of).order('priority.desc').execute()
    
    return {
        'status': 'success',
        'strategies': strategies.data or [],
        'week_of': week_of
    }

@router.get("/health-intelligence/status/{user_id}")
async def get_intelligence_status(user_id: str):
    """
    Check what components have been generated for the current week
    """
    try:
        week_of = get_current_week_monday()
        
        # Check each component
        insights = supabase.table('health_insights').select('id, created_at').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
        
        predictions = supabase.table('health_predictions').select('id, created_at').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
        
        patterns = supabase.table('shadow_patterns').select('id, created_at').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
        
        strategies = supabase.table('strategic_moves').select('id, created_at, completion_status').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
        
        # Check refresh limits
        refresh_limit = await check_refresh_limit(user_id)
        
        # Calculate strategy completion
        total_strategies = len(strategies.data) if strategies.data else 0
        completed_strategies = len([s for s in (strategies.data or []) if s['completion_status'] == 'completed'])
        
        return {
            'status': 'success',
            'week_of': week_of.isoformat(),
            'components': {
                'insights': {
                    'generated': bool(insights.data),
                    'count': len(insights.data) if insights.data else 0,
                    'last_generated': insights.data[0]['created_at'] if insights.data else None
                },
                'predictions': {
                    'generated': bool(predictions.data),
                    'count': len(predictions.data) if predictions.data else 0,
                    'last_generated': predictions.data[0]['created_at'] if predictions.data else None
                },
                'shadow_patterns': {
                    'generated': bool(patterns.data),
                    'count': len(patterns.data) if patterns.data else 0,
                    'last_generated': patterns.data[0]['created_at'] if patterns.data else None
                },
                'strategies': {
                    'generated': bool(strategies.data),
                    'count': total_strategies,
                    'completed': completed_strategies,
                    'completion_rate': round(completed_strategies / total_strategies * 100, 1) if total_strategies > 0 else 0,
                    'last_generated': strategies.data[0]['created_at'] if strategies.data else None
                }
            },
            'refresh_limits': refresh_limit,
            'all_generated': all([insights.data, predictions.data, patterns.data, strategies.data])
        }
        
    except Exception as e:
        logging.error(f"Failed to get intelligence status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve intelligence status")

@router.get("/analysis-history/{user_id}")
async def get_analysis_history(user_id: str, weeks: int = 4):
    """
    Get historical analysis data for trend visualization
    """
    try:
        cutoff_date = (date.today() - timedelta(weeks=weeks)).isoformat()
        
        # Get insights over time
        insights = supabase.table('health_insights').select(
            'week_of, insight_type, confidence'
        ).eq('user_id', user_id).gte('week_of', cutoff_date).execute()
        
        # Get predictions accuracy (if we tracked outcomes)
        predictions = supabase.table('health_predictions').select(
            'week_of, probability, status'
        ).eq('user_id', user_id).gte('week_of', cutoff_date).execute()
        
        # Get pattern evolution
        patterns = supabase.table('shadow_patterns').select(
            'week_of, pattern_name, significance'
        ).eq('user_id', user_id).gte('week_of', cutoff_date).execute()
        
        # Process into weekly summaries
        weekly_data = {}
        
        for insight in insights.data:
            week = insight['week_of']
            if week not in weekly_data:
                weekly_data[week] = {
                    'insights': {'positive': 0, 'warning': 0, 'neutral': 0},
                    'avg_confidence': [],
                    'predictions_accuracy': [],
                    'top_patterns': []
                }
            weekly_data[week]['insights'][insight['insight_type']] += 1
            weekly_data[week]['avg_confidence'].append(insight['confidence'])
        
        # Calculate averages
        for week, data in weekly_data.items():
            if data['avg_confidence']:
                data['avg_confidence'] = sum(data['avg_confidence']) / len(data['avg_confidence'])
            else:
                data['avg_confidence'] = 0
        
        return {
            'status': 'success',
            'history': weekly_data,
            'weeks_analyzed': weeks
        }
        
    except Exception as e:
        logging.error(f"Failed to get analysis history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analysis history")
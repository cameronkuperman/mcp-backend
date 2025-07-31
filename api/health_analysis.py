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
from services.ai_health_analyzer import HealthAnalyzer
from utils.data_gathering import gather_user_health_data
from models.requests import HealthAnalysisRequest, RefreshAnalysisRequest

router = APIRouter(prefix="/api", tags=["health_analysis"])

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize AI analyzer
analyzer = HealthAnalyzer()

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
    Generate only key insights for the current week with caching
    """
    try:
        logger.info(f"Generating insights for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        
        # Check if we should use cached data
        if not force_refresh:
            # Check if insights already exist for this week
            existing_insights = supabase.table('health_insights').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_insights.data and len(existing_insights.data) > 0:
                logger.info(f"Returning cached insights for user {user_id}")
                return {
                    'status': 'cached',
                    'insights': existing_insights.data,
                    'count': len(existing_insights.data),
                    'cached_from': existing_insights.data[0]['created_at']
                }
        
        # Delete old insights if force refresh
        if force_refresh:
            supabase.table('health_insights').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import the same function Oracle chat uses
        from api.chat import get_enhanced_llm_context
        
        # Get the same comprehensive health context that Oracle uses
        llm_context = await get_enhanced_llm_context(user_id, None, "weekly health insights")
        
        # Also get basic health data for additional context
        health_data = await gather_user_health_data(user_id)
        
        # Check if user has any health data at all
        if not llm_context or llm_context == "No previous health interactions recorded yet.":
            logger.warning(f"No health data found for user {user_id}")
            return {
                'status': 'no_data',
                'insights': [],
                'count': 0,
                'message': 'Start tracking your health to get insights'
            }
        
        try:
            # Generate insights using the same context as Oracle
            insights = await analyzer.generate_insights_from_context(llm_context, health_data, user_id)
            
            # Store insights
            stored_insights = []
            for insight in insights:
                if isinstance(insight, dict) and all(key in insight for key in ['type', 'title', 'description', 'confidence']):
                    try:
                        # Convert user_id to UUID if needed
                        import uuid
                        try:
                            # Validate it's a proper UUID
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            logger.error(f"Invalid UUID format for user_id: {user_id}")
                            user_id_for_insert = user_id  # Use as-is and let DB handle error
                        
                        # Create a dummy story_id since it's required by schema
                        dummy_story_id = str(uuid.uuid4())
                        
                        result = supabase.table('health_insights').insert({
                            'user_id': user_id_for_insert,
                            'story_id': dummy_story_id,  # Use dummy UUID since NOT NULL
                            'insight_type': insight['type'],
                            'title': insight['title'],
                            'description': insight['description'],
                            'confidence': insight['confidence'],
                            'week_of': week_of.isoformat(),
                            'metadata': insight.get('metadata', {'is_standalone': True}),
                            'generation_method': 'on_demand'
                        }).execute()
                        if result.data:
                            stored_insights.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store insight: {str(db_error)}")
                        logger.error(f"User ID: {user_id}, User ID for insert: {user_id_for_insert}")
            
            logger.info(f"Successfully generated {len(stored_insights)} insights for user {user_id}")
            return {
                'status': 'success',
                'insights': stored_insights,
                'count': len(stored_insights)
            }
            
        except Exception as ai_error:
            logger.error(f"AI generation failed for insights: {str(ai_error)}")
            # Return fallback insight
            import uuid as uuid_module
            try:
                uuid_obj = uuid_module.UUID(user_id)
                user_id_for_insert = str(uuid_obj)
            except ValueError:
                user_id_for_insert = user_id
            
            fallback_insight = {
                'user_id': user_id_for_insert,
                'story_id': str(uuid_module.uuid4()),  # Dummy story ID
                'insight_type': 'neutral',
                'title': 'Health Tracking Active',
                'description': 'Continue monitoring your health patterns for personalized insights.',
                'confidence': 70,
                'week_of': week_of.isoformat(),
                'metadata': {'is_fallback': True, 'is_standalone': True}
            }
            
            try:
                result = supabase.table('health_insights').insert(fallback_insight).execute()
                return {
                    'status': 'fallback',
                    'insights': result.data,
                    'count': 1,
                    'message': 'Using simplified insights'
                }
            except:
                return {
                    'status': 'error',
                    'insights': [],
                    'count': 0,
                    'error': str(ai_error)
                }
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'insights': [],
            'count': 0,
            'error': str(e)
        }

@router.post("/generate-predictions/{user_id}")
async def generate_predictions_only(user_id: str, force_refresh: bool = False):
    """
    Generate only health predictions for the current week with caching
    """
    try:
        logger.info(f"Generating predictions for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        
        # Check if we should use cached data
        if not force_refresh:
            # Check if predictions already exist for this week
            existing_predictions = supabase.table('health_predictions').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_predictions.data and len(existing_predictions.data) > 0:
                logger.info(f"Returning cached predictions for user {user_id}")
                return {
                    'status': 'cached',
                    'predictions': existing_predictions.data,
                    'count': len(existing_predictions.data),
                    'cached_from': existing_predictions.data[0]['created_at']
                }
        
        # Delete old predictions if force refresh
        if force_refresh:
            supabase.table('health_predictions').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Get health data and story
        health_data = await gather_user_health_data(user_id)
        
        story_result = supabase.table('health_stories').select('*').eq(
            'user_id', user_id
        ).gte('created_at', week_of.isoformat()).order('created_at.desc').limit(1).execute()
        
        if not story_result.data:
            logger.warning(f"No health story found for user {user_id} this week")
            return {
                'status': 'no_story',
                'predictions': [],
                'count': 0,
                'message': 'Generate a health story first to get predictions'
            }
        
        story = story_result.data[0]
        story_content = story.get('story_text') or ""
        
        if not story_content:
            return {
                'status': 'empty_story',
                'predictions': [],
                'count': 0,
                'message': 'Health story has no content'
            }
        
        try:
            # Generate predictions
            predictions = await analyzer.generate_predictions(story_content, health_data, user_id)
            
            # Store predictions
            stored_predictions = []
            for pred in predictions:
                if isinstance(pred, dict) and 'event' in pred and 'probability' in pred and 'timeframe' in pred:
                    try:
                        result = supabase.table('health_predictions').insert({
                            'user_id': user_id,
                            'story_id': story['id'],
                            'event_description': pred['event'],
                            'probability': max(0, min(100, int(pred.get('probability', 70)))),
                            'timeframe': pred['timeframe'],
                            'preventable': pred.get('preventable', False),
                            'reasoning': pred.get('reasoning', ''),
                            'suggested_actions': pred.get('actions', []),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'on_demand'
                        }).execute()
                        if result.data:
                            stored_predictions.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store prediction: {str(db_error)}")
            
            logger.info(f"Successfully generated {len(stored_predictions)} predictions for user {user_id}")
            return {
                'status': 'success',
                'predictions': stored_predictions,
                'count': len(stored_predictions)
            }
            
        except Exception as ai_error:
            logger.error(f"AI generation failed for predictions: {str(ai_error)}")
            # Return fallback prediction based on health data
            if health_data.get('recent_symptoms'):
                fallback_prediction = {
                    'user_id': user_id,
                    'story_id': story['id'],
                    'event_description': 'Monitor symptom patterns for changes',
                    'probability': 65,
                    'timeframe': 'This week',
                    'preventable': True,
                    'reasoning': 'Based on your recent health tracking',
                    'suggested_actions': ['Continue daily health monitoring', 'Note any triggers'],
                    'week_of': week_of.isoformat(),
                    'generation_method': 'on_demand'
                }
                
                try:
                    result = supabase.table('health_predictions').insert(fallback_prediction).execute()
                    return {
                        'status': 'fallback',
                        'predictions': result.data,
                        'count': 1,
                        'message': 'Using simplified predictions'
                    }
                except:
                    pass
            
            return {
                'status': 'error',
                'predictions': [],
                'count': 0,
                'error': str(ai_error)
            }
        
    except Exception as e:
        logger.error(f"Failed to generate predictions: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'predictions': [],
            'count': 0,
            'error': str(e)
        }

@router.post("/generate-shadow-patterns/{user_id}")
async def generate_shadow_patterns_only(user_id: str, force_refresh: bool = False):
    """
    Generate only shadow patterns (not mentioned) for the current week with caching
    """
    try:
        logger.info(f"Generating shadow patterns for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        
        # Check if we should use cached data
        if not force_refresh:
            # Check if patterns already exist for this week
            existing_patterns = supabase.table('shadow_patterns').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('created_at.desc').execute()
            
            if existing_patterns.data and len(existing_patterns.data) > 0:
                logger.info(f"Returning cached shadow patterns for user {user_id}")
                return {
                    'status': 'cached',
                    'shadow_patterns': existing_patterns.data,
                    'count': len(existing_patterns.data),
                    'cached_from': existing_patterns.data[0]['created_at']
                }
        
        # Delete old patterns if force refresh
        if force_refresh:
            supabase.table('shadow_patterns').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Import the same function Oracle chat uses for consistency
        from api.chat import get_enhanced_llm_context
        
        # Get comprehensive health context - split by time periods
        current_week_context = await get_enhanced_llm_context(user_id, None, "current week patterns")
        
        # Also get historical context (before this week)
        historical_context = await get_enhanced_llm_context(user_id, None, "historical patterns")
        
        # Get basic health data for additional info
        health_data = await gather_user_health_data(user_id)
        
        try:
            # Generate shadow patterns using both contexts
            shadow_patterns = await analyzer.detect_shadow_patterns_from_context(
                current_week_context, 
                historical_context, 
                health_data, 
                user_id
            )
            
            # Store shadow patterns
            stored_patterns = []
            for pattern in shadow_patterns:
                if isinstance(pattern, dict) and 'name' in pattern and 'last_seen' in pattern and 'significance' in pattern:
                    try:
                        # Convert user_id to UUID if needed
                        import uuid
                        try:
                            uuid_obj = uuid.UUID(user_id)
                            user_id_for_insert = str(uuid_obj)
                        except ValueError:
                            logger.error(f"Invalid UUID format for user_id: {user_id}")
                            user_id_for_insert = user_id
                        
                        result = supabase.table('shadow_patterns').insert({
                            'user_id': user_id_for_insert,
                            'pattern_name': pattern['name'],
                            'pattern_category': pattern.get('category', 'other'),
                            'last_seen_description': pattern['last_seen'],
                            'significance': pattern['significance'],
                            'last_mentioned_date': pattern.get('last_date'),
                            'days_missing': pattern.get('days_missing', 0),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'on_demand'
                        }).execute()
                        if result.data:
                            stored_patterns.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store shadow pattern: {str(db_error)}")
                        logger.error(f"Pattern data: {pattern}, User ID: {user_id}")
            
            logger.info(f"Successfully generated {len(stored_patterns)} shadow patterns for user {user_id}")
            return {
                'status': 'success',
                'shadow_patterns': stored_patterns,
                'count': len(stored_patterns)
            }
            
        except Exception as ai_error:
            logger.error(f"AI generation failed for shadow patterns: {str(ai_error)}")
            # Return empty patterns with error status
            return {
                'status': 'error',
                'shadow_patterns': [],
                'count': 0,
                'error': str(ai_error),
                'message': 'Pattern detection temporarily unavailable'
            }
        
    except Exception as e:
        logger.error(f"Failed to generate shadow patterns: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'shadow_patterns': [],
            'count': 0,
            'error': str(e)
        }

@router.post("/generate-strategies/{user_id}")
async def generate_strategies_only(user_id: str, force_refresh: bool = False):
    """
    Generate only strategic moves for the current week with caching
    """
    try:
        logger.info(f"Generating strategies for user {user_id} (force_refresh={force_refresh})")
        week_of = get_current_week_monday()
        
        # Check if we should use cached data
        if not force_refresh:
            # Check if strategies already exist for this week
            existing_strategies = supabase.table('strategic_moves').select('*').eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).order('priority.desc').execute()
            
            if existing_strategies.data and len(existing_strategies.data) > 0:
                logger.info(f"Returning cached strategies for user {user_id}")
                return {
                    'status': 'cached',
                    'strategies': existing_strategies.data,
                    'count': len(existing_strategies.data),
                    'cached_from': existing_strategies.data[0]['created_at']
                }
        
        # Delete old strategies if force refresh
        if force_refresh:
            supabase.table('strategic_moves').delete().eq(
                'user_id', user_id
            ).eq('week_of', week_of.isoformat()).execute()
        
        # Get existing analysis components
        insights_result = supabase.table('health_insights').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        predictions_result = supabase.table('health_predictions').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        patterns_result = supabase.table('shadow_patterns').select('*').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).execute()
        
        # Check if we have any components to base strategies on
        if not insights_result.data and not predictions_result.data and not patterns_result.data:
            logger.warning(f"No analysis components found for user {user_id}")
            return {
                'status': 'no_data',
                'strategies': [],
                'count': 0,
                'message': 'Generate insights, predictions, or patterns first'
            }
        
        # Convert back to the format the AI expects
        insights = []
        for i in (insights_result.data or []):
            insights.append({
                'type': i['insight_type'],
                'title': i['title'],
                'description': i['description'],
                'confidence': i['confidence']
            })
        
        predictions = []
        for p in (predictions_result.data or []):
            predictions.append({
                'event': p['event_description'],
                'probability': p['probability'],
                'timeframe': p['timeframe'],
                'preventable': p.get('preventable', False),
                'reasoning': p.get('reasoning', ''),
                'actions': p.get('suggested_actions', [])
            })
        
        shadow_patterns = []
        for sp in (patterns_result.data or []):
            shadow_patterns.append({
                'name': sp['pattern_name'],
                'category': sp.get('pattern_category', 'other'),
                'last_seen': sp['last_seen_description'],
                'significance': sp['significance'],
                'last_date': sp.get('last_mentioned_date'),
                'days_missing': sp.get('days_missing', 0)
            })
        
        try:
            # Generate strategies
            strategies = await analyzer.generate_strategies(
                insights, predictions, shadow_patterns, user_id
            )
            
            # Store strategies
            stored_strategies = []
            for strategy in strategies:
                if isinstance(strategy, dict) and 'strategy' in strategy and 'type' in strategy and 'priority' in strategy:
                    try:
                        result = supabase.table('strategic_moves').insert({
                            'user_id': user_id,
                            'strategy': strategy['strategy'],
                            'strategy_type': strategy['type'],
                            'priority': max(1, min(10, int(strategy.get('priority', 5)))),
                            'rationale': strategy.get('rationale', ''),
                            'expected_outcome': strategy.get('outcome', ''),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'on_demand'
                        }).execute()
                        if result.data:
                            stored_strategies.append(result.data[0])
                    except Exception as db_error:
                        logger.error(f"Failed to store strategy: {str(db_error)}")
            
            logger.info(f"Successfully generated {len(stored_strategies)} strategies for user {user_id}")
            return {
                'status': 'success',
                'strategies': stored_strategies,
                'count': len(stored_strategies)
            }
            
        except Exception as ai_error:
            logger.error(f"AI generation failed for strategies: {str(ai_error)}")
            # Return basic strategy based on available data
            basic_strategy = {
                'user_id': user_id,
                'strategy': 'Continue tracking your health patterns daily',
                'strategy_type': 'pattern',
                'priority': 7,
                'rationale': 'Consistent tracking enables better insights',
                'expected_outcome': 'Improved health awareness',
                'week_of': week_of.isoformat(),
                'generation_method': 'on_demand'
            }
            
            try:
                result = supabase.table('strategic_moves').insert(basic_strategy).execute()
                return {
                    'status': 'fallback',
                    'strategies': result.data,
                    'count': 1,
                    'message': 'Using simplified strategy'
                }
            except:
                return {
                    'status': 'error',
                    'strategies': [],
                    'count': 0,
                    'error': str(ai_error)
                }
        
    except Exception as e:
        logger.error(f"Failed to generate strategies: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'strategies': [],
            'count': 0,
            'error': str(e)
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
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
                        'metadata': insight.get('metadata', {})
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
                        'week_of': week_of.isoformat()
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
                        'week_of': week_of.isoformat()
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
                    'week_of': week_of.isoformat()
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
"""
Weekly Intelligence Generation Job
Automatically generates all intelligence features for active users
Runs once per week via scheduler
"""

import asyncio
from datetime import datetime, timedelta, date
from typing import List, Dict, Any
import logging
from supabase_client import supabase

logger = logging.getLogger(__name__)

async def generate_user_intelligence(user_id: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Generate all intelligence components for a single user
    Returns status of each component generation
    """
    results = {
        'user_id': user_id,
        'week_of': get_current_week_monday().isoformat(),
        'generated_at': datetime.utcnow().isoformat(),
        'components': {}
    }
    
    try:
        # Import intelligence modules
        from api.intelligence.weekly_brief import generate_weekly_brief, GenerateBriefRequest
        from api.health_analysis import (
            generate_insights_only,
            generate_predictions_only,
            generate_shadow_patterns_only,
            generate_strategies_only
        )
        
        # 1. Generate Weekly Health Brief (comprehensive narrative)
        try:
            logger.info(f"Generating weekly brief for user {user_id}")
            brief_request = GenerateBriefRequest(
                user_id=user_id,
                force_regenerate=force_refresh
            )
            brief_result = await generate_weekly_brief(brief_request)
            results['components']['weekly_brief'] = {
                'status': 'success',
                'id': brief_result.get('id') if isinstance(brief_result, dict) else None
            }
        except Exception as e:
            logger.error(f"Failed to generate weekly brief for {user_id}: {e}")
            results['components']['weekly_brief'] = {'status': 'error', 'error': str(e)}
        
        # 2. Generate Insights
        try:
            logger.info(f"Generating insights for user {user_id}")
            insights = await generate_insights_only(user_id, force_refresh=force_refresh)
            results['components']['insights'] = {
                'status': insights.get('status', 'success'),
                'count': insights.get('count', 0)
            }
        except Exception as e:
            logger.error(f"Failed to generate insights for {user_id}: {e}")
            results['components']['insights'] = {'status': 'error', 'error': str(e)}
        
        # 3. Generate Predictions
        try:
            logger.info(f"Generating predictions for user {user_id}")
            predictions = await generate_predictions_only(user_id, force_refresh=force_refresh)
            results['components']['predictions'] = {
                'status': predictions.get('status', 'success'),
                'count': predictions.get('count', 0)
            }
        except Exception as e:
            logger.error(f"Failed to generate predictions for {user_id}: {e}")
            results['components']['predictions'] = {'status': 'error', 'error': str(e)}
        
        # 4. Generate Shadow Patterns
        try:
            logger.info(f"Generating shadow patterns for user {user_id}")
            patterns = await generate_shadow_patterns_only(user_id, force_refresh=force_refresh)
            results['components']['shadow_patterns'] = {
                'status': patterns.get('status', 'success'),
                'count': patterns.get('count', 0)
            }
        except Exception as e:
            logger.error(f"Failed to generate shadow patterns for {user_id}: {e}")
            results['components']['shadow_patterns'] = {'status': 'error', 'error': str(e)}
        
        # 5. Generate Strategies (after other components)
        try:
            logger.info(f"Generating strategies for user {user_id}")
            strategies = await generate_strategies_only(user_id, force_refresh=force_refresh)
            results['components']['strategies'] = {
                'status': strategies.get('status', 'success'),
                'count': strategies.get('count', 0)
            }
        except Exception as e:
            logger.error(f"Failed to generate strategies for {user_id}: {e}")
            results['components']['strategies'] = {'status': 'error', 'error': str(e)}
        
        # Calculate overall success
        successful = sum(1 for c in results['components'].values() if c.get('status') == 'success')
        results['summary'] = {
            'total_components': 5,
            'successful': successful,
            'failed': 5 - successful,
            'success_rate': (successful / 5) * 100
        }
        
        logger.info(f"Completed intelligence generation for {user_id}: {successful}/5 successful")
        
    except Exception as e:
        logger.error(f"Critical error generating intelligence for {user_id}: {e}")
        results['error'] = str(e)
        results['summary'] = {'success_rate': 0}
    
    return results

def get_current_week_monday() -> date:
    """Get Monday of the current week"""
    today = date.today()
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)

async def get_active_users(days_active: int = 30) -> List[str]:
    """
    Get users who have been active in the last N days
    Active = has symptoms, consultations, or any health interactions
    """
    cutoff_date = (datetime.now() - timedelta(days=days_active)).isoformat()
    
    active_users = set()
    
    # Users with recent symptoms
    symptoms = supabase.table('symptom_tracking').select('user_id').gte(
        'recorded_at', cutoff_date
    ).execute()
    for record in (symptoms.data or []):
        if record.get('user_id'):
            active_users.add(record['user_id'])
    
    # Users with recent consultations
    chats = supabase.table('oracle_chats').select('user_id').gte(
        'created_at', cutoff_date
    ).execute()
    for record in (chats.data or []):
        if record.get('user_id'):
            active_users.add(record['user_id'])
    
    # Users with recent scans
    scans = supabase.table('quick_scans').select('user_id').gte(
        'created_at', cutoff_date
    ).execute()
    for record in (scans.data or []):
        if record.get('user_id'):
            active_users.add(record['user_id'])
    
    logger.info(f"Found {len(active_users)} active users in last {days_active} days")
    return list(active_users)

async def run_weekly_intelligence_generation(
    user_ids: List[str] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Main job function to generate weekly intelligence for all active users
    
    Args:
        user_ids: Optional list of specific user IDs to process
        force_refresh: Whether to force regeneration even if data exists
    
    Returns:
        Summary of the job execution
    """
    start_time = datetime.utcnow()
    logger.info(f"Starting weekly intelligence generation at {start_time}")
    
    # Get users to process
    if user_ids:
        users_to_process = user_ids
        logger.info(f"Processing specified {len(users_to_process)} users")
    else:
        users_to_process = await get_active_users(days_active=30)
        logger.info(f"Processing {len(users_to_process)} active users")
    
    if not users_to_process:
        logger.info("No users to process")
        return {
            'status': 'complete',
            'message': 'No active users found',
            'users_processed': 0,
            'duration_seconds': 0
        }
    
    # Process users in batches to avoid overwhelming the system
    batch_size = 5  # Process 5 users at a time
    all_results = []
    
    for i in range(0, len(users_to_process), batch_size):
        batch = users_to_process[i:i + batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(users_to_process) + batch_size - 1)//batch_size}")
        
        # Run batch in parallel
        batch_tasks = [
            generate_user_intelligence(user_id, force_refresh)
            for user_id in batch
        ]
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Process results
        for user_id, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process user {user_id}: {result}")
                all_results.append({
                    'user_id': user_id,
                    'error': str(result),
                    'summary': {'success_rate': 0}
                })
            else:
                all_results.append(result)
        
        # Small delay between batches to prevent rate limiting
        if i + batch_size < len(users_to_process):
            await asyncio.sleep(2)
    
    # Calculate overall statistics
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    total_users = len(all_results)
    successful_users = sum(1 for r in all_results if r.get('summary', {}).get('success_rate', 0) > 0)
    total_components = sum(len(r.get('components', {})) for r in all_results)
    successful_components = sum(
        sum(1 for c in r.get('components', {}).values() if c.get('status') == 'success')
        for r in all_results
    )
    
    summary = {
        'status': 'complete',
        'started_at': start_time.isoformat(),
        'completed_at': end_time.isoformat(),
        'duration_seconds': duration,
        'users_processed': total_users,
        'users_successful': successful_users,
        'users_failed': total_users - successful_users,
        'components_generated': successful_components,
        'components_failed': total_components - successful_components,
        'success_rate': (successful_users / total_users * 100) if total_users > 0 else 0,
        'week_of': get_current_week_monday().isoformat()
    }
    
    # Store job execution log
    try:
        supabase.table('job_execution_log').insert({
            'job_name': 'weekly_intelligence_generation',
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'duration_seconds': duration,
            'users_processed': total_users,
            'success_rate': summary['success_rate'],
            'metadata': summary
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log job execution: {e}")
    
    logger.info(f"Weekly intelligence generation complete: {successful_users}/{total_users} users successful")
    return summary

# Function to be called by scheduler
async def scheduled_weekly_intelligence_job():
    """
    Entry point for scheduled execution
    Runs every Sunday night/Monday morning at 2 AM
    """
    logger.info("Starting scheduled weekly intelligence generation")
    
    # Check if we've already run this week
    week_monday = get_current_week_monday()
    existing = supabase.table('job_execution_log').select('id').eq(
        'job_name', 'weekly_intelligence_generation'
    ).gte('started_at', week_monday.isoformat()).execute()
    
    if existing.data:
        logger.info(f"Weekly intelligence already generated for week of {week_monday}")
        return {
            'status': 'skipped',
            'message': 'Already generated this week',
            'week_of': week_monday.isoformat()
        }
    
    # Run the generation
    return await run_weekly_intelligence_generation()

# Manual trigger for testing
async def trigger_weekly_intelligence_now(user_ids: List[str] = None):
    """
    Manually trigger the weekly intelligence generation
    Useful for testing or on-demand generation
    """
    logger.info("Manually triggering weekly intelligence generation")
    return await run_weekly_intelligence_generation(
        user_ids=user_ids,
        force_refresh=True  # Force regeneration when manually triggered
    )
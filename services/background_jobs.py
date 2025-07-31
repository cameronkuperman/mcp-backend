"""
Background Jobs Service - Handles scheduled and async tasks
Includes weekly generation, batch processing, and cleanup tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from supabase import create_client, Client
import redis.asyncio as redis
from concurrent.futures import ThreadPoolExecutor
import json

# Import our services
from api.health_analysis import generate_weekly_analysis, GenerateAnalysisRequest
# Remove direct import - we'll call the endpoint instead
from utils.data_gathering import gather_user_health_data
# Import AI prediction functions will be done dynamically to avoid circular imports
from services.background_predictions import regeneration_service

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize Redis for job queuing and caching
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = None

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=4)

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")

async def cleanup_redis():
    """Cleanup Redis connection"""
    if redis_client:
        await redis_client.close()

def get_current_week_monday() -> date:
    """Get Monday of the current week"""
    today = date.today()
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)

async def get_active_users(batch_size: int = 100) -> List[Dict]:
    """Get all active users who need weekly generation"""
    logger.info("Getting active users for weekly generation...")
    try:
        # Get users who have been active in the last 30 days
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        # Query for active users through conversations
        result = supabase.table('conversations').select(
            'user_id'
        ).gte('updated_at', cutoff_date).execute()
        
        # Get unique user IDs
        user_ids = list(set(record['user_id'] for record in result.data))
        
        # Get user profiles
        users = []
        for i in range(0, len(user_ids), batch_size):
            batch_ids = user_ids[i:i + batch_size]
            profiles = supabase.table('profiles').select('*').in_('user_id', batch_ids).execute()
            users.extend(profiles.data)
        
        logger.info(f"Found {len(users)} active users for weekly generation")
        return users
        
    except Exception as e:
        logger.error(f"Failed to get active users: {str(e)}")
        return []

async def check_existing_generation(user_id: str, week_of: date) -> bool:
    """Check if weekly generation already exists"""
    try:
        # Check for existing insights this week
        result = supabase.table('health_insights').select('id').eq(
            'user_id', user_id
        ).eq('week_of', week_of.isoformat()).limit(1).execute()
        
        return len(result.data) > 0
        
    except Exception as e:
        logger.error(f"Failed to check existing generation: {str(e)}")
        return False

async def generate_user_weekly_content(user_id: str) -> Dict:
    """Generate complete weekly content for a single user"""
    try:
        week_of = get_current_week_monday()
        
        # Check if already generated
        if await check_existing_generation(user_id, week_of):
            logger.info(f"Weekly content already exists for user {user_id}")
            return {
                'user_id': user_id,
                'status': 'already_exists',
                'week_of': week_of.isoformat()
            }
        
        # Log start
        start_time = datetime.utcnow()
        log_id = supabase.table('analysis_generation_log').insert({
            'user_id': user_id,
            'generation_type': 'weekly_auto',
            'status': 'started',
            'week_of': week_of.isoformat(),
            'model_used': 'google/gemini-2.5-pro'
        }).execute().data[0]['id']
        
        try:
            # Step 1: Generate weekly story if not exists
            story_result = supabase.table('health_stories').select('id').eq(
                'user_id', user_id
            ).gte('created_at', week_of.isoformat()).limit(1).execute()
            
            if not story_result.data:
                logger.info(f"Generating weekly story for user {user_id}")
                # Call the health story endpoint via HTTP
                import httpx
                async with httpx.AsyncClient() as client:
                    # Use environment variable for API URL
                    api_url = os.getenv("API_URL", "http://localhost:8000")
                    response = await client.post(
                        f"{api_url}/api/health-story",
                        json={"user_id": user_id}
                    )
                    if response.status_code != 200:
                        logger.error(f"Failed to generate story: {response.text}")
            
            # Step 2: Generate analysis
            request = GenerateAnalysisRequest(
                user_id=user_id,
                force_refresh=False,
                include_predictions=True,
                include_patterns=True,
                include_strategies=True
            )
            
            # Use background tasks to avoid blocking
            from fastapi import BackgroundTasks
            background_tasks = BackgroundTasks()
            
            result = await generate_weekly_analysis(request, background_tasks)
            
            # Update log with success
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            supabase.table('analysis_generation_log').update({
                'status': 'completed',
                'processing_time_ms': processing_time,
                'completed_at': datetime.utcnow().isoformat()
            }).eq('id', log_id).execute()
            
            # Cache result if Redis available
            if redis_client:
                cache_key = f"weekly_analysis:{user_id}:{week_of.isoformat()}"
                await redis_client.setex(
                    cache_key,
                    86400,  # 24 hours
                    json.dumps(result.dict() if hasattr(result, 'dict') else result)
                )
            
            return {
                'user_id': user_id,
                'status': 'success',
                'week_of': week_of.isoformat(),
                'processing_time_ms': processing_time
            }
            
        except Exception as e:
            # Update log with failure
            supabase.table('analysis_generation_log').update({
                'status': 'failed',
                'error_message': str(e),
                'completed_at': datetime.utcnow().isoformat()
            }).eq('id', log_id).execute()
            
            raise
            
    except Exception as e:
        logger.error(f"Failed to generate weekly content for user {user_id}: {str(e)}")
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e),
            'week_of': get_current_week_monday().isoformat()
        }

async def generate_weekly_ai_predictions_for_user(user_id: str) -> Dict:
    """Generate and store weekly AI predictions for a single user"""
    try:
        logger.info(f"Generating AI predictions for user {user_id}")
        
        # Check if user has preferences
        prefs_result = supabase.table('user_ai_preferences').select('*').eq('user_id', user_id).execute()
        
        if not prefs_result.data:
            # Create default preferences
            supabase.table('user_ai_preferences').insert({
                'user_id': user_id,
                'initial_predictions_generated': True,
                'initial_generation_date': datetime.utcnow().isoformat()
            }).execute()
        
        # Mark old predictions as not current (handled by trigger, but just in case)
        supabase.table('weekly_ai_predictions').update({
            'is_current': False
        }).eq('user_id', user_id).eq('is_current', True).execute()
        
        # Create new prediction record
        prediction_record = {
            'user_id': user_id,
            'generation_status': 'pending',
            'generated_at': datetime.utcnow().isoformat()
        }
        
        result = supabase.table('weekly_ai_predictions').insert(prediction_record).execute()
        prediction_id = result.data[0]['id']
        
        try:
            # Generate all AI predictions via HTTP calls
            import httpx
            api_url = os.getenv("API_URL", "http://localhost:8000")
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
                # 1. Dashboard Alert
                alert_response = await client.get(f"{api_url}/api/ai/dashboard-alert/{user_id}")
                alert_data = alert_response.json() if alert_response.status_code == 200 else {}
                dashboard_alert = alert_data.get('alert') if alert_data else None
                
                # 2. Immediate Predictions
                predictions_response = await client.get(f"{api_url}/api/ai/predictions/immediate/{user_id}")
                predictions_data = predictions_response.json() if predictions_response.status_code == 200 else {}
                predictions = predictions_data.get('predictions', []) if predictions_data else []
                data_quality_score = predictions_data.get('data_quality_score', 0) if predictions_data else 0
                
                # 3. Pattern Questions
                questions_response = await client.get(f"{api_url}/api/ai/questions/{user_id}")
                questions_data = questions_response.json() if questions_response.status_code == 200 else {}
                pattern_questions = questions_data.get('questions', []) if questions_data else []
                
                # 4. Body Patterns
                patterns_response = await client.get(f"{api_url}/api/ai/patterns/{user_id}")
                patterns_data = patterns_response.json() if patterns_response.status_code == 200 else {}
                body_patterns = {
                    'tendencies': patterns_data.get('tendencies', []),
                    'positiveResponses': patterns_data.get('positive_responses', [])
                } if patterns_data else {}
            
            # Update the record with all data
            update_data = {
                'dashboard_alert': dashboard_alert,
                'predictions': predictions,
                'pattern_questions': pattern_questions,
                'body_patterns': body_patterns,
                'data_quality_score': data_quality_score,
                'generation_status': 'completed',
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('weekly_ai_predictions').update(update_data).eq('id', prediction_id).execute()
            
            # Update user preferences
            supabase.table('user_ai_preferences').update({
                'last_generation_date': datetime.utcnow().isoformat(),
                'generation_failure_count': 0
            }).eq('user_id', user_id).execute()
            
            logger.info(f"Successfully generated AI predictions for user {user_id}")
            return {
                'user_id': user_id,
                'status': 'success',
                'prediction_id': prediction_id
            }
            
        except Exception as e:
            # Update record with error
            supabase.table('weekly_ai_predictions').update({
                'generation_status': 'failed',
                'error_message': str(e),
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', prediction_id).execute()
            
            # Increment failure count
            supabase.table('user_ai_preferences').update({
                'generation_failure_count': supabase.raw('generation_failure_count + 1')
            }).eq('user_id', user_id).execute()
            
            raise
            
    except Exception as e:
        logger.error(f"Failed to generate AI predictions for user {user_id}: {str(e)}")
        return {
            'user_id': user_id,
            'status': 'error',
            'error': str(e)
        }


@scheduler.scheduled_job(CronTrigger(day_of_week='wed', hour=17, minute=0), id='weekly_ai_predictions')
async def weekly_ai_predictions_job():
    """
    Weekly AI predictions generation job - runs every Wednesday at 5 PM UTC
    Generates and stores AI predictions for all active users
    """
    logger.info(f"========== WEEKLY AI PREDICTIONS STARTED at {datetime.utcnow()} ==========")
    
    try:
        # Get users due for generation based on their preferences
        users_result = supabase.rpc('get_users_due_for_generation').execute()
        users_to_process = users_result.data if users_result.data else []
        
        if not users_to_process:
            logger.info("No users due for AI predictions generation")
            return
        
        total_users = len(users_to_process)
        successful = 0
        failed = 0
        
        # Process in batches
        batch_size = 5  # Smaller batch size for AI operations
        
        for i in range(0, total_users, batch_size):
            batch = users_to_process[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for user in batch:
                task = generate_weekly_ai_predictions_for_user(user['user_id'])
                tasks.append(task)
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for user, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"AI prediction generation failed for user {user['user_id']}: {result}")
                    failed += 1
                elif isinstance(result, dict) and result.get('status') == 'success':
                    successful += 1
                else:
                    failed += 1
            
            # Log progress
            logger.info(f"AI Predictions Progress: {i + len(batch)}/{total_users} users processed")
            
            # Delay between batches to avoid API rate limits
            if i + batch_size < total_users:
                await asyncio.sleep(10)
        
        # Log summary
        logger.info(
            f"Weekly AI predictions completed. "
            f"Successful: {successful}, Failed: {failed}, Total: {total_users}"
        )
        
        # Store summary
        supabase.table('generation_summaries').insert({
            'job_type': 'weekly_ai_predictions',
            'total_users': total_users,
            'successful': successful,
            'failed': failed,
            'completed_at': datetime.utcnow().isoformat()
        }).execute()
        
    except Exception as e:
        logger.error(f"Weekly AI predictions job failed: {str(e)}")


# Add function to process users at specific times based on their timezone
@scheduler.scheduled_job(CronTrigger(minute='0'), id='hourly_ai_predictions_check')
async def hourly_ai_predictions_check():
    """
    Hourly check for users whose preferred generation time has arrived
    This handles timezone-specific generation
    """
    try:
        current_hour = datetime.utcnow().hour
        current_day = datetime.utcnow().weekday()
        
        # Get users who prefer generation at this hour
        users_result = supabase.table('user_ai_preferences').select('*').eq(
            'weekly_generation_enabled', True
        ).eq('preferred_hour', current_hour).eq(
            'preferred_day_of_week', current_day
        ).execute()
        
        if users_result.data:
            logger.info(f"Processing {len(users_result.data)} users for hourly AI predictions")
            
            for user_pref in users_result.data:
                # Check if already generated this week
                last_gen = user_pref.get('last_generation_date')
                if last_gen:
                    last_gen_date = datetime.fromisoformat(last_gen.replace('Z', '+00:00'))
                    if (datetime.utcnow() - last_gen_date).days < 6:
                        continue
                
                # Generate predictions for this user
                await generate_weekly_ai_predictions_for_user(user_pref['user_id'])
                
    except Exception as e:
        logger.error(f"Hourly AI predictions check failed: {str(e)}")


@scheduler.scheduled_job(CronTrigger(day_of_week='mon', hour=9, minute=0), id='weekly_generation')
async def weekly_health_generation_job():
    """
    Main weekly generation job - runs every Monday at 9 AM UTC
    Generates health stories and analysis for all active users
    """
    logger.info(f"========== WEEKLY GENERATION STARTED at {datetime.utcnow()} ==========")
    
    try:
        # Get all active users
        active_users = await get_active_users()
        
        if not active_users:
            logger.warning("No active users found for weekly generation")
            return
        
        # Process in batches to avoid overload
        batch_size = 10  # Process 10 users concurrently
        total_users = len(active_users)
        successful = 0
        failed = 0
        
        for i in range(0, total_users, batch_size):
            batch = active_users[i:i + batch_size]
            
            # Process batch concurrently
            tasks = []
            for user in batch:
                task = generate_user_weekly_content(user['user_id'])
                tasks.append(task)
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for user, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"Generation failed for user {user['user_id']}: {result}")
                    failed += 1
                elif isinstance(result, dict) and result.get('status') == 'success':
                    successful += 1
                elif isinstance(result, dict) and result.get('status') == 'already_exists':
                    # Don't count as success or failure
                    pass
                else:
                    failed += 1
            
            # Log progress
            logger.info(f"Progress: {i + len(batch)}/{total_users} users processed")
            
            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < total_users:
                await asyncio.sleep(5)
        
        # Send summary notification (implement your notification system)
        logger.info(
            f"Weekly generation completed. "
            f"Successful: {successful}, Failed: {failed}, Total: {total_users}"
        )
        
        # Store summary in database
        supabase.table('generation_summaries').insert({
            'job_type': 'weekly_generation',
            'total_users': total_users,
            'successful': successful,
            'failed': failed,
            'completed_at': datetime.utcnow().isoformat()
        }).execute()
        
    except Exception as e:
        logger.error(f"Weekly generation job failed: {str(e)}")

@scheduler.scheduled_job(CronTrigger(hour=2, minute=0), id='cleanup_expired_shares')
async def cleanup_expired_shares():
    """Daily cleanup of expired share links"""
    try:
        logger.info("Starting cleanup of expired share links")
        
        # Delete expired share records
        result = supabase.table('export_history').delete().lt(
            'expires_at', datetime.utcnow().isoformat()
        ).execute()
        
        count = len(result.data) if result.data else 0
        logger.info(f"Cleaned up {count} expired share links")
        
    except Exception as e:
        logger.error(f"Cleanup job failed: {str(e)}")

@scheduler.scheduled_job(CronTrigger(day_of_week='sun', hour=23, minute=0), id='reset_refresh_limits')
async def reset_weekly_refresh_limits():
    """Reset user refresh limits at the end of each week"""
    try:
        logger.info("Resetting weekly refresh limits")
        
        # Get last week's Monday
        last_week = get_current_week_monday() - timedelta(days=7)
        
        # Archive old refresh records
        old_records = supabase.table('user_refresh_limits').select('*').lt(
            'week_of', last_week.isoformat()
        ).execute()
        
        if old_records.data:
            # Archive to a history table if needed
            logger.info(f"Archiving {len(old_records.data)} old refresh records")
            
            # Delete old records
            supabase.table('user_refresh_limits').delete().lt(
                'week_of', last_week.isoformat()
            ).execute()
        
    except Exception as e:
        logger.error(f"Failed to reset refresh limits: {str(e)}")

async def process_batch_analysis(user_ids: List[str], analysis_type: str = 'full') -> Dict:
    """Process analysis for multiple users in batch"""
    results = {
        'successful': [],
        'failed': [],
        'total': len(user_ids)
    }
    
    # Use semaphore to limit concurrent processing
    semaphore = asyncio.Semaphore(5)
    
    async def process_with_semaphore(user_id: str):
        async with semaphore:
            try:
                result = await generate_user_weekly_content(user_id)
                if result['status'] == 'success':
                    results['successful'].append(user_id)
                else:
                    results['failed'].append({
                        'user_id': user_id,
                        'error': result.get('error', 'Unknown error')
                    })
            except Exception as e:
                results['failed'].append({
                    'user_id': user_id,
                    'error': str(e)
                })
    
    # Process all users concurrently with semaphore
    tasks = [process_with_semaphore(user_id) for user_id in user_ids]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

# Manual trigger endpoints (for admin use)
async def trigger_weekly_generation_manual(user_ids: Optional[List[str]] = None) -> Dict:
    """Manually trigger weekly generation for specific users or all"""
    try:
        if user_ids:
            # Generate for specific users
            return await process_batch_analysis(user_ids)
        else:
            # Run the full weekly job
            await weekly_health_generation_job()
            return {'status': 'success', 'message': 'Weekly generation triggered for all users'}
            
    except Exception as e:
        logger.error(f"Manual trigger failed: {str(e)}")
        return {'status': 'error', 'error': str(e)}

# Initialize and start scheduler
async def init_scheduler():
    """Initialize the scheduler and Redis"""
    await init_redis()
    scheduler.start()
    logger.info("Background job scheduler started")
    
    # Start the prediction regeneration service in the background
    asyncio.create_task(regeneration_service.run_periodic_tasks())
    logger.info("Prediction regeneration service started")

async def shutdown_scheduler():
    """Cleanup scheduler and connections"""
    scheduler.shutdown()
    await cleanup_redis()
    await regeneration_service.close()
    logger.info("Background job scheduler stopped")

# Export functions for use in FastAPI
__all__ = [
    'init_scheduler',
    'shutdown_scheduler',
    'trigger_weekly_generation_manual',
    'process_batch_analysis'
]
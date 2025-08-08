"""Background service for smart caching and regeneration of AI predictions"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
from supabase_client import supabase
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# API configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")


class PredictionRegenerationService:
    """Service to handle background regeneration of expired predictions"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=300.0)
        self.api_url = API_URL
    
    async def check_and_regenerate_predictions(self):
        """Check for expired predictions and regenerate them"""
        try:
            # Get expired predictions directly from the table
            # Find predictions where regenerate_after has passed or expires_at has passed
            current_time = datetime.now(timezone.utc).isoformat()
            
            # Query for predictions that need regeneration
            expired_result = supabase.table('weekly_ai_predictions')\
                .select('user_id, prediction_type')\
                .eq('is_current', True)\
                .or_(f"regenerate_after.lt.{current_time},expires_at.lt.{current_time}")\
                .execute()
            
            if not expired_result.data:
                logger.info("No expired predictions to regenerate")
                return
            
            # Get unique user-prediction type combinations
            seen = set()
            expired_predictions = []
            for pred in expired_result.data:
                key = (pred['user_id'], pred['prediction_type'])
                if key not in seen:
                    seen.add(key)
                    expired_predictions.append(pred)
            
            logger.info(f"Found {len(expired_predictions)} expired predictions to regenerate")
            
            # Process each expired prediction
            for expired in expired_predictions:
                user_id = expired['user_id']
                prediction_type = expired['prediction_type']
                
                try:
                    await self.regenerate_prediction(user_id, prediction_type)
                except Exception as e:
                    logger.error(f"Failed to regenerate {prediction_type} for user {user_id}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error checking expired predictions: {str(e)}")
    
    async def regenerate_prediction(self, user_id: str, prediction_type: str):
        """Regenerate a specific prediction type for a user"""
        logger.info(f"Regenerating {prediction_type} prediction for user {user_id}")
        
        # Map prediction types to endpoints
        endpoints = {
            'dashboard': f'/api/ai/dashboard-alert/{user_id}',
            'immediate': f'/api/ai/predictions/immediate/{user_id}',
            'seasonal': f'/api/ai/predictions/seasonal/{user_id}',
            'longterm': f'/api/ai/predictions/longterm/{user_id}',
            'patterns': f'/api/ai/patterns/{user_id}',
            'questions': f'/api/ai/questions/{user_id}'
        }
        
        endpoint = endpoints.get(prediction_type)
        if not endpoint:
            logger.warning(f"Unknown prediction type: {prediction_type}")
            return
        
        # Call the API endpoint with force_refresh
        try:
            response = await self.client.get(
                f"{self.api_url}{endpoint}",
                params={"force_refresh": True}
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully regenerated {prediction_type} for user {user_id}")
                
                # Track regeneration stats
                try:
                    supabase.table('ai_prediction_stats').insert({
                        'user_id': user_id,
                        'prediction_type': prediction_type,
                        'cache_hit': False,
                        'forced_refresh': True,
                        'error_occurred': False
                    }).execute()
                except:
                    pass
            else:
                logger.error(f"Failed to regenerate {prediction_type} for user {user_id}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error calling regeneration endpoint: {str(e)}")
            
            # Track error
            try:
                supabase.table('ai_prediction_stats').insert({
                    'user_id': user_id,
                    'prediction_type': prediction_type,
                    'cache_hit': False,
                    'forced_refresh': True,
                    'error_occurred': True,
                    'error_message': str(e)
                }).execute()
            except:
                pass
    
    async def cleanup_old_predictions(self):
        """Clean up old non-current predictions"""
        try:
            # Delete predictions older than 90 days that are not current
            cutoff_date = datetime.now(timezone.utc).isoformat()
            
            result = supabase.table('weekly_ai_predictions').delete().eq(
                'is_current', False
            ).lt('generated_at', cutoff_date).execute()
            
            if result.data:
                logger.info(f"Cleaned up {len(result.data)} old predictions")
        
        except Exception as e:
            logger.error(f"Error cleaning up old predictions: {str(e)}")
    
    async def run_periodic_tasks(self):
        """Run periodic maintenance tasks"""
        while True:
            try:
                # Check and regenerate expired predictions
                await self.check_and_regenerate_predictions()
                
                # Clean up old predictions once a day
                if datetime.now().hour == 3:  # Run at 3 AM
                    await self.cleanup_old_predictions()
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in periodic tasks: {str(e)}")
                await asyncio.sleep(300)  # Sleep 5 minutes on error
    
    async def close(self):
        """Clean up resources"""
        await self.client.aclose()


# Create global service instance
regeneration_service = PredictionRegenerationService()


async def start_background_service():
    """Start the background regeneration service"""
    logger.info("Starting prediction regeneration background service")
    try:
        await regeneration_service.run_periodic_tasks()
    except KeyboardInterrupt:
        logger.info("Stopping prediction regeneration service")
        await regeneration_service.close()


if __name__ == "__main__":
    # Run the service standalone
    logging.basicConfig(level=logging.INFO)
    asyncio.run(start_background_service())
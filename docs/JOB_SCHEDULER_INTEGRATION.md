# Weekly Intelligence Job Scheduler Integration

## Complete Implementation Guide for Production-Ready Weekly Jobs

### 1. Integrate Weekly Intelligence into Background Jobs v2

```python
# Add to services/background_jobs_v2.py

from services.weekly_intelligence_job import (
    scheduled_weekly_intelligence_job,
    trigger_weekly_intelligence_now
)

class IntelligenceJobManager:
    """Manages weekly intelligence generation with retry logic"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay = timedelta(hours=2)
        self.batch_size = 10  # Process 10 users at a time
        
    async def schedule_weekly_intelligence(self):
        """Schedule the weekly intelligence job"""
        # Run every Monday at 2 AM
        scheduler.add_job(
            self.run_weekly_intelligence_with_verification,
            CronTrigger(day_of_week='mon', hour=2, minute=0),
            id='weekly_intelligence_generation',
            name='Generate Weekly Intelligence',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
            misfire_grace_time=3600  # 1 hour grace period
        )
        
    async def run_weekly_intelligence_with_verification(self):
        """Run weekly intelligence with verification and retry"""
        start_time = datetime.utcnow()
        job_id = f"intelligence_{start_time.isoformat()}"
        
        try:
            # Mark job as running
            await self.set_job_status(job_id, JobStatus.RUNNING)
            
            # Run the intelligence generation
            result = await scheduled_weekly_intelligence_job()
            
            # Verify results
            verification = await self.verify_generation(result)
            
            if verification['success_rate'] < 0.8:
                # Retry failed users
                await self.retry_failed_users(verification['failed_users'])
            
            # Mark job as completed
            await self.set_job_status(job_id, JobStatus.COMPLETED, result)
            
        except Exception as e:
            logger.error(f"Weekly intelligence job failed: {e}")
            await self.set_job_status(job_id, JobStatus.FAILED, {'error': str(e)})
            await self.trigger_fallback_generation()
    
    async def verify_generation(self, result: Dict) -> Dict:
        """Verify that intelligence was generated correctly"""
        week_of = get_current_week_monday()
        
        # Check each user's generation
        verification_results = []
        for user in result.get('users_processed', []):
            checks = {
                'brief_exists': await self.check_brief_exists(user, week_of),
                'insights_generated': await self.check_insights(user, week_of),
                'patterns_found': await self.check_patterns(user, week_of),
                'velocity_calculated': await self.check_velocity(user)
            }
            
            success = all(checks.values())
            verification_results.append({
                'user_id': user,
                'success': success,
                'checks': checks
            })
        
        successful = [r for r in verification_results if r['success']]
        failed = [r for r in verification_results if not r['success']]
        
        return {
            'success_rate': len(successful) / len(verification_results) if verification_results else 0,
            'successful_users': [r['user_id'] for r in successful],
            'failed_users': [r['user_id'] for r in failed],
            'details': verification_results
        }
    
    async def retry_failed_users(self, failed_users: List[str]):
        """Retry generation for failed users"""
        if not failed_users:
            return
        
        logger.info(f"Retrying intelligence generation for {len(failed_users)} users")
        
        for attempt in range(self.max_retries):
            await asyncio.sleep(self.retry_delay.total_seconds() * (attempt + 1))
            
            result = await trigger_weekly_intelligence_now(user_ids=failed_users)
            
            if result['success_rate'] > 0.8:
                logger.info(f"Retry successful on attempt {attempt + 1}")
                return
        
        logger.error(f"Failed to generate intelligence for users after {self.max_retries} retries")
        await self.notify_admin_failure(failed_users)
```

### 2. Database Schema for Job Tracking

```sql
-- Create job execution tracking tables
CREATE TABLE job_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    job_id VARCHAR(255) UNIQUE,
    status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed', 'retrying')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INT,
    users_processed INT DEFAULT 0,
    users_successful INT DEFAULT 0,
    users_failed INT DEFAULT 0,
    success_rate FLOAT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_job_execution_name_status ON job_execution_log(job_name, status);
CREATE INDEX idx_job_execution_started ON job_execution_log(started_at DESC);

-- Job retry tracking
CREATE TABLE job_retry_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    last_error TEXT,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(job_name, user_id)
);

-- User job preferences
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS
    intelligence_generation_enabled BOOLEAN DEFAULT true,
    intelligence_generation_frequency VARCHAR(20) DEFAULT 'weekly',
    last_intelligence_generated_at TIMESTAMP WITH TIME ZONE,
    intelligence_notification_enabled BOOLEAN DEFAULT true;
```

### 3. Redis Caching Strategy

```python
# Cache configuration for intelligence data
class IntelligenceCache:
    """Redis-based caching for intelligence data"""
    
    def __init__(self):
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)
        self.ttl = {
            'brief': 7 * 24 * 3600,  # 7 days
            'velocity': 3600,         # 1 hour
            'patterns': 24 * 3600,    # 1 day
            'systems': 3600           # 1 hour
        }
    
    async def cache_brief(self, user_id: str, week_of: str, data: Dict):
        """Cache weekly brief with appropriate TTL"""
        key = f"brief:{user_id}:{week_of}"
        await self.redis.setex(
            key,
            self.ttl['brief'],
            json.dumps(data)
        )
    
    async def get_cached_brief(self, user_id: str, week_of: str) -> Optional[Dict]:
        """Get cached brief if exists"""
        key = f"brief:{user_id}:{week_of}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache for a user"""
        pattern = f"*:{user_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
```

### 4. Manual Trigger Endpoint

```python
# Add to run_oracle.py or create new admin endpoints
@router.post("/admin/trigger-intelligence")
async def trigger_intelligence_generation(
    user_ids: Optional[List[str]] = None,
    force_refresh: bool = False,
    api_key: str = Header(None)
):
    """Manually trigger intelligence generation for testing"""
    
    # Verify admin API key
    if api_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    try:
        result = await trigger_weekly_intelligence_now(
            user_ids=user_ids,
            force_refresh=force_refresh
        )
        
        return {
            "status": "triggered",
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to trigger intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### 5. Testing Strategy

```python
# tests/test_weekly_intelligence.py
import pytest
from datetime import datetime, timedelta
from services.weekly_intelligence_job import (
    run_weekly_intelligence_generation,
    get_active_users
)

@pytest.mark.asyncio
async def test_intelligence_generation():
    """Test weekly intelligence generation for sample users"""
    
    # Create test users with data
    test_users = await create_test_users_with_health_data()
    
    # Run generation
    result = await run_weekly_intelligence_generation(
        user_ids=[u['id'] for u in test_users],
        force_refresh=True
    )
    
    # Verify results
    assert result['status'] == 'complete'
    assert result['users_successful'] == len(test_users)
    assert result['success_rate'] == 100.0
    
    # Verify data was created
    for user in test_users:
        brief = await get_user_brief(user['id'])
        assert brief is not None
        assert 'main_story' in brief
        assert 'week_stats' in brief

@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test that failed generations are retried"""
    
    # Simulate failure by using invalid user ID
    result = await run_weekly_intelligence_generation(
        user_ids=['invalid-user-id'],
        force_refresh=True
    )
    
    # Should handle gracefully
    assert result['status'] == 'complete'
    assert result['users_failed'] == 1
    
    # Check retry queue
    retry_queue = await get_retry_queue('weekly_intelligence_generation')
    assert len(retry_queue) == 1

@pytest.mark.asyncio
async def test_partial_failure_recovery():
    """Test recovery from partial failures"""
    
    # Create mix of valid and problematic users
    users = await create_mixed_test_users()
    
    result = await run_weekly_intelligence_generation(
        user_ids=users,
        force_refresh=True
    )
    
    # Should complete with partial success
    assert result['status'] == 'complete'
    assert result['users_successful'] > 0
    assert result['users_failed'] > 0
```

### 6. Monitoring & Alerting

```python
# monitoring/intelligence_health.py
class IntelligenceMonitor:
    """Monitor health of intelligence generation system"""
    
    async def check_system_health(self) -> Dict:
        """Comprehensive health check"""
        
        checks = {
            'last_run': await self.check_last_run(),
            'success_rate': await self.check_success_rate(),
            'generation_time': await self.check_generation_time(),
            'cache_hit_rate': await self.check_cache_performance(),
            'error_rate': await self.check_error_rate()
        }
        
        health_score = sum(1 for check in checks.values() if check['healthy']) / len(checks)
        
        return {
            'healthy': health_score > 0.8,
            'score': health_score,
            'checks': checks,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def check_last_run(self) -> Dict:
        """Check if job ran recently"""
        last_run = await get_last_job_execution('weekly_intelligence_generation')
        
        if not last_run:
            return {'healthy': False, 'message': 'No runs found'}
        
        hours_since = (datetime.utcnow() - last_run['started_at']).total_seconds() / 3600
        
        return {
            'healthy': hours_since < 168,  # Less than 1 week
            'hours_since_last_run': hours_since,
            'last_run_status': last_run['status']
        }
```

## Deployment Checklist

### Pre-deployment
- [ ] Run test suite with sample data
- [ ] Verify database migrations applied
- [ ] Configure Redis connection
- [ ] Set up monitoring dashboards
- [ ] Configure alerting thresholds

### Deployment
- [ ] Deploy code with feature flag OFF
- [ ] Run manual test with single user
- [ ] Run manual test with 10 users
- [ ] Enable for 1% of users
- [ ] Monitor for 24 hours
- [ ] Enable for all users

### Post-deployment
- [ ] Monitor success rates
- [ ] Check generation times
- [ ] Review error logs
- [ ] Optimize slow queries
- [ ] Adjust batch sizes if needed

## Performance Targets

- Generation time: < 5 seconds per user
- Success rate: > 95%
- Cache hit rate: > 80%
- Retry success rate: > 90%
- System availability: 99.9%
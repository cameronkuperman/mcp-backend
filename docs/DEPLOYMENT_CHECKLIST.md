# Complete Deployment Checklist for Intelligence Features

## 🚨 CRITICAL: Database Migrations to Run FIRST

### Step 1: Run These Supabase Migrations (IN ORDER)

```sql
-- 1. RUN THIS FIRST: Create weekly health briefs table
-- File: migrations/create_weekly_health_briefs.sql
-- Copy and paste the ENTIRE content into Supabase SQL editor

CREATE TABLE IF NOT EXISTS weekly_health_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    week_of DATE NOT NULL,
    greeting JSONB NOT NULL DEFAULT '{}'::jsonb,
    main_story JSONB NOT NULL DEFAULT '{}'::jsonb,
    discoveries JSONB NOT NULL DEFAULT '{}'::jsonb,
    experiments JSONB NOT NULL DEFAULT '{}'::jsonb,
    spotlight JSONB NOT NULL DEFAULT '{}'::jsonb,
    week_stats JSONB NOT NULL DEFAULT '{}'::jsonb,
    looking_ahead JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_opened_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, week_of)
);

-- 2. RUN THIS SECOND: Create job tracking tables
CREATE TABLE IF NOT EXISTS job_execution_log (
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

-- 3. RUN THIS THIRD: Intelligence cache table
CREATE TABLE IF NOT EXISTS intelligence_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    cache_key VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, cache_key)
);

-- 4. RUN THIS FOURTH: Anonymous patterns for comparative intelligence
CREATE TABLE IF NOT EXISTS anonymous_symptom_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_hash VARCHAR(16) NOT NULL,
    user_hash VARCHAR(16) NOT NULL,
    occurrence_count INT DEFAULT 1,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(pattern_hash, user_hash)
);

-- 5. RUN THIS FIFTH: User preferences updates
ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS
    weekly_brief_enabled BOOLEAN DEFAULT true,
    weekly_brief_frequency VARCHAR(20) DEFAULT 'weekly',
    last_brief_dismissed_at TIMESTAMP WITH TIME ZONE,
    total_briefs_dismissed INT DEFAULT 0,
    avg_engagement_time FLOAT DEFAULT 0,
    intelligence_generation_enabled BOOLEAN DEFAULT true,
    last_intelligence_generated_at TIMESTAMP WITH TIME ZONE;

-- 6. RUN THIS SIXTH: Create all indexes for performance
CREATE INDEX IF NOT EXISTS idx_weekly_briefs_user_id ON weekly_health_briefs(user_id);
CREATE INDEX IF NOT EXISTS idx_weekly_briefs_week_of ON weekly_health_briefs(week_of);
CREATE INDEX IF NOT EXISTS idx_job_execution_name_status ON job_execution_log(job_name, status);
CREATE INDEX IF NOT EXISTS idx_job_execution_started ON job_execution_log(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_intelligence_cache_expires ON intelligence_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_anon_patterns_hash ON anonymous_symptom_patterns(pattern_hash);

-- 7. RUN THIS SEVENTH: Enable RLS
ALTER TABLE weekly_health_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_cache ENABLE ROW LEVEL SECURITY;

-- 8. RUN THIS EIGHTH: Create RLS policies
CREATE POLICY "Users can view their own briefs"
    ON weekly_health_briefs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own briefs"
    ON weekly_health_briefs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own briefs"
    ON weekly_health_briefs FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own cache"
    ON intelligence_cache FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage their own cache"
    ON intelligence_cache FOR ALL
    USING (auth.uid() = user_id);

-- 9. RUN THIS LAST: Grant permissions
GRANT ALL ON weekly_health_briefs TO authenticated;
GRANT ALL ON intelligence_cache TO authenticated;
GRANT ALL ON anonymous_symptom_patterns TO authenticated;
GRANT ALL ON job_execution_log TO service_role;
```

## 🔧 Environment Variables to Add

Add these to your `.env` file:

```bash
# Admin key for manual triggers
ADMIN_API_KEY=your-secure-admin-key-here

# Redis (optional but recommended for caching)
REDIS_URL=redis://localhost:6379

# Job configuration
INTELLIGENCE_BATCH_SIZE=10
INTELLIGENCE_RETRY_DELAY_HOURS=2
INTELLIGENCE_MAX_RETRIES=3

# Feature flags
WEEKLY_INTELLIGENCE_ENABLED=true
INTELLIGENCE_CACHE_ENABLED=true
```

## 📦 Python Dependencies to Install

```bash
# Add to requirements.txt if not present
apscheduler>=3.10.0
redis>=5.0.0
httpx>=0.25.0
```

## 🚀 Backend Deployment Steps

### 1. Test Locally First
```bash
# Test that server starts without errors
python -m py_compile run_oracle.py

# Run server locally
python run_oracle.py

# Test health check
curl http://localhost:8000/api/health
```

### 2. Test Individual Intelligence Endpoints
```bash
# Test weekly brief generation
curl -X POST http://localhost:8000/api/health-brief/generate \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user-id"}'

# Test health velocity
curl http://localhost:8000/api/intelligence/health-velocity/test-user-id

# Test body systems
curl http://localhost:8000/api/intelligence/body-systems/test-user-id

# Test timeline
curl http://localhost:8000/api/intelligence/timeline/test-user-id

# Test patterns
curl http://localhost:8000/api/intelligence/patterns/test-user-id
```

### 3. Deploy to Railway/Your Platform
```bash
# Ensure Python 3.11 is specified
# Check railway.toml has:
# runtime.txt: python-3.11.x
```

## 🎨 Frontend Implementation Steps

### 1. Install Required Packages
```json
// Add to package.json
{
  "dependencies": {
    "@tanstack/react-query": "^5.0.0",  // For data fetching
    "framer-motion": "^10.0.0",         // For animations
    "react-intersection-observer": "^9.0.0", // For lazy loading
    "date-fns": "^2.30.0"                // For date handling
  }
}
```

### 2. Create API Hooks
```typescript
// hooks/useIntelligence.ts
export const useWeeklyBrief = (userId: string) => {
  return useQuery({
    queryKey: ['weekly-brief', userId],
    queryFn: () => fetch(`/api/health-brief/${userId}/current`),
    staleTime: 1000 * 60 * 60, // 1 hour
    cacheTime: 1000 * 60 * 60 * 24, // 24 hours
  });
};

export const useHealthVelocity = (userId: string, timeRange: string) => {
  return useQuery({
    queryKey: ['health-velocity', userId, timeRange],
    queryFn: () => fetch(`/api/intelligence/health-velocity/${userId}?time_range=${timeRange}`),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
};
```

### 3. Implement Weekly Brief Overlay
```typescript
// components/WeeklyBriefOverlay.tsx
const WeeklyBriefOverlay = () => {
  const { data: brief } = useWeeklyBrief(userId);
  const [dismissed, setDismissed] = useLocalStorage(`brief-dismissed-${brief?.week_of}`, false);
  
  // Show on first login of the week
  useEffect(() => {
    if (brief && !dismissed && isFirstLoginThisWeek()) {
      setShowOverlay(true);
    }
  }, [brief]);
  
  // Track engagement
  const handleDismiss = () => {
    trackEvent('weekly_brief_dismissed', {
      engagement_time: Date.now() - startTime,
      scroll_depth: getScrollDepth()
    });
    setDismissed(true);
    setShowOverlay(false);
  };
};
```

## 🧪 Testing Checklist

### Database Tests
- [ ] All tables created successfully
- [ ] RLS policies working (test with different users)
- [ ] Indexes improving query performance

### API Tests
- [ ] Each intelligence endpoint returns data
- [ ] Error handling works (test with invalid user IDs)
- [ ] Rate limiting doesn't block legitimate requests

### Job Tests
- [ ] Manual trigger works via admin endpoint
- [ ] Weekly schedule triggers on time
- [ ] Retry mechanism handles failures
- [ ] Partial failures don't break entire job

### Frontend Tests
- [ ] Brief overlay appears on first login
- [ ] Dismissal tracking works
- [ ] All intelligence components load
- [ ] Mobile responsive design works
- [ ] Loading states display correctly

## 📊 Monitoring Setup

### 1. Create Monitoring Dashboard
```sql
-- Add this view to Supabase for monitoring
CREATE OR REPLACE VIEW intelligence_health_dashboard AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(DISTINCT user_id) as briefs_generated,
    AVG(EXTRACT(EPOCH FROM (last_opened_at - created_at))) as avg_time_to_open,
    COUNT(CASE WHEN last_opened_at IS NOT NULL THEN 1 END)::FLOAT / COUNT(*) as open_rate
FROM weekly_health_briefs
GROUP BY DATE_TRUNC('day', created_at);
```

### 2. Set Up Alerts
- Alert if job success rate < 90%
- Alert if generation time > 10 seconds per user
- Alert if cache hit rate < 70%
- Alert if any endpoint response time > 3 seconds

## 🚨 Common Issues & Solutions

### Issue: "Table not found" errors
**Solution**: Run all migrations in order, check for typos

### Issue: Intelligence generation timing out
**Solution**: Reduce batch size in INTELLIGENCE_BATCH_SIZE env var

### Issue: Brief not appearing on dashboard
**Solution**: Check user_preferences.weekly_brief_enabled is true

### Issue: Patterns showing no data
**Solution**: Ensure user has insights/predictions generated first

### Issue: Rate limit errors from LLM
**Solution**: Check MODEL_FALLBACK_CHAIN includes free models

## 📅 Weekly Maintenance Tasks

### Every Monday After Generation
1. Check job_execution_log for failures
2. Review average generation times
3. Check cache hit rates
4. Monitor user engagement with briefs

### Monthly Tasks
1. Clean up old cache entries
2. Archive old job logs
3. Review and optimize slow queries
4. Update model fallback chain if needed

## 🎯 Success Metrics to Track

After 1 Week:
- [ ] 80%+ of active users have briefs generated
- [ ] < 5% job failure rate
- [ ] Average generation time < 5s per user
- [ ] 50%+ brief open rate

After 1 Month:
- [ ] 90%+ success rate maintained
- [ ] Cache hit rate > 80%
- [ ] User engagement increasing week-over-week
- [ ] No critical failures in production

## Emergency Contacts

If critical issues arise:
1. Check job_execution_log for errors
2. Review Railway/deployment platform logs
3. Check Supabase logs for database issues
4. Monitor OpenRouter API status
5. Check Redis connection if using caching

---

**IMPORTANT**: Complete ALL database migrations before deploying code changes!
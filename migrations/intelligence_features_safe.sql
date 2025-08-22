-- SAFE SUPABASE MIGRATION FOR INTELLIGENCE FEATURES
-- This version checks for existing objects before creating
-- Created: 2025-08-20

-- ============================================
-- 1. CREATE MISSING JOB EXECUTION LOG TABLE
-- ============================================
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

-- ============================================
-- 2. CREATE USER_PREFERENCES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE UNIQUE,
    weekly_brief_enabled BOOLEAN DEFAULT true,
    weekly_brief_frequency VARCHAR(20) DEFAULT 'weekly',
    last_brief_dismissed_at TIMESTAMP WITH TIME ZONE,
    total_briefs_dismissed INT DEFAULT 0,
    avg_engagement_time FLOAT DEFAULT 0,
    intelligence_generation_enabled BOOLEAN DEFAULT true,
    last_intelligence_generated_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- 3. CREATE INDEXES (IF NOT EXISTS)
-- ============================================
CREATE INDEX IF NOT EXISTS idx_weekly_briefs_user_id 
    ON weekly_health_briefs(user_id);
    
CREATE INDEX IF NOT EXISTS idx_weekly_briefs_week_of 
    ON weekly_health_briefs(week_of);
    
CREATE INDEX IF NOT EXISTS idx_job_execution_name_status 
    ON job_execution_log(job_name, status);
    
CREATE INDEX IF NOT EXISTS idx_job_execution_started 
    ON job_execution_log(started_at DESC);
    
CREATE INDEX IF NOT EXISTS idx_intelligence_cache_expires 
    ON intelligence_cache(expires_at);
    
CREATE INDEX IF NOT EXISTS idx_anon_patterns_hash 
    ON anonymous_symptom_patterns(pattern_hash);

-- ============================================
-- 4. ENABLE RLS (Safe - won't error if already enabled)
-- ============================================
ALTER TABLE weekly_health_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE intelligence_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_execution_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- ============================================
-- 5. DROP AND RECREATE POLICIES (Safe approach)
-- ============================================

-- Weekly Health Briefs Policies
DROP POLICY IF EXISTS "Users can view their own briefs" ON weekly_health_briefs;
CREATE POLICY "Users can view their own briefs"
    ON weekly_health_briefs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can create their own briefs" ON weekly_health_briefs;
CREATE POLICY "Users can create their own briefs"
    ON weekly_health_briefs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own briefs" ON weekly_health_briefs;
CREATE POLICY "Users can update their own briefs"
    ON weekly_health_briefs FOR UPDATE
    USING (auth.uid() = user_id);

-- Intelligence Cache Policies
DROP POLICY IF EXISTS "Users can view their own cache" ON intelligence_cache;
CREATE POLICY "Users can view their own cache"
    ON intelligence_cache FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own cache" ON intelligence_cache;
CREATE POLICY "Users can manage their own cache"
    ON intelligence_cache FOR ALL
    USING (auth.uid() = user_id);

-- User Preferences Policies
DROP POLICY IF EXISTS "Users can view their own preferences" ON user_preferences;
CREATE POLICY "Users can view their own preferences"
    ON user_preferences FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can manage their own preferences" ON user_preferences;
CREATE POLICY "Users can manage their own preferences"
    ON user_preferences FOR ALL
    USING (auth.uid() = user_id);

-- Job Execution Log Policies
DROP POLICY IF EXISTS "Service role can manage job logs" ON job_execution_log;
CREATE POLICY "Service role can manage job logs"
    ON job_execution_log FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================
-- 6. GRANT PERMISSIONS (Safe - won't error)
-- ============================================
GRANT ALL ON weekly_health_briefs TO authenticated;
GRANT ALL ON intelligence_cache TO authenticated;
GRANT ALL ON anonymous_symptom_patterns TO authenticated;
GRANT ALL ON job_execution_log TO service_role;
GRANT ALL ON user_preferences TO authenticated;

-- ============================================
-- 7. CREATE MONITORING VIEW
-- ============================================
DROP VIEW IF EXISTS intelligence_health_dashboard;
CREATE VIEW intelligence_health_dashboard AS
SELECT 
    DATE_TRUNC('day', created_at) as date,
    COUNT(DISTINCT user_id) as briefs_generated,
    AVG(EXTRACT(EPOCH FROM (last_opened_at - created_at))) as avg_time_to_open,
    COUNT(CASE WHEN last_opened_at IS NOT NULL THEN 1 END)::FLOAT / COUNT(*) as open_rate
FROM weekly_health_briefs
GROUP BY DATE_TRUNC('day', created_at);

-- Grant access to the view
GRANT SELECT ON intelligence_health_dashboard TO authenticated;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================
-- After running this migration, check these:

-- 1. Verify tables exist:
SELECT required.table_name, 
       CASE WHEN t.table_name IS NOT NULL THEN '✅ Created' ELSE '❌ Missing' END as status
FROM (
    VALUES 
    ('weekly_health_briefs'),
    ('job_execution_log'),
    ('intelligence_cache'),
    ('anonymous_symptom_patterns'),
    ('user_preferences')
) AS required(table_name)
LEFT JOIN information_schema.tables t 
    ON t.table_schema = 'public' 
    AND t.table_name = required.table_name;

-- 2. Verify RLS is enabled:
SELECT tablename, 
       CASE WHEN rowsecurity THEN '✅ Enabled' ELSE '❌ Disabled' END as rls_status
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('weekly_health_briefs', 'intelligence_cache', 'job_execution_log', 'user_preferences');

-- 3. Verify policies exist:
SELECT tablename, COUNT(*) as policy_count 
FROM pg_policies 
WHERE schemaname = 'public'
AND tablename IN ('weekly_health_briefs', 'intelligence_cache', 'job_execution_log', 'user_preferences')
GROUP BY tablename;
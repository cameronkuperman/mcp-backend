-- Migration: Convert intelligence tables to use text user_id for consistency
-- This makes intelligence tables compatible with the rest of the application

-- 1. Drop foreign key constraints first
ALTER TABLE weekly_health_briefs DROP CONSTRAINT IF EXISTS weekly_health_briefs_user_id_fkey;
ALTER TABLE health_insights DROP CONSTRAINT IF EXISTS health_insights_user_id_fkey;
ALTER TABLE health_predictions DROP CONSTRAINT IF EXISTS health_predictions_user_id_fkey;
ALTER TABLE shadow_patterns DROP CONSTRAINT IF EXISTS shadow_patterns_user_id_fkey;
ALTER TABLE strategic_moves DROP CONSTRAINT IF EXISTS strategic_moves_user_id_fkey;
ALTER TABLE intelligence_cache DROP CONSTRAINT IF EXISTS intelligence_cache_user_id_fkey;
ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;
ALTER TABLE analysis_generation_log DROP CONSTRAINT IF EXISTS analysis_generation_log_user_id_fkey;

-- 2. Convert user_id columns from uuid to text
ALTER TABLE weekly_health_briefs ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE health_insights ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE health_predictions ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE shadow_patterns ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE strategic_moves ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE intelligence_cache ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE user_preferences ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE analysis_generation_log ALTER COLUMN user_id TYPE text USING user_id::text;

-- 3. Update any other related tables that might reference these
ALTER TABLE health_stories ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE story_notes ALTER COLUMN user_id TYPE text USING user_id::text;
ALTER TABLE user_refresh_limits ALTER COLUMN user_id TYPE text USING user_id::text;

-- 4. Create indexes for performance (text columns need indexes for queries)
CREATE INDEX IF NOT EXISTS idx_weekly_health_briefs_user_id ON weekly_health_briefs(user_id);
CREATE INDEX IF NOT EXISTS idx_health_insights_user_id ON health_insights(user_id);
CREATE INDEX IF NOT EXISTS idx_health_predictions_user_id ON health_predictions(user_id);
CREATE INDEX IF NOT EXISTS idx_shadow_patterns_user_id ON shadow_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_strategic_moves_user_id ON strategic_moves(user_id);
CREATE INDEX IF NOT EXISTS idx_intelligence_cache_user_id ON intelligence_cache(user_id);

-- 5. Add composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_weekly_health_briefs_user_week ON weekly_health_briefs(user_id, week_of);
CREATE INDEX IF NOT EXISTS idx_health_insights_user_week ON health_insights(user_id, week_of);
CREATE INDEX IF NOT EXISTS idx_health_predictions_user_week ON health_predictions(user_id, week_of);

-- Note: After this migration, all user_id fields will be text type
-- This matches the pattern used in quick_scans, symptom_tracking, etc.
-- No foreign key to auth.users - allows flexibility for different auth providers
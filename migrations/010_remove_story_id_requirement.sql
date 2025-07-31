-- Migration: Remove story_id requirement from health_insights and add performance indexes
-- Date: 2025-01-31
-- Purpose: Allow insights to be generated independently of stories

-- Make story_id nullable in health_insights table
ALTER TABLE health_insights ALTER COLUMN story_id DROP NOT NULL;

-- Add performance indexes for week-based queries
CREATE INDEX IF NOT EXISTS idx_health_insights_week ON health_insights(user_id, week_of);
CREATE INDEX IF NOT EXISTS idx_shadow_patterns_week ON shadow_patterns(user_id, week_of);
CREATE INDEX IF NOT EXISTS idx_health_predictions_week ON health_predictions(user_id, week_of);
CREATE INDEX IF NOT EXISTS idx_strategic_moves_week ON strategic_moves(user_id, week_of);

-- Add index for efficient weekly queries with status
CREATE INDEX IF NOT EXISTS idx_health_insights_week_created ON health_insights(user_id, week_of, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_shadow_patterns_week_created ON shadow_patterns(user_id, week_of, created_at DESC);

-- Add composite index for the background job queries
CREATE INDEX IF NOT EXISTS idx_user_ai_prefs_generation ON user_ai_preferences(weekly_generation_enabled, preferred_day_of_week, preferred_hour);

-- Update existing NULL story_ids to a placeholder if needed (optional)
-- UPDATE health_insights SET story_id = NULL WHERE story_id = '00000000-0000-0000-0000-000000000000';

COMMENT ON COLUMN health_insights.story_id IS 'Optional reference to health story - insights can be generated independently';
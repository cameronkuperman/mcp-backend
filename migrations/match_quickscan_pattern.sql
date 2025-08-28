-- Migration: Make intelligence tables consistent with quick_scan/deep_dive pattern
-- This removes FK constraints but keeps UUID types, matching the working pattern

-- ============================================
-- INTELLIGENCE CORE TABLES
-- ============================================

-- Weekly Health Briefs (main intelligence feature)
ALTER TABLE weekly_health_briefs DROP CONSTRAINT IF EXISTS weekly_health_briefs_user_id_fkey;

-- Health Insights (AI-generated insights)
ALTER TABLE health_insights DROP CONSTRAINT IF EXISTS health_insights_user_id_fkey;

-- Health Predictions (AI predictions)
ALTER TABLE health_predictions DROP CONSTRAINT IF EXISTS health_predictions_user_id_fkey;

-- Shadow Patterns (stopped tracking patterns)
ALTER TABLE shadow_patterns DROP CONSTRAINT IF EXISTS shadow_patterns_user_id_fkey;

-- Strategic Moves (AI recommendations)
ALTER TABLE strategic_moves DROP CONSTRAINT IF EXISTS strategic_moves_user_id_fkey;

-- Intelligence Cache
ALTER TABLE intelligence_cache DROP CONSTRAINT IF EXISTS intelligence_cache_user_id_fkey;

-- ============================================
-- INTELLIGENCE SUPPORT TABLES
-- ============================================

-- User Preferences (for intelligence features)
ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;

-- Analysis Generation Log
ALTER TABLE analysis_generation_log DROP CONSTRAINT IF EXISTS analysis_generation_log_user_id_fkey;

-- User Refresh Limits
ALTER TABLE user_refresh_limits DROP CONSTRAINT IF EXISTS user_refresh_limits_user_id_fkey;

-- ============================================
-- STORY RELATED TABLES
-- ============================================

-- Health Stories
ALTER TABLE health_stories DROP CONSTRAINT IF EXISTS health_stories_user_id_fkey;

-- Story Notes
ALTER TABLE story_notes DROP CONSTRAINT IF EXISTS story_notes_user_id_fkey;

-- ============================================
-- OTHER TABLES THAT MIGHT BLOCK INTELLIGENCE
-- ============================================

-- LLM Context (might reference medical.id)
ALTER TABLE llm_context DROP CONSTRAINT IF EXISTS llm_context_user_id_fkey;

-- ============================================
-- NOTES
-- ============================================
-- After this migration:
-- 1. Intelligence tables will work like quick_scan/deep_dive (no FK constraints)
-- 2. Backend code will enforce medical profile requirement
-- 3. User IDs remain as UUID type (no data type changes)
-- 4. This matches your existing working pattern

-- To rollback (if needed):
-- You can re-add constraints later once all users are properly in auth.users
-- Example: ALTER TABLE weekly_health_briefs ADD CONSTRAINT weekly_health_briefs_user_id_fkey 
--          FOREIGN KEY (user_id) REFERENCES auth.users(id);
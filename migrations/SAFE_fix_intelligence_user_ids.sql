-- SAFER Migration: Fix intelligence tables user_id compatibility
-- This version only removes constraints, doesn't change data types
-- Run this first to test, then run full migration if needed

-- STEP 1: Just remove the foreign key constraints (SAFE - reversible)
-- This allows non-auth users to use intelligence features
ALTER TABLE weekly_health_briefs DROP CONSTRAINT IF EXISTS weekly_health_briefs_user_id_fkey;
ALTER TABLE health_insights DROP CONSTRAINT IF EXISTS health_insights_user_id_fkey;
ALTER TABLE health_predictions DROP CONSTRAINT IF EXISTS health_predictions_user_id_fkey;
ALTER TABLE shadow_patterns DROP CONSTRAINT IF EXISTS shadow_patterns_user_id_fkey;
ALTER TABLE strategic_moves DROP CONSTRAINT IF EXISTS strategic_moves_user_id_fkey;
ALTER TABLE intelligence_cache DROP CONSTRAINT IF EXISTS intelligence_cache_user_id_fkey;
ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;
ALTER TABLE analysis_generation_log DROP CONSTRAINT IF EXISTS analysis_generation_log_user_id_fkey;

-- That's it! This minimal change will:
-- 1. Allow intelligence features to work with users not in auth.users
-- 2. Keep UUID format for user_id (no data type changes)
-- 3. Be easily reversible if needed

-- After running this, test intelligence generation
-- If it still fails due to UUID format issues, then consider the full migration
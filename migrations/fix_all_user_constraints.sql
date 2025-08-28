-- Fix ALL user constraints to support mixed user types
-- Your app supports: anonymous, medical profile, and auth users

-- 1. Remove foreign key constraints from intelligence tables
ALTER TABLE weekly_health_briefs DROP CONSTRAINT IF EXISTS weekly_health_briefs_user_id_fkey;
ALTER TABLE health_insights DROP CONSTRAINT IF EXISTS health_insights_user_id_fkey;
ALTER TABLE health_predictions DROP CONSTRAINT IF EXISTS health_predictions_user_id_fkey;
ALTER TABLE shadow_patterns DROP CONSTRAINT IF EXISTS shadow_patterns_user_id_fkey;
ALTER TABLE strategic_moves DROP CONSTRAINT IF EXISTS strategic_moves_user_id_fkey;
ALTER TABLE intelligence_cache DROP CONSTRAINT IF EXISTS intelligence_cache_user_id_fkey;
ALTER TABLE user_preferences DROP CONSTRAINT IF EXISTS user_preferences_user_id_fkey;
ALTER TABLE analysis_generation_log DROP CONSTRAINT IF EXISTS analysis_generation_log_user_id_fkey;

-- 2. Remove foreign key from llm_context to medical
ALTER TABLE llm_context DROP CONSTRAINT IF EXISTS llm_context_user_id_fkey;

-- 3. Remove any other user foreign keys
ALTER TABLE health_stories DROP CONSTRAINT IF EXISTS health_stories_user_id_fkey;
ALTER TABLE story_notes DROP CONSTRAINT IF EXISTS story_notes_user_id_fkey;
ALTER TABLE user_refresh_limits DROP CONSTRAINT IF EXISTS user_refresh_limits_user_id_fkey;
ALTER TABLE assessment_chains DROP CONSTRAINT IF EXISTS assessment_chains_user_id_fkey;
ALTER TABLE assessment_follow_ups DROP CONSTRAINT IF EXISTS assessment_follow_ups_user_id_fkey;
ALTER TABLE flash_assessments DROP CONSTRAINT IF EXISTS flash_assessments_user_id_fkey;
ALTER TABLE follow_up_events DROP CONSTRAINT IF EXISTS follow_up_events_user_id_fkey;
ALTER TABLE follow_up_schedules DROP CONSTRAINT IF EXISTS follow_up_schedules_user_id_fkey;
ALTER TABLE follow_up_sessions DROP CONSTRAINT IF EXISTS follow_up_sessions_user_id_fkey;
ALTER TABLE follow_ups DROP CONSTRAINT IF EXISTS follow_ups_user_id_fkey;
ALTER TABLE general_assessment_refinements DROP CONSTRAINT IF EXISTS general_assessment_refinements_user_id_fkey;
ALTER TABLE general_assessments DROP CONSTRAINT IF EXISTS general_assessments_user_id_fkey;
ALTER TABLE general_deepdive_sessions DROP CONSTRAINT IF EXISTS general_deepdive_sessions_user_id_fkey;
ALTER TABLE medical_visits DROP CONSTRAINT IF EXISTS medical_visits_user_id_fkey;
ALTER TABLE photo_importance_markers DROP CONSTRAINT IF EXISTS photo_importance_markers_user_id_fkey;
ALTER TABLE photo_sessions DROP CONSTRAINT IF EXISTS photo_sessions_user_id_fkey;
ALTER TABLE photo_tracking_configurations DROP CONSTRAINT IF EXISTS photo_tracking_configurations_user_id_fkey;
ALTER TABLE timeline_events DROP CONSTRAINT IF EXISTS timeline_events_user_id_fkey;
ALTER TABLE user_profiles DROP CONSTRAINT IF EXISTS user_profiles_user_id_fkey;
ALTER TABLE user_tutorials DROP CONSTRAINT IF EXISTS user_tutorials_user_id_fkey;
ALTER TABLE subscription_events DROP CONSTRAINT IF EXISTS subscription_events_user_id_fkey;
ALTER TABLE subscriptions DROP CONSTRAINT IF EXISTS subscriptions_user_id_fkey;

-- This allows your app to work with:
-- 1. Anonymous users (just a generated UUID)
-- 2. Medical profile users (medical.id)
-- 3. Auth users (auth.users.id)
-- 4. Any combination of the above

-- The app can determine user type by checking:
-- - EXISTS in auth.users = authenticated
-- - EXISTS in medical = has medical profile
-- - Neither = anonymous user
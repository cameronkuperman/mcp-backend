-- Migration: Fix user_id data type inconsistency
-- Date: 2025-01-30
-- Description: Changes user_id from UUID to TEXT in health intelligence tables to match the rest of the system

-- Drop existing constraints and indexes first
DROP INDEX IF EXISTS idx_health_insights_user_story;
DROP INDEX IF EXISTS idx_health_predictions_user_week;
DROP INDEX IF EXISTS idx_shadow_patterns_user_week;
DROP INDEX IF EXISTS idx_strategic_moves_user_week;
DROP INDEX IF EXISTS idx_refresh_limits_user_week;

-- Alter tables to use TEXT instead of UUID for user_id
ALTER TABLE public.health_insights 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.health_predictions 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.shadow_patterns 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.strategic_moves 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.analysis_generation_log 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.user_refresh_limits 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

ALTER TABLE public.export_history 
  ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;

-- Recreate indexes with the new data type
CREATE INDEX idx_health_insights_user_story ON public.health_insights(user_id, story_id);
CREATE INDEX idx_health_predictions_user_week ON public.health_predictions(user_id, week_of);
CREATE INDEX idx_shadow_patterns_user_week ON public.shadow_patterns(user_id, week_of);
CREATE INDEX idx_strategic_moves_user_week ON public.strategic_moves(user_id, week_of);
CREATE INDEX idx_refresh_limits_user_week ON public.user_refresh_limits(user_id, week_of);
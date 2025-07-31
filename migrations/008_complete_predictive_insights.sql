-- Migration: Complete Predictive Insights System
-- Purpose: Fix failed caching migration and support all AI prediction endpoints
-- Date: 2025-01-31

-- 1. Drop existing failed components safely
DROP TRIGGER IF EXISTS set_expiry_trigger ON public.weekly_ai_predictions;
DROP FUNCTION IF EXISTS set_prediction_expiry() CASCADE;
DROP VIEW IF EXISTS current_ai_predictions CASCADE;
DROP FUNCTION IF EXISTS get_cached_prediction(text, text, boolean) CASCADE;
DROP FUNCTION IF EXISTS regenerate_expired_predictions() CASCADE;

-- 2. Fix weekly_ai_predictions table structure
-- Add missing columns if they don't exist
DO $$ 
BEGIN
    -- Add prediction_type column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'weekly_ai_predictions' 
                   AND column_name = 'prediction_type') THEN
        ALTER TABLE public.weekly_ai_predictions 
        ADD COLUMN prediction_type text DEFAULT 'weekly';
    END IF;

    -- Add expires_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'weekly_ai_predictions' 
                   AND column_name = 'expires_at') THEN
        ALTER TABLE public.weekly_ai_predictions 
        ADD COLUMN expires_at timestamp with time zone;
    END IF;

    -- Add regenerate_after column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'weekly_ai_predictions' 
                   AND column_name = 'regenerate_after') THEN
        ALTER TABLE public.weekly_ai_predictions 
        ADD COLUMN regenerate_after timestamp with time zone;
    END IF;

    -- Add metadata column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'weekly_ai_predictions' 
                   AND column_name = 'metadata') THEN
        ALTER TABLE public.weekly_ai_predictions 
        ADD COLUMN metadata jsonb DEFAULT '{}';
    END IF;

    -- Add force_refresh_count column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'weekly_ai_predictions' 
                   AND column_name = 'force_refresh_count') THEN
        ALTER TABLE public.weekly_ai_predictions 
        ADD COLUMN force_refresh_count integer DEFAULT 0;
    END IF;
END $$;

-- 3. Update prediction_type constraint to include all types
ALTER TABLE public.weekly_ai_predictions 
DROP CONSTRAINT IF EXISTS weekly_ai_predictions_prediction_type_check;

ALTER TABLE public.weekly_ai_predictions 
ADD CONSTRAINT weekly_ai_predictions_prediction_type_check 
CHECK (prediction_type IN ('weekly', 'seasonal', 'longterm', 'immediate', 'patterns', 'questions', 'dashboard'));

-- 4. Create function to set expiry dates based on prediction type
CREATE OR REPLACE FUNCTION set_prediction_expiry()
RETURNS TRIGGER AS $$
BEGIN
  -- Set expiry based on prediction type
  CASE NEW.prediction_type
    WHEN 'dashboard' THEN
      -- Dashboard alerts expire in 7 days
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '7 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
    WHEN 'immediate' THEN
      -- 7-day predictions expire in 7 days
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '7 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
    WHEN 'seasonal' THEN
      -- Seasonal predictions last 30 days, regenerate after 14
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '30 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '14 days');
    WHEN 'longterm' THEN
      -- Long-term predictions last 90 days, regenerate after 30
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '90 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '30 days');
    WHEN 'patterns' THEN
      -- Body patterns expire in 14 days, regenerate after 7
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '14 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
    WHEN 'questions' THEN
      -- Pattern questions expire in 14 days, regenerate after 7
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '14 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
    WHEN 'weekly' THEN
      -- Weekly compilation expires in 7 days
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '7 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
    ELSE
      -- Default to 7 days
      NEW.expires_at := COALESCE(NEW.expires_at, NEW.generated_at + INTERVAL '7 days');
      NEW.regenerate_after := COALESCE(NEW.regenerate_after, NEW.generated_at + INTERVAL '7 days');
  END CASE;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 5. Create trigger for auto-expiry
CREATE TRIGGER set_expiry_trigger
BEFORE INSERT OR UPDATE ON public.weekly_ai_predictions
FOR EACH ROW 
EXECUTE FUNCTION set_prediction_expiry();

-- 6. Create comprehensive indexes for performance
-- Drop existing indexes first to avoid duplicates
DROP INDEX IF EXISTS idx_predictions_lookup;
DROP INDEX IF EXISTS idx_predictions_expiry;
DROP INDEX IF EXISTS idx_weekly_predictions_user_current;
DROP INDEX IF EXISTS idx_predictions_type_current;
DROP INDEX IF EXISTS idx_predictions_metadata;

-- Create optimized indexes
CREATE INDEX IF NOT EXISTS idx_predictions_lookup 
ON public.weekly_ai_predictions(user_id, prediction_type, is_current, expires_at)
WHERE is_current = true;

CREATE INDEX IF NOT EXISTS idx_predictions_expiry
ON public.weekly_ai_predictions(expires_at)
WHERE is_current = true AND generation_status = 'completed';

CREATE INDEX IF NOT EXISTS idx_predictions_type_current
ON public.weekly_ai_predictions(prediction_type, is_current)
WHERE is_current = true;

-- Add JSONB indexes for pattern queries
CREATE INDEX IF NOT EXISTS idx_predictions_metadata_gin
ON public.weekly_ai_predictions USING gin(metadata);

CREATE INDEX IF NOT EXISTS idx_predictions_patterns_gin
ON public.weekly_ai_predictions USING gin(body_patterns);

CREATE INDEX IF NOT EXISTS idx_predictions_questions_gin
ON public.weekly_ai_predictions USING gin(pattern_questions);

-- 7. Create view for easy access to current valid predictions
CREATE OR REPLACE VIEW current_ai_predictions AS
SELECT 
  id,
  user_id,
  prediction_type,
  dashboard_alert,
  predictions,
  pattern_questions,
  body_patterns,
  metadata,
  generated_at,
  expires_at,
  regenerate_after,
  data_quality_score,
  viewed_at,
  force_refresh_count,
  CASE 
    WHEN expires_at > CURRENT_TIMESTAMP THEN true 
    ELSE false 
  END as is_valid,
  CASE 
    WHEN regenerate_after < CURRENT_TIMESTAMP THEN true 
    ELSE false 
  END as update_available,
  EXTRACT(EPOCH FROM (expires_at - CURRENT_TIMESTAMP)) as seconds_until_expiry
FROM public.weekly_ai_predictions
WHERE is_current = true
  AND generation_status = 'completed';

-- 8. Create smart cache retrieval function
CREATE OR REPLACE FUNCTION get_cached_prediction(
  p_user_id text,
  p_prediction_type text,
  p_force_refresh boolean DEFAULT false
)
RETURNS jsonb AS $$
DECLARE
  v_result jsonb;
BEGIN
  -- If forcing refresh, return null immediately
  IF p_force_refresh THEN
    RETURN null;
  END IF;
  
  -- Try to get cached data that hasn't expired
  SELECT jsonb_build_object(
    'id', id,
    'user_id', user_id,
    'prediction_type', prediction_type,
    'dashboard_alert', dashboard_alert,
    'predictions', predictions,
    'pattern_questions', pattern_questions,
    'body_patterns', body_patterns,
    'metadata', metadata,
    'generated_at', generated_at,
    'expires_at', expires_at,
    'regenerate_after', regenerate_after,
    'data_quality_score', data_quality_score,
    'viewed_at', viewed_at,
    'is_valid', CASE WHEN expires_at > CURRENT_TIMESTAMP THEN true ELSE false END,
    'update_available', CASE WHEN regenerate_after < CURRENT_TIMESTAMP THEN true ELSE false END,
    'seconds_until_expiry', EXTRACT(EPOCH FROM (expires_at - CURRENT_TIMESTAMP))
  ) INTO v_result
  FROM public.weekly_ai_predictions
  WHERE user_id = p_user_id 
    AND prediction_type = p_prediction_type
    AND is_current = true
    AND generation_status = 'completed'
    AND expires_at > CURRENT_TIMESTAMP
  ORDER BY generated_at DESC
  LIMIT 1;
  
  RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- 9. Create function to mark old predictions as not current
CREATE OR REPLACE FUNCTION mark_old_predictions_not_current()
RETURNS TRIGGER AS $$
BEGIN
    -- When inserting/updating a completed prediction, mark others as not current
    IF NEW.generation_status = 'completed' AND NEW.is_current = true THEN
        UPDATE weekly_ai_predictions 
        SET is_current = false, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = NEW.user_id 
        AND prediction_type = NEW.prediction_type
        AND id != NEW.id
        AND is_current = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Recreate trigger with better logic
DROP TRIGGER IF EXISTS update_current_predictions ON weekly_ai_predictions;
CREATE TRIGGER update_current_predictions 
AFTER INSERT OR UPDATE OF generation_status, is_current ON weekly_ai_predictions
FOR EACH ROW 
WHEN (NEW.generation_status = 'completed' AND NEW.is_current = true)
EXECUTE FUNCTION mark_old_predictions_not_current();

-- 10. Create ai_prediction_stats table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.ai_prediction_stats (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id text NOT NULL,
  prediction_type text NOT NULL,
  generation_time_ms integer,
  cache_hit boolean DEFAULT false,
  forced_refresh boolean DEFAULT false,
  error_occurred boolean DEFAULT false,
  error_message text,
  model_used text,
  data_quality_score integer,
  created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- Create index for stats
CREATE INDEX IF NOT EXISTS idx_prediction_stats_lookup
ON public.ai_prediction_stats(user_id, prediction_type, created_at DESC);

-- 11. Function to get expired predictions that need regeneration
CREATE OR REPLACE FUNCTION get_predictions_needing_refresh()
RETURNS TABLE(
  user_id text, 
  prediction_type text, 
  last_generated timestamp with time zone,
  expired_at timestamp with time zone
) AS $$
BEGIN
  RETURN QUERY
  SELECT DISTINCT 
    wap.user_id,
    wap.prediction_type,
    wap.generated_at as last_generated,
    wap.expires_at as expired_at
  FROM public.weekly_ai_predictions wap
  JOIN public.user_ai_preferences uap ON wap.user_id = uap.user_id
  WHERE wap.is_current = true
    AND wap.generation_status = 'completed'
    AND wap.expires_at < CURRENT_TIMESTAMP
    AND uap.weekly_generation_enabled = true
    AND wap.prediction_type IN ('seasonal', 'longterm', 'patterns', 'questions')
  ORDER BY wap.expires_at ASC;
END;
$$ LANGUAGE plpgsql;

-- 12. Update existing data to have proper metadata
UPDATE public.weekly_ai_predictions 
SET 
  prediction_type = COALESCE(prediction_type, 'weekly'),
  metadata = COALESCE(metadata, '{}')
WHERE prediction_type IS NULL OR metadata IS NULL;

-- 13. Create RLS policies if they don't exist
ALTER TABLE public.weekly_ai_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_prediction_stats ENABLE ROW LEVEL SECURITY;

-- Drop and recreate policies to ensure consistency
DROP POLICY IF EXISTS "Users can view their own predictions" ON public.weekly_ai_predictions;
DROP POLICY IF EXISTS "System can manage all predictions" ON public.weekly_ai_predictions;
DROP POLICY IF EXISTS "Service role can manage all predictions" ON public.weekly_ai_predictions;

CREATE POLICY "Users can view their own predictions" 
ON public.weekly_ai_predictions 
FOR SELECT 
USING (auth.uid()::text = user_id);

CREATE POLICY "System can manage all predictions" 
ON public.weekly_ai_predictions 
FOR ALL 
USING (auth.role() = 'service_role');

-- Policies for stats table
DO $$ 
BEGIN
    -- Check and create user select policy for stats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ai_prediction_stats' 
        AND policyname = 'Users can view their own stats'
    ) THEN
        CREATE POLICY "Users can view their own stats" 
        ON public.ai_prediction_stats 
        FOR SELECT 
        USING (auth.uid()::text = user_id);
    END IF;

    -- Check and create service role policy for stats
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'ai_prediction_stats' 
        AND policyname = 'System can manage all stats'
    ) THEN
        CREATE POLICY "System can manage all stats" 
        ON public.ai_prediction_stats 
        FOR ALL 
        USING (auth.role() = 'service_role');
    END IF;
END $$;

-- 14. Add helpful comments
COMMENT ON TABLE public.weekly_ai_predictions IS 'Stores all AI predictions with smart caching. Supports dashboard alerts, immediate/seasonal/longterm predictions, body patterns, and pattern questions.';
COMMENT ON COLUMN public.weekly_ai_predictions.prediction_type IS 'Type of prediction: dashboard, immediate, seasonal, longterm, patterns, questions, weekly';
COMMENT ON COLUMN public.weekly_ai_predictions.dashboard_alert IS 'Single alert object with severity, title, description for dashboard display';
COMMENT ON COLUMN public.weekly_ai_predictions.predictions IS 'Array of prediction objects (structure varies by type)';
COMMENT ON COLUMN public.weekly_ai_predictions.pattern_questions IS 'Array of question objects with deep_dive analysis';
COMMENT ON COLUMN public.weekly_ai_predictions.body_patterns IS 'Object with tendencies and positiveResponses arrays';
COMMENT ON COLUMN public.weekly_ai_predictions.expires_at IS 'When this prediction expires and needs regeneration';
COMMENT ON COLUMN public.weekly_ai_predictions.regenerate_after IS 'When to suggest regeneration (before expiry)';

-- 15. Grant necessary permissions
GRANT SELECT ON current_ai_predictions TO authenticated;
GRANT EXECUTE ON FUNCTION get_cached_prediction TO authenticated;
GRANT EXECUTE ON FUNCTION get_predictions_needing_refresh TO service_role;

-- Migration completed successfully
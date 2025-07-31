-- Migration: Add smart caching for AI predictions
-- Purpose: Enable caching of seasonal and long-term predictions with automatic expiry

-- 1. Add new columns to weekly_ai_predictions table
ALTER TABLE public.weekly_ai_predictions 
ADD COLUMN IF NOT EXISTS prediction_type text DEFAULT 'weekly' 
  CHECK (prediction_type IN ('weekly', 'seasonal', 'longterm', 'immediate', 'patterns', 'questions', 'dashboard')),
ADD COLUMN IF NOT EXISTS expires_at timestamp with time zone,
ADD COLUMN IF NOT EXISTS regenerate_after timestamp with time zone,
ADD COLUMN IF NOT EXISTS metadata jsonb DEFAULT '{}',
ADD COLUMN IF NOT EXISTS force_refresh_count integer DEFAULT 0;

-- 2. Create function to set expiry dates based on prediction type
CREATE OR REPLACE FUNCTION set_prediction_expiry()
RETURNS TRIGGER AS $$
BEGIN
  -- Set expiry based on prediction type
  CASE NEW.prediction_type
    WHEN 'weekly' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '7 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
    WHEN 'seasonal' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '30 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '14 days';
    WHEN 'longterm' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '90 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '30 days';
    WHEN 'immediate' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '7 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
    WHEN 'patterns' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '14 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
    WHEN 'questions' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '14 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
    WHEN 'dashboard' THEN
      NEW.expires_at := NEW.generated_at + INTERVAL '7 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
    ELSE
      -- Default to weekly
      NEW.expires_at := NEW.generated_at + INTERVAL '7 days';
      NEW.regenerate_after := NEW.generated_at + INTERVAL '7 days';
  END CASE;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create trigger for auto-expiry
CREATE TRIGGER set_expiry_trigger
BEFORE INSERT ON public.weekly_ai_predictions
FOR EACH ROW 
WHEN (NEW.expires_at IS NULL)
EXECUTE FUNCTION set_prediction_expiry();

-- 4. Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_predictions_lookup 
ON public.weekly_ai_predictions(user_id, prediction_type, is_current)
WHERE is_current = true;

CREATE INDEX IF NOT EXISTS idx_predictions_expiry
ON public.weekly_ai_predictions(expires_at)
WHERE is_current = true;

-- 5. Create a view for easy access to current valid predictions
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
  CASE 
    WHEN expires_at > CURRENT_TIMESTAMP THEN true 
    ELSE false 
  END as is_valid,
  CASE 
    WHEN regenerate_after < CURRENT_TIMESTAMP THEN true 
    ELSE false 
  END as update_available
FROM public.weekly_ai_predictions
WHERE is_current = true;

-- 6. Create function to get or generate predictions
CREATE OR REPLACE FUNCTION get_cached_prediction(
  p_user_id text,
  p_prediction_type text,
  p_force_refresh boolean DEFAULT false
)
RETURNS jsonb AS $$
DECLARE
  v_result jsonb;
BEGIN
  -- If not forcing refresh, try to get cached data
  IF NOT p_force_refresh THEN
    SELECT row_to_json(t) INTO v_result
    FROM (
      SELECT 
        *,
        CASE 
          WHEN expires_at > CURRENT_TIMESTAMP THEN true 
          ELSE false 
        END as is_valid,
        CASE 
          WHEN regenerate_after < CURRENT_TIMESTAMP THEN true 
          ELSE false 
        END as update_available
      FROM public.weekly_ai_predictions
      WHERE user_id = p_user_id 
        AND prediction_type = p_prediction_type
        AND is_current = true
        AND expires_at > CURRENT_TIMESTAMP
      LIMIT 1
    ) t;
    
    IF v_result IS NOT NULL THEN
      RETURN v_result;
    END IF;
  END IF;
  
  -- Return null to indicate need for generation
  RETURN null;
END;
$$ LANGUAGE plpgsql;

-- 7. Create stored procedure for background regeneration
CREATE OR REPLACE FUNCTION regenerate_expired_predictions()
RETURNS TABLE(user_id text, prediction_type text, regenerated boolean) AS $$
BEGIN
  RETURN QUERY
  WITH expired_predictions AS (
    SELECT DISTINCT 
      wap.user_id,
      wap.prediction_type
    FROM public.weekly_ai_predictions wap
    WHERE wap.is_current = true
      AND wap.expires_at < CURRENT_TIMESTAMP
      AND wap.prediction_type IN ('seasonal', 'longterm')
  )
  SELECT 
    ep.user_id,
    ep.prediction_type,
    false as regenerated -- Backend will handle actual regeneration
  FROM expired_predictions ep;
END;
$$ LANGUAGE plpgsql;

-- 8. Update existing data to have proper types
UPDATE public.weekly_ai_predictions 
SET prediction_type = 'weekly',
    expires_at = generated_at + INTERVAL '7 days',
    regenerate_after = generated_at + INTERVAL '7 days'
WHERE prediction_type IS NULL;

-- 9. Create table for tracking prediction generation stats
CREATE TABLE IF NOT EXISTS public.ai_prediction_stats (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  prediction_type text NOT NULL,
  generation_time_ms integer,
  cache_hit boolean DEFAULT false,
  forced_refresh boolean DEFAULT false,
  error_occurred boolean DEFAULT false,
  error_message text,
  created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT ai_prediction_stats_pkey PRIMARY KEY (id)
);

-- 10. Add RLS policies if needed
ALTER TABLE public.weekly_ai_predictions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own predictions" 
ON public.weekly_ai_predictions 
FOR SELECT 
USING (auth.uid()::text = user_id);

CREATE POLICY "System can manage all predictions" 
ON public.weekly_ai_predictions 
FOR ALL 
USING (auth.role() = 'service_role');

-- Create index for stats
CREATE INDEX IF NOT EXISTS idx_prediction_stats_lookup
ON public.ai_prediction_stats(user_id, prediction_type, created_at DESC);

-- Add comment
COMMENT ON TABLE public.weekly_ai_predictions IS 'Stores all AI predictions with smart caching and expiry. Supports weekly, seasonal, and long-term predictions.';
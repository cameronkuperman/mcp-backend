-- Migration: Health Intelligence Improvements for On-Demand Generation
-- Purpose: Add generation tracking and improve caching for individual endpoint calls
-- Date: 2025-01-31

-- 1. Add generation method tracking to existing tables
ALTER TABLE public.health_insights 
ADD COLUMN IF NOT EXISTS generation_method VARCHAR(20) DEFAULT 'weekly' 
CHECK (generation_method IN ('weekly', 'on_demand', 'auto'));

ALTER TABLE public.health_predictions 
ADD COLUMN IF NOT EXISTS generation_method VARCHAR(20) DEFAULT 'weekly' 
CHECK (generation_method IN ('weekly', 'on_demand', 'auto'));

ALTER TABLE public.shadow_patterns 
ADD COLUMN IF NOT EXISTS generation_method VARCHAR(20) DEFAULT 'weekly' 
CHECK (generation_method IN ('weekly', 'on_demand', 'auto'));

ALTER TABLE public.strategic_moves 
ADD COLUMN IF NOT EXISTS generation_method VARCHAR(20) DEFAULT 'weekly' 
CHECK (generation_method IN ('weekly', 'on_demand', 'auto'));

-- 2. Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_health_insights_generation 
ON public.health_insights(user_id, week_of, generation_method);

CREATE INDEX IF NOT EXISTS idx_health_predictions_generation 
ON public.health_predictions(user_id, week_of, generation_method);

CREATE INDEX IF NOT EXISTS idx_shadow_patterns_generation 
ON public.shadow_patterns(user_id, week_of, generation_method);

CREATE INDEX IF NOT EXISTS idx_strategic_moves_generation 
ON public.strategic_moves(user_id, week_of, generation_method);

-- 3. Create view for current week's intelligence status
CREATE OR REPLACE VIEW current_week_intelligence AS
SELECT 
  user_id,
  week_of,
  COUNT(DISTINCT CASE WHEN table_name = 'insights' THEN 1 END) as has_insights,
  COUNT(DISTINCT CASE WHEN table_name = 'predictions' THEN 1 END) as has_predictions,
  COUNT(DISTINCT CASE WHEN table_name = 'patterns' THEN 1 END) as has_patterns,
  COUNT(DISTINCT CASE WHEN table_name = 'strategies' THEN 1 END) as has_strategies,
  MAX(created_at) as last_generated_at
FROM (
  SELECT user_id, week_of, created_at, 'insights' as table_name FROM health_insights
  UNION ALL
  SELECT user_id, week_of, created_at, 'predictions' as table_name FROM health_predictions
  UNION ALL
  SELECT user_id, week_of, created_at, 'patterns' as table_name FROM shadow_patterns
  UNION ALL
  SELECT user_id, week_of, created_at, 'strategies' as table_name FROM strategic_moves
) combined
WHERE week_of = date_trunc('week', CURRENT_DATE)::DATE
GROUP BY user_id, week_of;

-- 4. Add last_generated columns for caching logic
ALTER TABLE public.health_insights 
ADD COLUMN IF NOT EXISTS last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

ALTER TABLE public.health_predictions 
ADD COLUMN IF NOT EXISTS last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

ALTER TABLE public.shadow_patterns 
ADD COLUMN IF NOT EXISTS last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

ALTER TABLE public.strategic_moves 
ADD COLUMN IF NOT EXISTS last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 5. Create function to check if regeneration is needed
CREATE OR REPLACE FUNCTION should_regenerate_component(
  p_user_id UUID,
  p_component_type TEXT,
  p_force_refresh BOOLEAN DEFAULT FALSE
)
RETURNS BOOLEAN AS $$
DECLARE
  v_last_generated TIMESTAMP WITH TIME ZONE;
  v_week_start DATE;
BEGIN
  -- If force refresh, always regenerate
  IF p_force_refresh THEN
    RETURN TRUE;
  END IF;
  
  v_week_start := date_trunc('week', CURRENT_DATE)::DATE;
  
  -- Check when component was last generated
  CASE p_component_type
    WHEN 'insights' THEN
      SELECT MAX(created_at) INTO v_last_generated
      FROM health_insights
      WHERE user_id = p_user_id AND week_of = v_week_start;
    WHEN 'predictions' THEN
      SELECT MAX(created_at) INTO v_last_generated
      FROM health_predictions
      WHERE user_id = p_user_id AND week_of = v_week_start;
    WHEN 'patterns' THEN
      SELECT MAX(created_at) INTO v_last_generated
      FROM shadow_patterns
      WHERE user_id = p_user_id AND week_of = v_week_start;
    WHEN 'strategies' THEN
      SELECT MAX(created_at) INTO v_last_generated
      FROM strategic_moves
      WHERE user_id = p_user_id AND week_of = v_week_start;
  END CASE;
  
  -- If never generated, return true
  IF v_last_generated IS NULL THEN
    RETURN TRUE;
  END IF;
  
  -- If generated more than 24 hours ago, allow regeneration
  IF v_last_generated < NOW() - INTERVAL '24 hours' THEN
    RETURN TRUE;
  END IF;
  
  RETURN FALSE;
END;
$$ LANGUAGE plpgsql;

-- 6. Create summary function for health intelligence
CREATE OR REPLACE FUNCTION get_health_intelligence_summary(p_user_id UUID)
RETURNS TABLE (
  insights_count INTEGER,
  predictions_count INTEGER,
  patterns_count INTEGER,
  strategies_count INTEGER,
  pending_strategies INTEGER,
  completed_strategies INTEGER,
  last_refresh TIMESTAMP WITH TIME ZONE,
  week_of DATE
) AS $$
DECLARE
  v_week_start DATE;
BEGIN
  v_week_start := date_trunc('week', CURRENT_DATE)::DATE;
  
  RETURN QUERY
  SELECT 
    (SELECT COUNT(*) FROM health_insights WHERE user_id = p_user_id AND week_of = v_week_start)::INTEGER,
    (SELECT COUNT(*) FROM health_predictions WHERE user_id = p_user_id AND week_of = v_week_start)::INTEGER,
    (SELECT COUNT(*) FROM shadow_patterns WHERE user_id = p_user_id AND week_of = v_week_start)::INTEGER,
    (SELECT COUNT(*) FROM strategic_moves WHERE user_id = p_user_id AND week_of = v_week_start)::INTEGER,
    (SELECT COUNT(*) FROM strategic_moves WHERE user_id = p_user_id AND week_of = v_week_start AND completion_status = 'pending')::INTEGER,
    (SELECT COUNT(*) FROM strategic_moves WHERE user_id = p_user_id AND week_of = v_week_start AND completion_status = 'completed')::INTEGER,
    GREATEST(
      (SELECT MAX(created_at) FROM health_insights WHERE user_id = p_user_id AND week_of = v_week_start),
      (SELECT MAX(created_at) FROM health_predictions WHERE user_id = p_user_id AND week_of = v_week_start),
      (SELECT MAX(created_at) FROM shadow_patterns WHERE user_id = p_user_id AND week_of = v_week_start),
      (SELECT MAX(created_at) FROM strategic_moves WHERE user_id = p_user_id AND week_of = v_week_start)
    ),
    v_week_start;
END;
$$ LANGUAGE plpgsql;

-- 7. Grant permissions
GRANT EXECUTE ON FUNCTION should_regenerate_component TO authenticated;
GRANT EXECUTE ON FUNCTION get_health_intelligence_summary TO authenticated;
GRANT SELECT ON current_week_intelligence TO authenticated;
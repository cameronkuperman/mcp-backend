-- Migration: Add Tier-Based Model Selection System
-- Description: Adds support for subscription tiers and model usage tracking
-- Date: 2025-01-13

-- 1. Add tier constraint to subscriptions table
-- This ensures only valid tier values are allowed
ALTER TABLE public.subscriptions 
ADD CONSTRAINT valid_tier CHECK (tier IN ('free', 'basic', 'pro', 'pro_plus', 'max'));

-- 2. Create model usage tracking table (optional but recommended)
-- Tracks which models are used, helping with cost analysis and performance monitoring
CREATE TABLE IF NOT EXISTS public.model_usage (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id text NOT NULL,
    model_used text NOT NULL,
    endpoint text NOT NULL,
    tokens_prompt integer,
    tokens_completion integer,
    tokens_reasoning integer,  -- Track reasoning tokens separately for DeepSeek R1 and o1 models
    reasoning_mode boolean DEFAULT false,
    tier_at_time text,
    success boolean DEFAULT true,
    error_message text,
    response_time_ms integer,
    created_at timestamptz DEFAULT now()
);

-- Create indexes for efficient querying
CREATE INDEX idx_model_usage_user ON public.model_usage(user_id);
CREATE INDEX idx_model_usage_created ON public.model_usage(created_at);
CREATE INDEX idx_model_usage_model ON public.model_usage(model_used);
CREATE INDEX idx_model_usage_endpoint ON public.model_usage(endpoint);

-- 3. Create tier configuration table (optional - for future flexibility)
-- Allows changing tier features without code deployment
CREATE TABLE IF NOT EXISTS public.tier_config (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    tier_name text UNIQUE NOT NULL,
    tier_level integer NOT NULL,  -- 0=free, 1=basic, 2=pro, 3=pro_plus, 4=max
    model_group text NOT NULL CHECK (model_group IN ('free', 'premium')),
    max_tokens_per_request integer DEFAULT 2000,
    rate_limit_per_hour integer DEFAULT 10,
    features jsonb DEFAULT '{}',  -- Store feature flags as JSON
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Insert default tier configurations
INSERT INTO public.tier_config (tier_name, tier_level, model_group, max_tokens_per_request, rate_limit_per_hour, features) 
VALUES 
    ('free', 0, 'free', 2000, 10, 
     '{"ultra_think": false, "reports": "basic", "chat_reasoning": true, "deep_dive": true}'),
    ('basic', 1, 'premium', 4000, 50, 
     '{"ultra_think": false, "reports": "standard", "chat_reasoning": true, "deep_dive": true}'),
    ('pro', 2, 'premium', 8000, 200, 
     '{"ultra_think": true, "reports": "advanced", "chat_reasoning": true, "deep_dive": true, "claude_chat": true}'),
    ('pro_plus', 3, 'premium', 16000, 1000, 
     '{"ultra_think": true, "reports": "all", "chat_reasoning": true, "deep_dive": true, "claude_chat": true}'),
    ('max', 4, 'premium', 32000, -1, 
     '{"ultra_think": true, "reports": "all", "chat_reasoning": true, "deep_dive": true, "claude_chat": true, "experimental": true}')
ON CONFLICT (tier_name) DO NOTHING;

-- 4. Add function to get user's current tier
-- This function can be called from the backend or used in RLS policies
CREATE OR REPLACE FUNCTION get_user_tier(p_user_id uuid)
RETURNS text AS $$
DECLARE
    v_tier text;
BEGIN
    SELECT tier INTO v_tier
    FROM public.subscriptions
    WHERE user_id = p_user_id 
        AND status = 'active'
        AND (current_period_end IS NULL OR current_period_end > NOW())
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN COALESCE(v_tier, 'free');
END;
$$ LANGUAGE plpgsql;

-- 5. Add function to log model usage
CREATE OR REPLACE FUNCTION log_model_usage(
    p_user_id text,
    p_model text,
    p_endpoint text,
    p_tokens_prompt integer DEFAULT NULL,
    p_tokens_completion integer DEFAULT NULL,
    p_tokens_reasoning integer DEFAULT NULL,
    p_reasoning_mode boolean DEFAULT false,
    p_success boolean DEFAULT true,
    p_error_message text DEFAULT NULL,
    p_response_time_ms integer DEFAULT NULL
)
RETURNS uuid AS $$
DECLARE
    v_tier text;
    v_id uuid;
BEGIN
    -- Get user's current tier
    v_tier := get_user_tier(p_user_id::uuid);
    
    -- Insert usage record
    INSERT INTO public.model_usage (
        user_id, model_used, endpoint, 
        tokens_prompt, tokens_completion, tokens_reasoning,
        reasoning_mode, tier_at_time, success, 
        error_message, response_time_ms
    ) VALUES (
        p_user_id, p_model, p_endpoint,
        p_tokens_prompt, p_tokens_completion, p_tokens_reasoning,
        p_reasoning_mode, v_tier, p_success,
        p_error_message, p_response_time_ms
    ) RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Create view for model usage analytics
CREATE OR REPLACE VIEW model_usage_analytics AS
SELECT 
    DATE_TRUNC('day', created_at) as usage_date,
    tier_at_time,
    endpoint,
    model_used,
    COUNT(*) as request_count,
    SUM(COALESCE(tokens_prompt, 0) + COALESCE(tokens_completion, 0) + COALESCE(tokens_reasoning, 0)) as total_tokens,
    SUM(tokens_reasoning) as reasoning_tokens,
    AVG(response_time_ms) as avg_response_time,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failure_count
FROM public.model_usage
GROUP BY DATE_TRUNC('day', created_at), tier_at_time, endpoint, model_used;

-- 7. Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON public.tier_config TO authenticated;
GRANT SELECT, INSERT ON public.model_usage TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_tier TO authenticated;
GRANT EXECUTE ON FUNCTION log_model_usage TO authenticated;
GRANT SELECT ON model_usage_analytics TO authenticated;

-- Add comment for documentation
COMMENT ON TABLE public.model_usage IS 'Tracks model usage per user for analytics and cost tracking';
COMMENT ON TABLE public.tier_config IS 'Configuration for subscription tiers and their features';
COMMENT ON FUNCTION get_user_tier IS 'Returns the current subscription tier for a user';
COMMENT ON FUNCTION log_model_usage IS 'Logs model usage for analytics and monitoring';
COMMENT ON VIEW model_usage_analytics IS 'Aggregated view of model usage for analytics dashboards';
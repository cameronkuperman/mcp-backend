-- Health Intelligence System Database Migration
-- Run this migration to create all necessary tables for the health intelligence features

-- 1. Health Insights Table
-- Stores AI-generated insights for each health story
CREATE TABLE IF NOT EXISTS public.health_insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    story_id UUID NOT NULL,
    insight_type VARCHAR(20) CHECK (insight_type IN ('positive', 'warning', 'neutral')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    confidence INTEGER CHECK (confidence >= 0 AND confidence <= 100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    week_of DATE NOT NULL, -- Monday of the week this was generated for
    metadata JSONB DEFAULT '{}' -- Additional data like related symptoms, body parts, etc
);

-- Indexes for performance
CREATE INDEX idx_health_insights_user_week ON public.health_insights(user_id, week_of);
CREATE INDEX idx_health_insights_story ON public.health_insights(story_id);
CREATE INDEX idx_health_insights_type ON public.health_insights(insight_type);

-- Enable RLS
ALTER TABLE public.health_insights ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own insights" 
    ON public.health_insights FOR SELECT 
    USING (auth.uid() = user_id);

-- 2. Health Predictions Table
-- Stores AI-generated predictions about potential health events
CREATE TABLE IF NOT EXISTS public.health_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    story_id UUID NOT NULL,
    event_description TEXT NOT NULL,
    probability INTEGER CHECK (probability >= 0 AND probability <= 100),
    timeframe TEXT NOT NULL, -- e.g., "This week", "Next few days", "Coming weekend"
    preventable BOOLEAN DEFAULT false,
    reasoning TEXT, -- AI's explanation for the prediction
    suggested_actions JSONB DEFAULT '[]', -- Array of preventive actions
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    week_of DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'occurred', 'prevented', 'expired'))
);

-- Indexes
CREATE INDEX idx_health_predictions_user_week ON public.health_predictions(user_id, week_of);
CREATE INDEX idx_health_predictions_probability ON public.health_predictions(probability DESC);
CREATE INDEX idx_health_predictions_status ON public.health_predictions(status);

-- Enable RLS
ALTER TABLE public.health_predictions ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own predictions" 
    ON public.health_predictions FOR SELECT 
    USING (auth.uid() = user_id);

-- 3. Shadow Patterns Table
-- Stores patterns that are missing from recent health stories
CREATE TABLE IF NOT EXISTS public.shadow_patterns (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    pattern_name TEXT NOT NULL,
    pattern_category VARCHAR(50), -- e.g., 'exercise', 'sleep', 'medication', 'symptom'
    last_seen_description TEXT NOT NULL,
    significance VARCHAR(10) CHECK (significance IN ('high', 'medium', 'low')),
    last_mentioned_date DATE,
    days_missing INTEGER DEFAULT 0, -- How many days since last mention
    historical_frequency JSONB DEFAULT '{}', -- Track how often this appeared historically
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    week_of DATE NOT NULL
);

-- Indexes
CREATE INDEX idx_shadow_patterns_user_week ON public.shadow_patterns(user_id, week_of);
CREATE INDEX idx_shadow_patterns_significance ON public.shadow_patterns(significance);
CREATE INDEX idx_shadow_patterns_category ON public.shadow_patterns(pattern_category);

-- Enable RLS
ALTER TABLE public.shadow_patterns ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own patterns" 
    ON public.shadow_patterns FOR SELECT 
    USING (auth.uid() = user_id);

-- 4. Strategic Moves Table
-- Stores personalized health strategies and recommendations
CREATE TABLE IF NOT EXISTS public.strategic_moves (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    strategy TEXT NOT NULL,
    strategy_type VARCHAR(20) CHECK (strategy_type IN ('discovery', 'pattern', 'prevention', 'optimization')),
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10), -- 1-10 scale
    rationale TEXT, -- Why this strategy is recommended
    expected_outcome TEXT, -- What user can expect if they follow this
    completion_status VARCHAR(20) DEFAULT 'pending' CHECK (completion_status IN ('pending', 'in_progress', 'completed', 'skipped')),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    week_of DATE NOT NULL
);

-- Indexes
CREATE INDEX idx_strategic_moves_user_week ON public.strategic_moves(user_id, week_of);
CREATE INDEX idx_strategic_moves_priority ON public.strategic_moves(priority DESC);
CREATE INDEX idx_strategic_moves_status ON public.strategic_moves(completion_status);

-- Enable RLS
ALTER TABLE public.strategic_moves ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own strategies" 
    ON public.strategic_moves FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own strategies" 
    ON public.strategic_moves FOR UPDATE 
    USING (auth.uid() = user_id);

-- 5. Export History Table
-- Tracks PDF exports and doctor shares
CREATE TABLE IF NOT EXISTS public.export_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    export_type VARCHAR(20) CHECK (export_type IN ('pdf', 'doctor_share', 'csv', 'full_report')),
    story_ids UUID[], -- array of story IDs included
    share_token TEXT UNIQUE, -- Unique token for share links
    share_link TEXT, -- Full URL for doctor shares
    expires_at TIMESTAMP WITH TIME ZONE, -- For time-limited shares
    recipient_email TEXT, -- If shared with specific doctor
    recipient_name TEXT, -- Doctor's name if provided
    access_count INTEGER DEFAULT 0, -- Track how many times accessed
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    file_url TEXT, -- S3/Storage URL for PDFs
    file_size_bytes INTEGER,
    metadata JSONB DEFAULT '{}', -- Additional export settings/options
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Indexes
CREATE INDEX idx_export_history_user ON public.export_history(user_id);
CREATE INDEX idx_export_history_share_token ON public.export_history(share_token);
CREATE INDEX idx_export_history_type ON public.export_history(export_type);
CREATE INDEX idx_export_history_expires ON public.export_history(expires_at);

-- Enable RLS
ALTER TABLE public.export_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own exports" 
    ON public.export_history FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Public can view shared exports" 
    ON public.export_history FOR SELECT 
    USING (
        share_token IS NOT NULL 
        AND export_type = 'doctor_share'
        AND (expires_at IS NULL OR expires_at > NOW())
    );

CREATE POLICY "Users can create exports" 
    ON public.export_history FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

-- 6. Analysis Generation Log Table (for tracking and debugging)
CREATE TABLE IF NOT EXISTS public.analysis_generation_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    generation_type VARCHAR(30) CHECK (generation_type IN ('weekly_auto', 'manual_refresh', 'initial', 'retry')),
    status VARCHAR(20) CHECK (status IN ('started', 'completed', 'failed', 'partial')),
    error_message TEXT,
    insights_count INTEGER DEFAULT 0,
    predictions_count INTEGER DEFAULT 0,
    patterns_count INTEGER DEFAULT 0,
    strategies_count INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    model_used VARCHAR(50), -- Track which AI model was used
    week_of DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes
CREATE INDEX idx_generation_log_user ON public.analysis_generation_log(user_id);
CREATE INDEX idx_generation_log_status ON public.analysis_generation_log(status);
CREATE INDEX idx_generation_log_week ON public.analysis_generation_log(week_of);

-- Enable RLS
ALTER TABLE public.analysis_generation_log ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own logs" 
    ON public.analysis_generation_log FOR SELECT 
    USING (auth.uid() = user_id);

-- 7. User Refresh Limits Table (track API usage)
CREATE TABLE IF NOT EXISTS public.user_refresh_limits (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    week_of DATE NOT NULL,
    refresh_count INTEGER DEFAULT 0,
    last_refresh_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    UNIQUE(user_id, week_of)
);

-- Index
CREATE INDEX idx_refresh_limits_user_week ON public.user_refresh_limits(user_id, week_of);

-- Enable RLS
ALTER TABLE public.user_refresh_limits ENABLE ROW LEVEL SECURITY;

-- RLS Policy
CREATE POLICY "Users can view their own limits" 
    ON public.user_refresh_limits FOR SELECT 
    USING (auth.uid() = user_id);

-- Create helper functions
CREATE OR REPLACE FUNCTION get_current_week_monday()
RETURNS DATE AS $$
BEGIN
    RETURN date_trunc('week', CURRENT_DATE)::DATE;
END;
$$ LANGUAGE plpgsql;

-- Function to increment access count for shared exports
CREATE OR REPLACE FUNCTION increment_share_access(p_share_token TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE public.export_history
    SET 
        access_count = access_count + 1,
        last_accessed_at = NOW()
    WHERE 
        share_token = p_share_token
        AND (expires_at IS NULL OR expires_at > NOW());
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions (adjust based on your Supabase setup)
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
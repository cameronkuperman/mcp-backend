-- Migration: Create health_scores table for AI-driven health scoring
-- Purpose: Store cached health scores and personalized daily actions
-- Date: 2025-01-31

-- Create health_scores table
CREATE TABLE IF NOT EXISTS public.health_scores (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id text NOT NULL,
    score integer NOT NULL CHECK (score >= 0 AND score <= 100),
    reasoning text,
    actions jsonb NOT NULL DEFAULT '[]'::jsonb,
    week_of timestamp with time zone NOT NULL DEFAULT date_trunc('week', CURRENT_TIMESTAMP),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    expires_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_health_scores_user_id ON public.health_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_health_scores_created_at ON public.health_scores(created_at);
CREATE INDEX IF NOT EXISTS idx_health_scores_expires_at ON public.health_scores(expires_at);
CREATE INDEX IF NOT EXISTS idx_health_scores_week_of ON public.health_scores(week_of);

-- Add composite index for user lookups by date
CREATE INDEX IF NOT EXISTS idx_health_scores_user_date ON public.health_scores(user_id, created_at DESC);

-- Enable RLS
ALTER TABLE public.health_scores ENABLE ROW LEVEL SECURITY;

-- Create policies for authenticated users
CREATE POLICY "Users can view their own health scores" ON public.health_scores
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage all health scores" ON public.health_scores
    FOR ALL USING (auth.role() = 'service_role');

-- Add comment
COMMENT ON TABLE public.health_scores IS 'Stores AI-generated health scores with personalized daily actions';
COMMENT ON COLUMN public.health_scores.score IS 'Health score from 0-100, starting base 80';
COMMENT ON COLUMN public.health_scores.actions IS 'Array of 3 daily actions with icon and text';
COMMENT ON COLUMN public.health_scores.reasoning IS 'AI explanation for the score';
COMMENT ON COLUMN public.health_scores.week_of IS 'Monday of the week this score belongs to';

-- Create function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_health_scores_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at
CREATE TRIGGER update_health_scores_updated_at
    BEFORE UPDATE ON public.health_scores
    FOR EACH ROW
    EXECUTE FUNCTION update_health_scores_updated_at();

-- Grant permissions
GRANT SELECT ON public.health_scores TO authenticated;
GRANT ALL ON public.health_scores TO service_role;
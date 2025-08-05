-- Create report_analyses table if it doesn't exist
CREATE TABLE IF NOT EXISTS report_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    purpose TEXT,
    recommended_type TEXT,
    confidence FLOAT,
    report_config JSONB,
    quick_scan_ids TEXT[],
    deep_dive_ids TEXT[],
    general_assessment_ids TEXT[],
    general_deep_dive_ids TEXT[],
    flash_assessment_ids TEXT[],
    photo_session_ids TEXT[]  -- Add this if missing
);

-- Add index for user lookup
CREATE INDEX IF NOT EXISTS idx_report_analyses_user_id ON report_analyses(user_id);

-- Add index for created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_report_analyses_created_at ON report_analyses(created_at);

-- Add RLS policies
ALTER TABLE report_analyses ENABLE ROW LEVEL SECURITY;

-- Users can only see their own analyses
CREATE POLICY "Users can view own report analyses" ON report_analyses
    FOR SELECT USING (auth.uid()::text = user_id);

-- Users can create their own analyses
CREATE POLICY "Users can create own report analyses" ON report_analyses
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Service role bypass
CREATE POLICY "Service role has full access" ON report_analyses
    FOR ALL USING (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON report_analyses TO authenticated;
GRANT ALL ON report_analyses TO service_role;

-- Add comment
COMMENT ON TABLE report_analyses IS 'Stores report analysis requests and configurations with selected data IDs';
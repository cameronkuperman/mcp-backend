-- Medical Reports Tables Migration
-- Run this in Supabase SQL editor

-- Create report_analyses table
CREATE TABLE IF NOT EXISTS report_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,  -- Nullable for anonymous
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Context
    purpose TEXT,
    symptom_focus TEXT,
    time_range JSONB,
    
    -- Results
    recommended_type TEXT NOT NULL,
    confidence DECIMAL(3,2),
    report_config JSONB NOT NULL,
    
    -- Tracking
    data_sources JSONB
);

-- Create medical_reports table
CREATE TABLE IF NOT EXISTS medical_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,  -- Nullable for anonymous
    analysis_id UUID REFERENCES report_analyses(id),
    report_type TEXT NOT NULL CHECK (report_type IN (
        'comprehensive', 'urgent_triage', 'photo_progression', 
        'symptom_timeline', 'specialist_focused', 'annual_summary'
    )),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Report content
    report_data JSONB NOT NULL,
    executive_summary TEXT NOT NULL,  -- Always have 1-page summary
    
    -- Metadata
    confidence_score INTEGER,
    model_used TEXT,
    data_sources JSONB,
    time_range JSONB,
    
    -- Access tracking
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_analyses_user ON report_analyses(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_user_type ON medical_reports(user_id, report_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_analysis ON medical_reports(analysis_id);
CREATE INDEX IF NOT EXISTS idx_reports_created ON medical_reports(created_at DESC);

-- Add RLS policies
ALTER TABLE report_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_reports ENABLE ROW LEVEL SECURITY;

-- Policies for report_analyses
CREATE POLICY "Users can read own analyses" ON report_analyses
    FOR SELECT
    USING (user_id = auth.uid()::text OR user_id IS NULL);

CREATE POLICY "Users can insert own analyses" ON report_analyses
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

-- Policies for medical_reports
CREATE POLICY "Users can read own reports" ON medical_reports
    FOR SELECT
    USING (user_id = auth.uid()::text OR user_id IS NULL);

CREATE POLICY "Users can insert own reports" ON medical_reports
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

CREATE POLICY "Users can update own report access" ON medical_reports
    FOR UPDATE
    USING (user_id = auth.uid()::text OR user_id IS NULL)
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

-- Grant permissions
GRANT ALL ON report_analyses TO authenticated;
GRANT ALL ON report_analyses TO anon;  -- For anonymous reports
GRANT ALL ON report_analyses TO service_role;

GRANT ALL ON medical_reports TO authenticated;
GRANT ALL ON medical_reports TO anon;  -- For anonymous reports
GRANT ALL ON medical_reports TO service_role;

-- Add comments
COMMENT ON TABLE report_analyses IS 'Stores report type analysis results';
COMMENT ON TABLE medical_reports IS 'Stores generated medical reports';
COMMENT ON COLUMN medical_reports.executive_summary IS 'Always contains 1-page summary for all report types';
COMMENT ON COLUMN medical_reports.report_data IS 'Full report content in structured JSON format';

-- Function to update access tracking
CREATE OR REPLACE FUNCTION update_report_access()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if it's been more than 1 minute since last access
    IF NEW.last_accessed IS NULL OR 
       NEW.last_accessed < NOW() - INTERVAL '1 minute' THEN
        NEW.last_accessed = NOW();
        NEW.access_count = COALESCE(OLD.access_count, 0) + 1;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for access tracking (optional)
CREATE TRIGGER report_access_tracker
    BEFORE UPDATE ON medical_reports
    FOR EACH ROW
    WHEN (pg_trigger_depth() = 0)
    EXECUTE FUNCTION update_report_access();

-- Add missing columns to symptom_tracking if needed
-- This links symptom entries to their originating sessions
ALTER TABLE symptom_tracking 
ADD COLUMN IF NOT EXISTS quick_scan_id UUID REFERENCES quick_scans(id),
ADD COLUMN IF NOT EXISTS deep_dive_id UUID REFERENCES deep_dive_sessions(id);

-- Create index for faster symptom lookups
CREATE INDEX IF NOT EXISTS idx_symptom_scan ON symptom_tracking(quick_scan_id);
CREATE INDEX IF NOT EXISTS idx_symptom_dive ON symptom_tracking(deep_dive_id);
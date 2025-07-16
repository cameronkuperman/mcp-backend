-- Medical Reports Database Tables Migration
-- Run this in your Supabase SQL editor

-- Table for storing report analysis results (Step 1 of 2-stage process)
CREATE TABLE IF NOT EXISTS report_analyses (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    purpose TEXT,
    symptom_focus TEXT,
    time_range JSONB,
    recommended_type TEXT,
    confidence DECIMAL,
    report_config JSONB,
    data_sources JSONB
);

-- Table for storing generated medical reports (Step 2 of 2-stage process)
CREATE TABLE IF NOT EXISTS medical_reports (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    analysis_id TEXT REFERENCES report_analyses(id),
    report_type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    report_data JSONB NOT NULL,
    executive_summary TEXT,
    confidence_score INTEGER,
    model_used TEXT,
    data_sources JSONB,
    time_range JSONB,
    specialty TEXT, -- For specialist reports
    year INTEGER    -- For annual reports
);

-- Add columns if they don't exist (for existing tables)
ALTER TABLE medical_reports ADD COLUMN IF NOT EXISTS specialty TEXT;
ALTER TABLE medical_reports ADD COLUMN IF NOT EXISTS year INTEGER;

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_report_analyses_user_id ON report_analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_report_analyses_created_at ON report_analyses(created_at);

CREATE INDEX IF NOT EXISTS idx_medical_reports_user_id ON medical_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_medical_reports_type ON medical_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_medical_reports_created_at ON medical_reports(created_at);
CREATE INDEX IF NOT EXISTS idx_medical_reports_analysis_id ON medical_reports(analysis_id);

-- Enable Row Level Security (RLS) if needed
ALTER TABLE report_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_reports ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (adjust based on your auth setup)
-- Allow users to see their own reports
CREATE POLICY "Users can view own report analyses" ON report_analyses
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can view own medical reports" ON medical_reports
    FOR SELECT USING (auth.uid()::text = user_id);

-- Allow authenticated users to create reports
CREATE POLICY "Authenticated users can create report analyses" ON report_analyses
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can create medical reports" ON medical_reports
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Grant necessary permissions
GRANT ALL ON report_analyses TO authenticated;
GRANT ALL ON medical_reports TO authenticated;
GRANT ALL ON report_analyses TO anon;
GRANT ALL ON medical_reports TO anon;

-- Note: Run the following additional migration files for complete setup:
-- 1. supabase_migrations/quick_scan_tables.sql
-- 2. supabase_migrations/deep_dive_sessions.sql
-- 3. supabase_migrations/long_term_tracking.sql
-- Create quick_scans table
CREATE TABLE IF NOT EXISTS quick_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,  -- Nullable for anonymous users
    body_part TEXT NOT NULL,
    form_data JSONB NOT NULL,
    analysis_result JSONB NOT NULL,
    confidence_score INTEGER CHECK (confidence_score BETWEEN 0 AND 100),
    urgency_level TEXT CHECK (urgency_level IN ('low', 'medium', 'high')),
    llm_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    escalated_to_oracle BOOLEAN DEFAULT FALSE,
    oracle_conversation_id UUID REFERENCES conversations(id),
    physician_report_generated BOOLEAN DEFAULT FALSE
);

-- Create indexes for quick_scans
CREATE INDEX idx_user_scans ON quick_scans (user_id, created_at DESC);
CREATE INDEX idx_body_part ON quick_scans (body_part, created_at DESC);

-- Create symptom_tracking table for line graphs
CREATE TABLE IF NOT EXISTS symptom_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    quick_scan_id UUID REFERENCES quick_scans(id),
    symptom_name TEXT NOT NULL,
    body_part TEXT NOT NULL,
    severity INTEGER CHECK (severity BETWEEN 1 AND 10),
    occurrence_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for symptom_tracking
CREATE INDEX idx_user_symptoms ON symptom_tracking (user_id, symptom_name, occurrence_date);
CREATE UNIQUE INDEX idx_unique_symptom_daily ON symptom_tracking (user_id, symptom_name, body_part, occurrence_date);

-- Add RLS (Row Level Security) policies for quick_scans
ALTER TABLE quick_scans ENABLE ROW LEVEL SECURITY;

-- Policy for users to read their own quick scans
CREATE POLICY "Users can read own quick scans" ON quick_scans
    FOR SELECT
    USING (user_id = auth.uid()::text OR user_id IS NULL);

-- Policy for users to insert their own quick scans
CREATE POLICY "Users can insert own quick scans" ON quick_scans
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

-- Policy for users to update their own quick scans
CREATE POLICY "Users can update own quick scans" ON quick_scans
    FOR UPDATE
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- Add RLS policies for symptom_tracking
ALTER TABLE symptom_tracking ENABLE ROW LEVEL SECURITY;

-- Policy for users to read their own symptom tracking
CREATE POLICY "Users can read own symptoms" ON symptom_tracking
    FOR SELECT
    USING (user_id = auth.uid()::text);

-- Policy for users to insert their own symptom tracking
CREATE POLICY "Users can insert own symptoms" ON symptom_tracking
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::text);

-- Policy for users to update their own symptom tracking
CREATE POLICY "Users can update own symptoms" ON symptom_tracking
    FOR UPDATE
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- Policy for users to delete their own symptom tracking
CREATE POLICY "Users can delete own symptoms" ON symptom_tracking
    FOR DELETE
    USING (user_id = auth.uid()::text);

-- Grant necessary permissions
GRANT ALL ON quick_scans TO authenticated;
GRANT ALL ON symptom_tracking TO authenticated;
GRANT ALL ON quick_scans TO anon;  -- For anonymous quick scans
GRANT SELECT ON symptom_tracking TO anon;

-- Add comment documentation
COMMENT ON TABLE quick_scans IS 'Stores quick scan health assessments with AI analysis';
COMMENT ON TABLE symptom_tracking IS 'Tracks symptoms over time for graphing and trend analysis';
COMMENT ON COLUMN quick_scans.escalated_to_oracle IS 'Indicates if user escalated to full Oracle consultation';
COMMENT ON COLUMN quick_scans.confidence_score IS 'AI confidence in the analysis (0-100)';
COMMENT ON COLUMN symptom_tracking.occurrence_date IS 'Date of symptom occurrence for daily tracking';
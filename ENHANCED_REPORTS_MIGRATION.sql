-- Enhanced Medical Reports Database Migration
-- Run this in Supabase SQL Editor AFTER the base migration

-- =====================================================
-- ENHANCED REPORT TABLES
-- =====================================================

-- Update medical_reports table with new fields
ALTER TABLE medical_reports 
ADD COLUMN IF NOT EXISTS doctor_reviewed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_modified TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS report_version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS is_draft BOOLEAN DEFAULT FALSE;

-- Doctor notes and collaboration
CREATE TABLE IF NOT EXISTS report_doctor_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id TEXT REFERENCES medical_reports(id) ON DELETE CASCADE,
    doctor_npi TEXT NOT NULL,
    specialty TEXT,
    notes TEXT NOT NULL,
    sections_reviewed TEXT[],
    diagnosis_added TEXT,
    plan_modifications JSONB,
    follow_up_instructions TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report sharing between doctors
CREATE TABLE IF NOT EXISTS report_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id TEXT REFERENCES medical_reports(id) ON DELETE CASCADE,
    shared_by_npi TEXT NOT NULL,
    shared_with_npi TEXT NOT NULL,
    access_level TEXT CHECK (access_level IN ('read_only', 'full_access')),
    share_notes TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    accessed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Report ratings from doctors
CREATE TABLE IF NOT EXISTS report_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id TEXT REFERENCES medical_reports(id) ON DELETE CASCADE,
    doctor_npi TEXT NOT NULL,
    usefulness_score INTEGER CHECK (usefulness_score BETWEEN 1 AND 5),
    accuracy_score INTEGER CHECK (accuracy_score BETWEEN 1 AND 5),
    time_saved_minutes INTEGER,
    would_recommend BOOLEAN,
    feedback_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(report_id, doctor_npi)
);

-- Pattern detection results cache
CREATE TABLE IF NOT EXISTS report_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN ('temporal', 'correlation', 'trigger', 'effectiveness')),
    pattern_data JSONB NOT NULL,
    confidence_score DECIMAL,
    date_range JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '30 days')
);

-- Outbreak tracking for population health
CREATE TABLE IF NOT EXISTS outbreak_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_cluster TEXT NOT NULL,
    geographic_area TEXT,
    case_count INTEGER DEFAULT 1,
    trend TEXT CHECK (trend IN ('increasing', 'stable', 'decreasing')),
    first_detected TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cdc_alert_id TEXT,
    status TEXT DEFAULT 'active'
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- Doctor collaboration indexes
CREATE INDEX IF NOT EXISTS idx_doctor_notes_report ON report_doctor_notes(report_id);
CREATE INDEX IF NOT EXISTS idx_doctor_notes_npi ON report_doctor_notes(doctor_npi);

CREATE INDEX IF NOT EXISTS idx_report_shares_report ON report_shares(report_id);
CREATE INDEX IF NOT EXISTS idx_report_shares_recipient ON report_shares(shared_with_npi);
CREATE INDEX IF NOT EXISTS idx_report_shares_active ON report_shares(expires_at) WHERE expires_at > NOW();

CREATE INDEX IF NOT EXISTS idx_report_ratings_report ON report_ratings(report_id);
CREATE INDEX IF NOT EXISTS idx_report_ratings_scores ON report_ratings(usefulness_score, accuracy_score);

-- Pattern detection indexes
CREATE INDEX IF NOT EXISTS idx_patterns_user ON report_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON report_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_active ON report_patterns(expires_at) WHERE expires_at > NOW();

-- Outbreak tracking indexes
CREATE INDEX IF NOT EXISTS idx_outbreak_symptom ON outbreak_tracking(symptom_cluster);
CREATE INDEX IF NOT EXISTS idx_outbreak_area ON outbreak_tracking(geographic_area);
CREATE INDEX IF NOT EXISTS idx_outbreak_active ON outbreak_tracking(status) WHERE status = 'active';

-- =====================================================
-- ROW LEVEL SECURITY (RLS)
-- =====================================================

-- Enable RLS on new tables
ALTER TABLE report_doctor_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_ratings ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbreak_tracking ENABLE ROW LEVEL SECURITY;

-- RLS Policies for doctor notes
CREATE POLICY "Doctors can manage their own notes" ON report_doctor_notes
    FOR ALL
    USING (doctor_npi = current_setting('app.current_doctor_npi', true))
    WITH CHECK (doctor_npi = current_setting('app.current_doctor_npi', true));

CREATE POLICY "Report owners can view doctor notes" ON report_doctor_notes
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM medical_reports 
            WHERE medical_reports.id = report_doctor_notes.report_id 
            AND medical_reports.user_id = auth.uid()::text
        )
    );

-- RLS Policies for report shares
CREATE POLICY "Doctors can manage their shares" ON report_shares
    FOR ALL
    USING (
        shared_by_npi = current_setting('app.current_doctor_npi', true) OR
        shared_with_npi = current_setting('app.current_doctor_npi', true)
    );

-- RLS Policies for ratings
CREATE POLICY "Anyone can view aggregate ratings" ON report_ratings
    FOR SELECT
    USING (true);

CREATE POLICY "Doctors can manage their ratings" ON report_ratings
    FOR INSERT
    WITH CHECK (doctor_npi = current_setting('app.current_doctor_npi', true));

-- RLS Policies for patterns
CREATE POLICY "Users can view their own patterns" ON report_patterns
    FOR SELECT
    USING (user_id = auth.uid()::text);

-- RLS Policies for outbreak tracking (public health data)
CREATE POLICY "Public can view outbreak data" ON outbreak_tracking
    FOR SELECT
    USING (true);

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to detect patterns in symptom data
CREATE OR REPLACE FUNCTION detect_symptom_patterns(
    p_user_id TEXT,
    p_days INTEGER DEFAULT 30
) RETURNS TABLE (
    pattern_type TEXT,
    pattern_description TEXT,
    confidence DECIMAL,
    occurrences INTEGER
) AS $$
BEGIN
    -- This is a placeholder for pattern detection logic
    -- In production, this would analyze symptom_tracking data
    RETURN QUERY
    SELECT 
        'temporal'::TEXT as pattern_type,
        'Headaches occur more frequently on weekdays'::TEXT as pattern_description,
        0.87::DECIMAL as confidence,
        15::INTEGER as occurrences;
END;
$$ LANGUAGE plpgsql;

-- Function to get report effectiveness metrics
CREATE OR REPLACE FUNCTION get_report_metrics(
    p_report_type TEXT DEFAULT NULL
) RETURNS TABLE (
    report_type TEXT,
    avg_usefulness DECIMAL,
    avg_accuracy DECIMAL,
    avg_time_saved INTEGER,
    recommendation_rate DECIMAL,
    total_ratings INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mr.report_type,
        ROUND(AVG(rr.usefulness_score), 2) as avg_usefulness,
        ROUND(AVG(rr.accuracy_score), 2) as avg_accuracy,
        ROUND(AVG(rr.time_saved_minutes), 0)::INTEGER as avg_time_saved,
        ROUND(AVG(CASE WHEN rr.would_recommend THEN 1 ELSE 0 END) * 100, 1) as recommendation_rate,
        COUNT(*)::INTEGER as total_ratings
    FROM medical_reports mr
    JOIN report_ratings rr ON mr.id = rr.report_id
    WHERE (p_report_type IS NULL OR mr.report_type = p_report_type)
    GROUP BY mr.report_type;
END;
$$ LANGUAGE plpgsql;

-- Function to update outbreak tracking
CREATE OR REPLACE FUNCTION update_outbreak_tracking() RETURNS VOID AS $$
DECLARE
    v_symptom_record RECORD;
    v_threshold INTEGER := 5;
BEGIN
    -- Analyze recent symptoms for clusters
    FOR v_symptom_record IN 
        SELECT 
            lower(form_data->>'symptoms') as symptom,
            COUNT(*) as symptom_count
        FROM quick_scans
        WHERE created_at > NOW() - INTERVAL '14 days'
        AND form_data->>'symptoms' IS NOT NULL
        GROUP BY lower(form_data->>'symptoms')
        HAVING COUNT(*) >= v_threshold
    LOOP
        INSERT INTO outbreak_tracking (symptom_cluster, case_count, trend)
        VALUES (v_symptom_record.symptom, v_symptom_record.symptom_count, 'increasing')
        ON CONFLICT (symptom_cluster) 
        DO UPDATE SET 
            case_count = v_symptom_record.symptom_count,
            last_updated = NOW(),
            trend = CASE 
                WHEN outbreak_tracking.case_count < v_symptom_record.symptom_count THEN 'increasing'
                WHEN outbreak_tracking.case_count > v_symptom_record.symptom_count THEN 'decreasing'
                ELSE 'stable'
            END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- PERMISSIONS
-- =====================================================

GRANT ALL ON report_doctor_notes TO authenticated;
GRANT ALL ON report_shares TO authenticated;
GRANT ALL ON report_ratings TO authenticated;
GRANT ALL ON report_patterns TO authenticated;
GRANT SELECT ON outbreak_tracking TO authenticated;
GRANT SELECT ON outbreak_tracking TO anon;

-- =====================================================
-- SCHEDULED JOBS (Optional - requires pg_cron)
-- =====================================================

-- If you have pg_cron enabled, uncomment these:
-- SELECT cron.schedule('update-outbreak-tracking', '0 * * * *', 'SELECT update_outbreak_tracking();');
-- SELECT cron.schedule('cleanup-expired-patterns', '0 2 * * *', 'DELETE FROM report_patterns WHERE expires_at < NOW();');
-- SELECT cron.schedule('cleanup-expired-shares', '0 2 * * *', 'DELETE FROM report_shares WHERE expires_at < NOW();');

-- =====================================================
-- SAMPLE DATA FOR TESTING (Optional)
-- =====================================================

-- Insert sample outbreak data
INSERT INTO outbreak_tracking (symptom_cluster, case_count, trend, geographic_area)
VALUES 
    ('fever and cough', 12, 'increasing', 'Downtown'),
    ('gastrointestinal symptoms', 8, 'stable', 'Suburbs'),
    ('rash', 5, 'decreasing', 'North District')
ON CONFLICT DO NOTHING;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check all new tables exist
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN (
    'report_doctor_notes', 
    'report_shares', 
    'report_ratings', 
    'report_patterns',
    'outbreak_tracking'
);

-- Verify medical_reports has new columns
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'medical_reports' 
AND column_name IN ('doctor_reviewed', 'last_modified', 'report_version', 'is_draft');

-- Check indexes
SELECT indexname 
FROM pg_indexes 
WHERE tablename IN (
    'report_doctor_notes', 
    'report_shares', 
    'report_ratings', 
    'report_patterns',
    'outbreak_tracking'
);

-- =====================================================
-- SUCCESS!
-- =====================================================
-- Your enhanced medical reports system is ready!
-- 
-- Features added:
-- ✅ Doctor collaboration (notes, sharing, ratings)
-- ✅ Pattern detection caching
-- ✅ Outbreak tracking
-- ✅ Report versioning
-- ✅ Performance indexes
-- ✅ Security policies
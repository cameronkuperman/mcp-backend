-- Enhanced Specialist Reports Migration
-- Adds fields required for AI-driven clinical scales and enhanced reporting

-- Add confidence_score to reports table if not exists
ALTER TABLE medical_reports 
ADD COLUMN IF NOT EXISTS confidence_score DECIMAL(3,2);

-- Add metadata for storing clinical scale calculations and other data
ALTER TABLE medical_reports 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

-- Add analysis_id for tracking report generation (already exists from foreign key)
-- Just ensure the index exists
CREATE INDEX IF NOT EXISTS idx_reports_analysis_id ON medical_reports(analysis_id);

-- Add composite index for faster user + report type queries
CREATE INDEX IF NOT EXISTS idx_reports_user_id_type ON medical_reports(user_id, report_type);

-- Add index for confidence score queries (e.g., finding high-confidence reports)
CREATE INDEX IF NOT EXISTS idx_reports_confidence ON medical_reports(confidence_score) 
WHERE confidence_score IS NOT NULL;

-- Add index on metadata for specific clinical scale queries
CREATE INDEX IF NOT EXISTS idx_reports_metadata_scales ON medical_reports 
USING GIN ((metadata -> 'clinical_scales'));

-- Update report_analyses table to support enhanced triage data
ALTER TABLE report_analyses 
ADD COLUMN IF NOT EXISTS triage_result JSONB,
ADD COLUMN IF NOT EXISTS quick_scan_ids TEXT[],
ADD COLUMN IF NOT EXISTS deep_dive_ids TEXT[];

-- Add function to calculate report confidence based on data completeness
CREATE OR REPLACE FUNCTION calculate_report_confidence(
    p_report_data JSONB
) RETURNS DECIMAL AS $$
DECLARE
    v_confidence DECIMAL := 0.5; -- Base confidence
    v_data_points INTEGER := 0;
    v_scale_confidence DECIMAL;
BEGIN
    -- Check for clinical scales presence and average their confidence
    IF p_report_data -> 'clinical_scales' IS NOT NULL THEN
        SELECT AVG((value -> 'confidence')::DECIMAL)
        INTO v_scale_confidence
        FROM jsonb_each(p_report_data -> 'clinical_scales');
        
        IF v_scale_confidence IS NOT NULL THEN
            v_confidence := v_scale_confidence;
        END IF;
    END IF;
    
    -- Adjust based on data quality notes
    IF p_report_data -> 'data_quality_notes' -> 'completeness' ? 'high' THEN
        v_confidence := LEAST(v_confidence + 0.1, 1.0);
    ELSIF p_report_data -> 'data_quality_notes' -> 'completeness' ? 'low' THEN
        v_confidence := GREATEST(v_confidence - 0.1, 0.0);
    END IF;
    
    RETURN ROUND(v_confidence, 2);
END;
$$ LANGUAGE plpgsql;

-- Add trigger to auto-calculate confidence score on insert/update
CREATE OR REPLACE FUNCTION update_report_confidence()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.report_data IS NOT NULL AND NEW.confidence_score IS NULL THEN
        NEW.confidence_score := calculate_report_confidence(NEW.report_data);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_confidence_trigger
BEFORE INSERT OR UPDATE ON medical_reports
FOR EACH ROW
EXECUTE FUNCTION update_report_confidence();

-- Create view for high-confidence specialist reports
CREATE OR REPLACE VIEW high_confidence_specialist_reports AS
SELECT 
    r.id,
    r.user_id,
    r.report_type,
    r.specialty,
    r.created_at,
    r.confidence_score,
    r.report_data -> 'executive_summary' -> 'one_page_summary' as summary,
    r.report_data -> 'clinical_scales' as clinical_scales
FROM medical_reports r
WHERE r.confidence_score >= 0.8
AND r.specialty IS NOT NULL
ORDER BY r.created_at DESC;

-- Grant permissions
GRANT SELECT ON high_confidence_specialist_reports TO authenticated;
GRANT SELECT ON high_confidence_specialist_reports TO anon;

-- Add comments for documentation
COMMENT ON COLUMN medical_reports.confidence_score IS 'AI confidence in report accuracy (0.0-1.0)';
COMMENT ON COLUMN medical_reports.metadata IS 'Additional report metadata including scale calculations';
COMMENT ON FUNCTION calculate_report_confidence IS 'Calculates report confidence based on clinical scale confidence and data quality';

-- Verification queries
SELECT 
    'Enhanced specialist reports migration completed successfully' as status,
    COUNT(*) as tables_checked
FROM information_schema.columns 
WHERE table_name = 'medical_reports' 
AND column_name IN ('confidence_score', 'metadata');
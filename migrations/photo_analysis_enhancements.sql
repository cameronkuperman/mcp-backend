-- Photo Analysis Enhancements Migration
-- Adds support for quantitative metrics, quality scores, and importance markers

-- Add quantitative metrics to photo_analyses table
ALTER TABLE photo_analyses
ADD COLUMN IF NOT EXISTS quantitative_metrics JSONB,
ADD COLUMN IF NOT EXISTS condition_specific_scores JSONB,
ADD COLUMN IF NOT EXISTS photo_quality_score FLOAT;

-- Add measurement deltas to photo_comparisons table
ALTER TABLE photo_comparisons
ADD COLUMN IF NOT EXISTS measurement_deltas JSONB,
ADD COLUMN IF NOT EXISTS clinical_significance TEXT,
ADD COLUMN IF NOT EXISTS visual_annotations JSONB,
ADD COLUMN IF NOT EXISTS primary_change TEXT,
ADD COLUMN IF NOT EXISTS change_significance VARCHAR(20) CHECK (change_significance IN ('minor', 'moderate', 'significant', 'critical'));

-- Add quality score to photo_uploads
ALTER TABLE photo_uploads
ADD COLUMN IF NOT EXISTS quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100);

-- Create photo importance markers table
CREATE TABLE IF NOT EXISTS photo_importance_markers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  photo_id UUID REFERENCES photo_uploads(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id),
  importance_score INTEGER DEFAULT 5 CHECK (importance_score >= 1 AND importance_score <= 10),
  reason TEXT,
  marked_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_photo_importance_photo_id ON photo_importance_markers(photo_id);
CREATE INDEX IF NOT EXISTS idx_photo_importance_user_id ON photo_importance_markers(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_uploads_quality_score ON photo_uploads(quality_score) WHERE quality_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_photo_comparisons_significance ON photo_comparisons(change_significance);

-- Add progression tracking fields to photo_sessions
ALTER TABLE photo_sessions
ADD COLUMN IF NOT EXISTS monitoring_phase VARCHAR(50) DEFAULT 'initial' CHECK (monitoring_phase IN ('initial', 'active_monitoring', 'maintenance', 'ongoing')),
ADD COLUMN IF NOT EXISTS last_progression_analysis TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS progression_summary JSONB;

-- RLS policies for photo_importance_markers
ALTER TABLE photo_importance_markers ENABLE ROW LEVEL SECURITY;

-- Users can only see and modify their own importance markers
CREATE POLICY photo_importance_user_policy ON photo_importance_markers
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service role bypass RLS
CREATE POLICY photo_importance_service_policy ON photo_importance_markers
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON photo_importance_markers TO authenticated;
GRANT ALL ON photo_importance_markers TO service_role;

-- Add comments for documentation
COMMENT ON COLUMN photo_analyses.quantitative_metrics IS 'Stores precise measurements like size_mm, RGB values, texture scores';
COMMENT ON COLUMN photo_analyses.condition_specific_scores IS 'Stores condition-specific metrics like ABCDE scores for moles';
COMMENT ON COLUMN photo_analyses.photo_quality_score IS 'Quality score of analyzed photos (0-100)';
COMMENT ON COLUMN photo_comparisons.measurement_deltas IS 'Quantitative changes between photos';
COMMENT ON COLUMN photo_comparisons.clinical_significance IS 'Medical interpretation of the changes';
COMMENT ON COLUMN photo_uploads.quality_score IS 'Photo quality score for importance calculation';
COMMENT ON TABLE photo_importance_markers IS 'User-marked important photos for prioritization in batching';
COMMENT ON COLUMN photo_sessions.monitoring_phase IS 'Current phase of monitoring: initial, active_monitoring, maintenance, ongoing';
COMMENT ON COLUMN photo_sessions.progression_summary IS 'Cached summary of progression analysis';

-- Migration completion message
DO $$
BEGIN
  RAISE NOTICE 'Photo analysis enhancements migration completed successfully';
END $$;
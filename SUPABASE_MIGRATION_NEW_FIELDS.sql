-- ============================================
-- SUPABASE MIGRATION: Add New Assessment Fields
-- ============================================
-- This migration adds columns to store the new enhanced fields
-- These are OPTIONAL columns - the API will generate them dynamically if not stored
-- But storing them allows for better analytics and historical tracking

-- 1. UPDATE general_assessments TABLE
-- Add columns for the new fields (all nullable for backward compatibility)
ALTER TABLE general_assessments 
ADD COLUMN IF NOT EXISTS severity_level TEXT CHECK (severity_level IN ('low', 'moderate', 'high', 'urgent')),
ADD COLUMN IF NOT EXISTS confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- Add indexes for filtering
CREATE INDEX IF NOT EXISTS idx_general_assessments_severity ON general_assessments(severity_level);
CREATE INDEX IF NOT EXISTS idx_general_assessments_confidence_level ON general_assessments(confidence_level);

-- 2. UPDATE general_deepdive_sessions TABLE
-- Add columns for enhanced deep dive responses
ALTER TABLE general_deepdive_sessions
ADD COLUMN IF NOT EXISTS severity_level TEXT CHECK (severity_level IN ('low', 'moderate', 'high', 'urgent')),
ADD COLUMN IF NOT EXISTS confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- 3. UPDATE quick_scans TABLE (OPTIONAL - only for analytics)
-- These are generated dynamically but can be stored for tracking
ALTER TABLE quick_scans
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- 4. UPDATE deep_dive_sessions TABLE (OPTIONAL - only for analytics)
-- These are generated dynamically but can be stored for tracking
ALTER TABLE deep_dive_sessions
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- 5. CREATE A VIEW for enhanced analytics (OPTIONAL)
-- This view combines all assessments with the new fields for reporting
CREATE OR REPLACE VIEW assessment_analytics AS
SELECT 
    'general' as assessment_type,
    id::text as id,
    user_id::text as user_id,
    created_at,
    severity_level,
    confidence_level,
    urgency_level as urgency,
    what_this_means,
    immediate_actions,
    red_flags,
    tracking_metrics,
    follow_up_timeline,
    category,
    confidence_score
FROM general_assessments
WHERE severity_level IS NOT NULL

UNION ALL

SELECT 
    'general_deepdive' as assessment_type,
    id::text as id,
    user_id::text as user_id,
    created_at,
    severity_level,
    confidence_level,
    CASE 
        WHEN final_analysis->>'urgency' IS NOT NULL THEN final_analysis->>'urgency'
        ELSE 'medium'
    END as urgency,
    what_this_means,
    immediate_actions,
    red_flags,
    tracking_metrics,
    follow_up_timeline,
    category,
    final_confidence as confidence_score
FROM general_deepdive_sessions
WHERE status = 'completed' AND severity_level IS NOT NULL

UNION ALL

SELECT 
    'quick_scan' as assessment_type,
    id::text as id,
    user_id::text as user_id,
    created_at,
    CASE 
        WHEN urgency_level = 'low' THEN 'low'
        WHEN urgency_level = 'medium' THEN 'moderate'
        WHEN urgency_level = 'high' THEN 'high'
        ELSE 'moderate'
    END as severity_level,
    CASE 
        WHEN confidence_score >= 80 THEN 'high'
        WHEN confidence_score >= 60 THEN 'medium'
        ELSE 'low'
    END as confidence_level,
    urgency_level as urgency,
    what_this_means,
    immediate_actions,
    COALESCE((analysis_result->>'redFlags')::jsonb, '[]'::jsonb) as red_flags,
    '[]'::jsonb as tracking_metrics,
    '{}'::jsonb as follow_up_timeline,
    body_part as category,
    confidence_score
FROM quick_scans
WHERE what_this_means IS NOT NULL

UNION ALL

SELECT 
    'deep_dive' as assessment_type,
    id::text as id,
    user_id::text as user_id,
    created_at,
    CASE 
        WHEN final_analysis->>'urgency' = 'low' THEN 'low'
        WHEN final_analysis->>'urgency' = 'medium' THEN 'moderate'
        WHEN final_analysis->>'urgency' = 'high' THEN 'high'
        ELSE 'moderate'
    END as severity_level,
    CASE 
        WHEN final_confidence >= 80 THEN 'high'
        WHEN final_confidence >= 60 THEN 'medium'
        ELSE 'low'
    END as confidence_level,
    COALESCE(final_analysis->>'urgency', 'medium') as urgency,
    what_this_means,
    immediate_actions,
    COALESCE((final_analysis->>'redFlags')::jsonb, '[]'::jsonb) as red_flags,
    '[]'::jsonb as tracking_metrics,
    '{}'::jsonb as follow_up_timeline,
    body_part as category,
    final_confidence as confidence_score
FROM deep_dive_sessions
WHERE status IN ('completed', 'analysis_ready') AND what_this_means IS NOT NULL;

-- 6. Add RLS policies if needed (adjust based on your setup)
-- Example for general_assessments
ALTER TABLE general_assessments ENABLE ROW LEVEL SECURITY;

-- 7. Grant permissions (adjust based on your roles)
GRANT SELECT ON assessment_analytics TO authenticated;
GRANT ALL ON general_assessments TO authenticated;
GRANT ALL ON general_deepdive_sessions TO authenticated;

-- ============================================
-- NOTES:
-- ============================================
-- 1. All new columns are NULLABLE - no existing data will break
-- 2. The API will dynamically generate these fields if not in DB
-- 3. Storing them is OPTIONAL but useful for:
--    - Analytics and reporting
--    - Historical tracking
--    - Performance (no need to regenerate)
-- 4. The view 'assessment_analytics' provides unified reporting
-- 5. You can run this migration safely - it uses IF NOT EXISTS
-- ============================================
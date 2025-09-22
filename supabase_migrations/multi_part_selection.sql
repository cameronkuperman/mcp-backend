-- =====================================================
-- MULTI-PART SELECTION MIGRATION
-- Adds support for selecting multiple body parts in scans
-- Run this in Supabase SQL Editor
-- =====================================================

-- Add body_parts array column to quick_scans table
ALTER TABLE quick_scans 
ADD COLUMN IF NOT EXISTS body_parts TEXT[] DEFAULT NULL,
ADD COLUMN IF NOT EXISTS is_multi_part BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS parts_relationship JSONB DEFAULT NULL;

-- Migrate existing body_part data to body_parts array
UPDATE quick_scans 
SET body_parts = ARRAY[body_part]::TEXT[]
WHERE body_part IS NOT NULL AND body_parts IS NULL;

-- Update is_multi_part flag based on array length
UPDATE quick_scans 
SET is_multi_part = (array_length(body_parts, 1) > 1)
WHERE body_parts IS NOT NULL;

-- Add body_parts array column to deep_dive_sessions table  
ALTER TABLE deep_dive_sessions
ADD COLUMN IF NOT EXISTS body_parts TEXT[] DEFAULT NULL,
ADD COLUMN IF NOT EXISTS is_multi_part BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS parts_relationship JSONB DEFAULT NULL;

-- Migrate existing body_part data to body_parts array
UPDATE deep_dive_sessions 
SET body_parts = ARRAY[body_part]::TEXT[]
WHERE body_part IS NOT NULL AND body_parts IS NULL;

-- Update is_multi_part flag based on array length
UPDATE deep_dive_sessions 
SET is_multi_part = (array_length(body_parts, 1) > 1)
WHERE body_parts IS NOT NULL;

-- Create optimized indexes for multi-part queries
CREATE INDEX IF NOT EXISTS idx_body_parts_gin 
ON quick_scans USING gin(body_parts);

CREATE INDEX IF NOT EXISTS idx_multi_part_scans 
ON quick_scans(user_id, created_at DESC) 
WHERE array_length(body_parts, 1) > 1;

CREATE INDEX IF NOT EXISTS idx_body_parts_gin_dive 
ON deep_dive_sessions USING gin(body_parts);

CREATE INDEX IF NOT EXISTS idx_multi_part_dives 
ON deep_dive_sessions(user_id, created_at DESC) 
WHERE array_length(body_parts, 1) > 1;

-- Add check constraints to ensure at least one body part when using array
ALTER TABLE quick_scans 
ADD CONSTRAINT check_body_parts_not_empty 
CHECK (body_parts IS NULL OR array_length(body_parts, 1) > 0);

ALTER TABLE deep_dive_sessions 
ADD CONSTRAINT check_body_parts_not_empty 
CHECK (body_parts IS NULL OR array_length(body_parts, 1) > 0);

-- Create a function to detect relationships between body parts
CREATE OR REPLACE FUNCTION detect_body_parts_relationship(parts TEXT[])
RETURNS TEXT AS $$
DECLARE
    -- Common related body part groups
    cardiac_parts TEXT[] := ARRAY['chest', 'left arm', 'left shoulder', 'jaw', 'neck'];
    neurological_parts TEXT[] := ARRAY['head', 'eyes', 'face', 'neck', 'spine'];
    digestive_parts TEXT[] := ARRAY['abdomen', 'stomach', 'chest', 'throat'];
    musculoskeletal_parts TEXT[] := ARRAY['back', 'neck', 'shoulders', 'hips', 'knees'];
    
    overlap_cardiac INTEGER := 0;
    overlap_neuro INTEGER := 0;
    overlap_digestive INTEGER := 0;
    overlap_musculo INTEGER := 0;
    max_overlap INTEGER := 0;
BEGIN
    IF array_length(parts, 1) = 1 THEN
        RETURN 'single';
    END IF;
    
    -- Check overlaps with each system
    overlap_cardiac := cardinality(parts::text[] && cardiac_parts::text[]);
    overlap_neuro := cardinality(parts::text[] && neurological_parts::text[]);
    overlap_digestive := cardinality(parts::text[] && digestive_parts::text[]);
    overlap_musculo := cardinality(parts::text[] && musculoskeletal_parts::text[]);
    
    max_overlap := GREATEST(overlap_cardiac, overlap_neuro, overlap_digestive, overlap_musculo);
    
    IF max_overlap >= 2 THEN
        RETURN 'related';
    ELSE
        RETURN 'unrelated';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Create view for multi-part scan analytics
CREATE OR REPLACE VIEW multi_part_scan_analytics AS
SELECT 
    user_id,
    DATE(created_at) as scan_date,
    array_length(body_parts, 1) as parts_count,
    detect_body_parts_relationship(body_parts) as relationship_type,
    urgency_level,
    COUNT(*) as scan_count
FROM quick_scans
WHERE body_parts IS NOT NULL
GROUP BY user_id, DATE(created_at), body_parts, urgency_level;

-- Add comments for documentation
COMMENT ON COLUMN quick_scans.body_parts IS 'Array of body parts selected for this scan (supports multi-selection)';
COMMENT ON COLUMN quick_scans.is_multi_part IS 'True if scan involves multiple body parts';
COMMENT ON COLUMN quick_scans.parts_relationship IS 'AI-detected relationship between selected parts and analysis metadata';

COMMENT ON COLUMN deep_dive_sessions.body_parts IS 'Array of body parts selected for this deep dive (supports multi-selection)';
COMMENT ON COLUMN deep_dive_sessions.is_multi_part IS 'True if deep dive involves multiple body parts';
COMMENT ON COLUMN deep_dive_sessions.parts_relationship IS 'AI-detected relationship between selected parts and analysis metadata';

-- Grant permissions
GRANT SELECT ON multi_part_scan_analytics TO authenticated;
GRANT SELECT ON multi_part_scan_analytics TO anon;
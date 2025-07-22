-- ============================================
-- Think Harder & Ultra Think Schema Updates
-- ============================================
-- This adds columns to store enhanced analysis results from Think Harder and Ultra Think features
-- Run this in your Supabase SQL editor

-- ============================================
-- 1. UPDATE QUICK_SCANS TABLE
-- ============================================

-- Add Think Harder columns
ALTER TABLE public.quick_scans
ADD COLUMN IF NOT EXISTS enhanced_analysis jsonb,
ADD COLUMN IF NOT EXISTS enhanced_confidence integer CHECK (enhanced_confidence >= 0 AND enhanced_confidence <= 100),
ADD COLUMN IF NOT EXISTS enhanced_model text,
ADD COLUMN IF NOT EXISTS enhanced_at timestamp with time zone;

-- Add O4-Mini columns
ALTER TABLE public.quick_scans
ADD COLUMN IF NOT EXISTS o4_mini_analysis jsonb,
ADD COLUMN IF NOT EXISTS o4_mini_confidence integer CHECK (o4_mini_confidence >= 0 AND o4_mini_confidence <= 100),
ADD COLUMN IF NOT EXISTS o4_mini_model text,
ADD COLUMN IF NOT EXISTS o4_mini_at timestamp with time zone;

-- Add Ultra Think columns
ALTER TABLE public.quick_scans
ADD COLUMN IF NOT EXISTS ultra_analysis jsonb,
ADD COLUMN IF NOT EXISTS ultra_confidence integer CHECK (ultra_confidence >= 0 AND ultra_confidence <= 100),
ADD COLUMN IF NOT EXISTS ultra_model text,
ADD COLUMN IF NOT EXISTS ultra_at timestamp with time zone;

-- ============================================
-- 2. UPDATE DEEP_DIVE_SESSIONS TABLE
-- ============================================

-- Add Think Harder columns
ALTER TABLE public.deep_dive_sessions
ADD COLUMN IF NOT EXISTS enhanced_analysis jsonb,
ADD COLUMN IF NOT EXISTS enhanced_confidence integer CHECK (enhanced_confidence >= 0 AND enhanced_confidence <= 100),
ADD COLUMN IF NOT EXISTS enhanced_model text,
ADD COLUMN IF NOT EXISTS enhanced_at timestamp with time zone;

-- Add Ultra Think columns (Deep Dive doesn't use O4-Mini)
ALTER TABLE public.deep_dive_sessions
ADD COLUMN IF NOT EXISTS ultra_analysis jsonb,
ADD COLUMN IF NOT EXISTS ultra_confidence integer CHECK (ultra_confidence >= 0 AND ultra_confidence <= 100),
ADD COLUMN IF NOT EXISTS ultra_model text,
ADD COLUMN IF NOT EXISTS ultra_at timestamp with time zone;

-- ============================================
-- 3. CREATE PERFORMANCE INDEXES
-- ============================================

-- Indexes for quick_scans
CREATE INDEX IF NOT EXISTS idx_quick_scans_enhanced_at ON public.quick_scans(enhanced_at);
CREATE INDEX IF NOT EXISTS idx_quick_scans_o4_mini_at ON public.quick_scans(o4_mini_at);
CREATE INDEX IF NOT EXISTS idx_quick_scans_ultra_at ON public.quick_scans(ultra_at);
CREATE INDEX IF NOT EXISTS idx_quick_scans_user_id_created ON public.quick_scans(user_id, created_at DESC);

-- Indexes for deep_dive_sessions
CREATE INDEX IF NOT EXISTS idx_deep_dive_enhanced_at ON public.deep_dive_sessions(enhanced_at);
CREATE INDEX IF NOT EXISTS idx_deep_dive_ultra_at ON public.deep_dive_sessions(ultra_at);
CREATE INDEX IF NOT EXISTS idx_deep_dive_user_id_created ON public.deep_dive_sessions(user_id, created_at DESC);

-- ============================================
-- 4. CREATE ANALYSIS PROGRESSION VIEW
-- ============================================

CREATE OR REPLACE VIEW public.analysis_progression AS
SELECT 
    'quick_scan' as analysis_type,
    id,
    user_id,
    body_part,
    created_at,
    confidence_score as original_confidence,
    enhanced_confidence,
    o4_mini_confidence,
    ultra_confidence,
    GREATEST(
        COALESCE(confidence_score, 0), 
        COALESCE(enhanced_confidence, 0), 
        COALESCE(o4_mini_confidence, 0), 
        COALESCE(ultra_confidence, 0)
    ) as max_confidence,
    CASE 
        WHEN ultra_confidence IS NOT NULL THEN 'ultra'
        WHEN o4_mini_confidence IS NOT NULL THEN 'o4_mini'
        WHEN enhanced_confidence IS NOT NULL THEN 'enhanced'
        ELSE 'original'
    END as highest_tier,
    analysis_result,
    enhanced_analysis,
    o4_mini_analysis,
    ultra_analysis
FROM public.quick_scans
UNION ALL
SELECT 
    'deep_dive' as analysis_type,
    id,
    user_id,
    body_part,
    created_at,
    final_confidence as original_confidence,
    enhanced_confidence,
    NULL as o4_mini_confidence,
    ultra_confidence,
    GREATEST(
        COALESCE(final_confidence, 0), 
        COALESCE(enhanced_confidence, 0), 
        COALESCE(ultra_confidence, 0)
    ) as max_confidence,
    CASE 
        WHEN ultra_confidence IS NOT NULL THEN 'ultra'
        WHEN enhanced_confidence IS NOT NULL THEN 'enhanced'
        ELSE 'original'
    END as highest_tier,
    final_analysis as analysis_result,
    enhanced_analysis,
    NULL as o4_mini_analysis,
    ultra_analysis
FROM public.deep_dive_sessions
WHERE status IN ('completed', 'analysis_ready');  -- Include analysis_ready for Ask Me More support

-- ============================================
-- 5. HELPER FUNCTIONS (Optional)
-- ============================================

-- Function to get the best available analysis for a quick scan
CREATE OR REPLACE FUNCTION get_best_quick_scan_analysis(scan_id uuid)
RETURNS jsonb AS $$
BEGIN
    RETURN (
        SELECT 
            COALESCE(
                ultra_analysis,
                o4_mini_analysis,
                enhanced_analysis,
                analysis_result
            )
        FROM public.quick_scans
        WHERE id = scan_id
    );
END;
$$ LANGUAGE plpgsql;

-- Function to get the best available analysis for a deep dive
CREATE OR REPLACE FUNCTION get_best_deep_dive_analysis(session_id uuid)
RETURNS jsonb AS $$
BEGIN
    RETURN (
        SELECT 
            COALESCE(
                ultra_analysis,
                enhanced_analysis,
                final_analysis
            )
        FROM public.deep_dive_sessions
        WHERE id = session_id
    );
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. RLS POLICIES (If you have Row Level Security enabled)
-- ============================================

-- Enable RLS on tables if not already enabled
-- ALTER TABLE public.quick_scans ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.deep_dive_sessions ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (uncomment and modify as needed)
-- CREATE POLICY "Users can view their own quick scans" ON public.quick_scans
--     FOR SELECT USING (auth.uid()::text = user_id);

-- CREATE POLICY "Users can view their own deep dive sessions" ON public.deep_dive_sessions
--     FOR SELECT USING (auth.uid()::text = user_id);

-- ============================================
-- 7. GRANT PERMISSIONS (if needed)
-- ============================================

-- Grant access to the view
GRANT SELECT ON public.analysis_progression TO authenticated;
GRANT EXECUTE ON FUNCTION get_best_quick_scan_analysis TO authenticated;
GRANT EXECUTE ON FUNCTION get_best_deep_dive_analysis TO authenticated;
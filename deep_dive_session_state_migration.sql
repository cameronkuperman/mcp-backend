-- ============================================
-- Deep Dive Session State Migration
-- ============================================
-- This adds support for the analysis_ready state and Ask Me More functionality
-- Run this in your Supabase SQL editor

-- ============================================
-- 1. UPDATE CHECK CONSTRAINT FOR SESSION STATUS
-- ============================================

-- First, drop the existing constraint
ALTER TABLE public.deep_dive_sessions 
DROP CONSTRAINT IF EXISTS deep_dive_sessions_status_check;

-- Add new constraint with analysis_ready state
ALTER TABLE public.deep_dive_sessions
ADD CONSTRAINT deep_dive_sessions_status_check 
CHECK (status = ANY (ARRAY['active'::text, 'analysis_ready'::text, 'completed'::text, 'abandoned'::text]));

-- ============================================
-- 2. ADD NEW COLUMNS FOR ASK ME MORE SUPPORT
-- ============================================

-- Add columns to track Ask Me More functionality
ALTER TABLE public.deep_dive_sessions
ADD COLUMN IF NOT EXISTS allow_more_questions BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS initial_questions_count INTEGER,
ADD COLUMN IF NOT EXISTS additional_questions_count INTEGER DEFAULT 0;

-- ============================================
-- 3. UPDATE EXISTING SESSIONS
-- ============================================

-- Update recently completed sessions to analysis_ready to allow Ask Me More
-- Only for sessions completed in the last 7 days
UPDATE public.deep_dive_sessions 
SET 
    status = 'analysis_ready',
    allow_more_questions = TRUE,
    initial_questions_count = COALESCE(array_length(questions, 1), 0)
WHERE 
    status = 'completed' 
    AND completed_at > NOW() - INTERVAL '7 days'
    AND final_confidence < 90;  -- Only for sessions that could benefit from more questions

-- ============================================
-- 4. CREATE INDEX FOR PERFORMANCE
-- ============================================

-- Index for finding analysis_ready sessions
CREATE INDEX IF NOT EXISTS idx_deep_dive_analysis_ready 
ON public.deep_dive_sessions(status, allow_more_questions) 
WHERE status = 'analysis_ready';

-- ============================================
-- 5. ADD FUNCTION TO CHECK ASK ME MORE ELIGIBILITY
-- ============================================

CREATE OR REPLACE FUNCTION can_ask_more_questions(session_id uuid)
RETURNS boolean AS $$
DECLARE
    session_record RECORD;
BEGIN
    SELECT 
        status,
        allow_more_questions,
        initial_questions_count,
        additional_questions_count,
        final_confidence
    INTO session_record
    FROM public.deep_dive_sessions
    WHERE id = session_id;
    
    -- Check if session exists
    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;
    
    -- Check if session is in valid state
    IF session_record.status NOT IN ('analysis_ready', 'completed') THEN
        RETURN FALSE;
    END IF;
    
    -- Check if Ask Me More is allowed
    IF NOT session_record.allow_more_questions THEN
        RETURN FALSE;
    END IF;
    
    -- Check if we've reached the 5 additional questions limit
    IF session_record.additional_questions_count >= 5 THEN
        RETURN FALSE;
    END IF;
    
    -- Check if confidence is already high enough
    IF session_record.final_confidence >= 95 THEN
        RETURN FALSE;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 6. ADD TRIGGER TO TRACK ADDITIONAL QUESTIONS
-- ============================================

CREATE OR REPLACE FUNCTION update_additional_questions_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Only count questions added after initial analysis
    IF NEW.status IN ('analysis_ready', 'completed') AND OLD.status = 'analysis_ready' THEN
        NEW.additional_questions_count = COALESCE(
            array_length(NEW.questions, 1) - COALESCE(NEW.initial_questions_count, 0),
            0
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS track_additional_questions ON public.deep_dive_sessions;
CREATE TRIGGER track_additional_questions
BEFORE UPDATE ON public.deep_dive_sessions
FOR EACH ROW
EXECUTE FUNCTION update_additional_questions_count();

-- ============================================
-- 7. GRANT PERMISSIONS
-- ============================================

-- Grant execute permission on the new function
GRANT EXECUTE ON FUNCTION can_ask_more_questions TO authenticated;

-- ============================================
-- 8. UPDATE VIEW TO INCLUDE NEW STATE
-- ============================================

-- Update the analysis_progression view to handle analysis_ready state
DROP VIEW IF EXISTS public.analysis_progression;
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
WHERE status IN ('completed', 'analysis_ready');  -- Include analysis_ready sessions

-- Grant access to the updated view
GRANT SELECT ON public.analysis_progression TO authenticated;
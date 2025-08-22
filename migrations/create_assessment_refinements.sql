-- Migration: Create general_assessment_refinements table
-- Purpose: Store refined analyses from follow-up questions on general assessments
-- Created: 2025-01-20

-- Create table for storing refinements of general assessments
CREATE TABLE IF NOT EXISTS public.general_assessment_refinements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES general_assessments(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    
    -- Q&A Data
    follow_up_questions JSONB NOT NULL,  -- Original questions from assessment
    answers JSONB NOT NULL,               -- User's answers [{question: "...", answer: "..."}]
    
    -- Refined Analysis Results
    refined_analysis JSONB NOT NULL,
    refined_confidence FLOAT CHECK (refined_confidence >= 0 AND refined_confidence <= 100),
    original_confidence FLOAT,           -- Store original for comparison
    confidence_improvement FLOAT 
     ALWAYS AS (refined_confidence - original_confidence) STORED,
    
    -- Enhanced diagnostic fields (matching general_assessments structure)
    severity_level TEXT CHECK (severity_level IN ('low', 'moderate', 'high', 'urgent')),
    confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
    what_this_means TEXT,
    immediate_actions JSONB DEFAULT '[]'::jsonb,
    red_flags JSONB DEFAULT '[]'::jsonb,
    tracking_metrics JSONB DEFAULT '[]'::jsonb,
    follow_up_timeline JSONB DEFAULT '{}'::jsonb,
    
    -- Additional refinement-specific fields
    differential_diagnoses JSONB,        -- More specific differential after refinement
    diagnostic_certainty TEXT,           -- 'provisional', 'probable', 'definitive'
    next_steps JSONB,                    -- Clear next steps based on refinement
    
    -- Metadata
    model_used TEXT,
    processing_time_ms INTEGER,
    refinement_number INTEGER DEFAULT 1,  -- Support multiple refinements
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_refinements_assessment ON general_assessment_refinements(assessment_id);
CREATE INDEX idx_refinements_user ON general_assessment_refinements(user_id, created_at DESC);
CREATE INDEX idx_refinements_created ON general_assessment_refinements(created_at DESC);

-- Add comment for documentation
COMMENT ON TABLE general_assessment_refinements IS 'Stores refined analyses from answering follow-up questions on general assessments';
COMMENT ON COLUMN general_assessment_refinements.assessment_id IS 'Reference to the original general assessment';
COMMENT ON COLUMN general_assessment_refinements.follow_up_questions IS 'Original follow-up questions from the assessment';
COMMENT ON COLUMN general_assessment_refinements.answers IS 'User answers to the follow-up questions';
COMMENT ON COLUMN general_assessment_refinements.refined_analysis IS 'Complete refined analysis after incorporating answers';
COMMENT ON COLUMN general_assessment_refinements.confidence_improvement IS 'How much the confidence improved (auto-calculated)';
COMMENT ON COLUMN general_assessment_refinements.diagnostic_certainty IS 'Level of diagnostic certainty after refinement';
COMMENT ON COLUMN general_assessment_refinements.refinement_number IS 'Supports multiple refinements of the same assessment';

-- Grant permissions (adjust based on your setup)
GRANT ALL ON general_assessment_refinements TO authenticated;
GRANT SELECT ON general_assessment_refinements TO anon;
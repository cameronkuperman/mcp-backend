-- ============================================
-- COMPLETE SUPABASE MIGRATION FOR NEW FIELDS
-- Run this to add all columns for storing the enhanced response fields
-- ============================================

-- 1. QUICK SCANS TABLE - Add 2 new fields
-- These fields are ALREADY returned by the API (generated dynamically)
-- Adding columns allows us to store them for analytics
ALTER TABLE quick_scans 
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- Note: Quick Scan ALREADY has these fields in the analysis_result JSON:
-- redFlags, selfCare, timeline, followUp, relatedSymptoms, recommendations, differentials
-- We're only adding what_this_means and immediate_actions as new fields

-- 2. DEEP DIVE SESSIONS TABLE - Add 2 new fields
ALTER TABLE deep_dive_sessions
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- Note: Deep Dive ALREADY has these fields in the final_analysis JSON:
-- redFlags, selfCare, timeline, followUp, relatedSymptoms, recommendations, differentials, reasoning_snippets
-- We're only adding what_this_means and immediate_actions as new fields

-- 3. GENERAL ASSESSMENTS TABLE - Add ALL 7 new fields
-- This table gets the full enhancement
ALTER TABLE general_assessments 
ADD COLUMN IF NOT EXISTS severity_level TEXT CHECK (severity_level IN ('low', 'moderate', 'high', 'urgent')),
ADD COLUMN IF NOT EXISTS confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- 4. GENERAL DEEPDIVE SESSIONS TABLE - Add ALL 7 new fields
ALTER TABLE general_deepdive_sessions
ADD COLUMN IF NOT EXISTS severity_level TEXT CHECK (severity_level IN ('low', 'moderate', 'high', 'urgent')),
ADD COLUMN IF NOT EXISTS confidence_level TEXT CHECK (confidence_level IN ('low', 'medium', 'high')),
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- 5. ADD INDEXES for better query performance
CREATE INDEX IF NOT EXISTS idx_quick_scans_what_this_means ON quick_scans(what_this_means) WHERE what_this_means IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deep_dive_what_this_means ON deep_dive_sessions(what_this_means) WHERE what_this_means IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_general_assessments_severity ON general_assessments(severity_level);
CREATE INDEX IF NOT EXISTS idx_general_assessments_confidence ON general_assessments(confidence_level);
CREATE INDEX IF NOT EXISTS idx_general_deepdive_severity ON general_deepdive_sessions(severity_level);
CREATE INDEX IF NOT EXISTS idx_general_deepdive_confidence ON general_deepdive_sessions(confidence_level);

-- ============================================
-- VERIFICATION QUERIES - Run these to check the migration worked
-- ============================================

-- Check Quick Scans columns
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'quick_scans' 
-- AND column_name IN ('what_this_means', 'immediate_actions');

-- Check Deep Dive columns
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'deep_dive_sessions' 
-- AND column_name IN ('what_this_means', 'immediate_actions');

-- Check General Assessments columns (should have 7 new columns)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'general_assessments' 
-- AND column_name IN ('severity_level', 'confidence_level', 'what_this_means', 
--                      'immediate_actions', 'red_flags', 'tracking_metrics', 'follow_up_timeline');

-- Check General Deep Dive columns (should have 7 new columns)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'general_deepdive_sessions' 
-- AND column_name IN ('severity_level', 'confidence_level', 'what_this_means', 
--                      'immediate_actions', 'red_flags', 'tracking_metrics', 'follow_up_timeline');

-- ============================================
-- SUMMARY OF CHANGES:
-- ============================================
-- Quick Scans: +2 fields (what_this_means, immediate_actions)
-- Deep Dive Sessions: +2 fields (what_this_means, immediate_actions)
-- General Assessments: +7 fields (all enhanced fields)
-- General Deep Dive Sessions: +7 fields (all enhanced fields)
-- 
-- Total: 18 new columns across 4 tables
-- ============================================
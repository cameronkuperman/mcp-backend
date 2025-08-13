-- ============================================
-- SIMPLIFIED SUPABASE MIGRATION
-- Just add the columns - skip the view if it has issues
-- ============================================

-- 1. General Assessments - Add ALL 7 new fields
ALTER TABLE general_assessments 
ADD COLUMN IF NOT EXISTS severity_level TEXT,
ADD COLUMN IF NOT EXISTS confidence_level TEXT,
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- 2. General Deep Dive Sessions - Add ALL 7 new fields
ALTER TABLE general_deepdive_sessions
ADD COLUMN IF NOT EXISTS severity_level TEXT,
ADD COLUMN IF NOT EXISTS confidence_level TEXT,
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS red_flags JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS tracking_metrics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS follow_up_timeline JSONB DEFAULT '{}'::jsonb;

-- 3. Quick Scans - Add 2 minimal fields
ALTER TABLE quick_scans
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- 4. Deep Dive Sessions - Add 2 minimal fields
ALTER TABLE deep_dive_sessions
ADD COLUMN IF NOT EXISTS what_this_means TEXT,
ADD COLUMN IF NOT EXISTS immediate_actions JSONB DEFAULT '[]'::jsonb;

-- ============================================
-- THAT'S IT! This adds all the columns.
-- The API will populate these automatically.
-- ============================================
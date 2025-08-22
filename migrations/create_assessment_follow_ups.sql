-- Assessment Follow-Up System Migration
-- Purpose: Implement temporal follow-up tracking with event sourcing for medical assessments
-- Created: 2025-01-22
-- Following FAANG scalability best practices with immutable records and event sourcing

-- Create enum for follow-up status if not exists
DO $$ BEGIN
    CREATE TYPE follow_up_status AS ENUM (
        'pending',      -- Follow-up scheduled but not started
        'in_progress',  -- User is answering questions
        'completed',    -- Follow-up completed
        'abandoned'     -- User started but didn't finish
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create enum for assessment source types
DO $$ BEGIN
    CREATE TYPE assessment_source_type AS ENUM (
        'quick_scan',
        'deep_dive',
        'general_assessment',
        'general_deepdive',
        'follow_up'  -- Follow-ups can chain to other follow-ups
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 1. Main follow-up table - stores completed follow-up assessments
CREATE TABLE IF NOT EXISTS public.assessment_follow_ups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL,  -- Links all follow-ups in a chain
    user_id UUID REFERENCES auth.users(id),
    
    -- Source assessment reference (polymorphic)
    source_type assessment_source_type NOT NULL,
    source_id UUID NOT NULL,  -- ID of the original assessment
    parent_follow_up_id UUID REFERENCES assessment_follow_ups(id),  -- If this is a follow-up to a follow-up
    
    -- Temporal tracking
    original_assessment_date TIMESTAMPTZ NOT NULL,
    days_since_original INTEGER NOT NULL,
    days_since_last_followup INTEGER,
    follow_up_number INTEGER NOT NULL DEFAULT 1,  -- Position in the chain
    
    -- Base questions and responses (5 standard questions)
    base_responses JSONB NOT NULL DEFAULT '{}'::jsonb,
    /* Structure:
    {
        "changes_since_last": "much_better|somewhat_better|no_change|somewhat_worse|much_worse",
        "specific_changes": "text describing changes",
        "severity_change": "much_worse|somewhat_worse|same|somewhat_better|much_better",
        "new_triggers": {"found": true/false, "description": "text"},
        "saw_doctor": true/false
    }
    */
    
    -- AI-generated questions and responses (3 custom questions)
    ai_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
    /* Structure:
    [
        {
            "question": "Specific question text",
            "question_type": "symptom_specific|treatment_tracking|pattern_discovery",
            "response": "User's answer"
        }
    ]
    */
    
    -- Medical visit information (if saw_doctor = true)
    medical_visit JSONB,
    /* Structure:
    {
        "provider_type": "primary|specialist|urgent_care|er|telehealth",
        "provider_specialty": "text if specialist",
        "assessment": "What doctor said",
        "treatments": "Medications/procedures started",
        "follow_up_timing": "When to follow up",
        "layman_explanation": "AI-generated plain English explanation of medical terms"
    }
    */
    
    -- Analysis results
    analysis_result JSONB NOT NULL,
    primary_assessment TEXT NOT NULL,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    confidence_change FLOAT,  -- Change from previous assessment
    diagnostic_certainty TEXT CHECK (diagnostic_certainty IN ('provisional', 'probable', 'definitive')),
    
    -- Evolution tracking
    assessment_evolution JSONB NOT NULL,
    /* Structure:
    {
        "original_assessment": "Initial diagnosis",
        "current_assessment": "Current diagnosis",
        "confidence_progression": [60, 75, 85],  -- Array of confidence scores over time
        "diagnosis_refined": true/false,
        "key_discoveries": ["Pattern found", "Trigger identified"]
    }
    */
    
    -- Pattern insights
    pattern_insights JSONB,
    discovered_patterns TEXT[],
    concerning_patterns TEXT[],
    
    -- Treatment tracking
    treatment_efficacy JSONB,
    /* Structure:
    {
        "working": ["Treatment A", "Treatment B"],
        "not_working": ["Treatment C"],
        "should_try": ["Treatment D"]
    }
    */
    
    -- Recommendations
    recommendations TEXT[],
    immediate_actions TEXT[],
    red_flags TEXT[],
    urgency_level TEXT CHECK (urgency_level IN ('low', 'medium', 'high', 'emergency')),
    next_follow_up_suggested TEXT,  -- "3 days", "1 week", "as needed", etc.
    
    -- Metadata
    model_used TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 2. Follow-up events table for event sourcing pattern
CREATE TABLE IF NOT EXISTS public.follow_up_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id UUID NOT NULL,
    follow_up_id UUID REFERENCES assessment_follow_ups(id),
    user_id UUID REFERENCES auth.users(id),
    
    -- Event details
    event_type TEXT NOT NULL CHECK (event_type IN (
        'follow_up_scheduled',
        'follow_up_started',
        'question_answered',
        'medical_visit_added',
        'follow_up_completed',
        'follow_up_abandoned',
        'pattern_discovered',
        'confidence_milestone',  -- e.g., reached 90% confidence
        'diagnosis_changed',
        'treatment_efficacy_noted'
    )),
    
    event_data JSONB NOT NULL,
    event_timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- For audit trail
    session_id TEXT,  -- Frontend session tracking
    ip_address INET,
    user_agent TEXT
);

-- 3. Medical visits table (normalized for better querying)
CREATE TABLE IF NOT EXISTS public.medical_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    follow_up_id UUID REFERENCES assessment_follow_ups(id),
    
    -- Visit details
    visit_date DATE NOT NULL,
    provider_type TEXT NOT NULL,
    provider_name TEXT,
    provider_specialty TEXT,
    
    -- Medical information
    chief_complaint TEXT,
    assessment TEXT NOT NULL,
    diagnosis_codes TEXT[],  -- ICD codes if available
    procedures_performed TEXT[],
    medications_prescribed JSONB,  -- [{name, dosage, frequency, duration}]
    lab_tests_ordered TEXT[],
    imaging_ordered TEXT[],
    
    -- AI enhancements
    layman_explanation TEXT,  -- AI-generated plain English
    key_takeaways TEXT[],
    action_items TEXT[],
    
    -- Follow-up
    follow_up_required BOOLEAN DEFAULT FALSE,
    follow_up_timing TEXT,
    referrals_made JSONB,  -- [{specialty, reason, urgency}]
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Follow-up scheduling table (for reminder system)
CREATE TABLE IF NOT EXISTS public.follow_up_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    chain_id UUID NOT NULL,
    source_assessment_id UUID NOT NULL,
    
    -- Scheduling
    scheduled_date DATE NOT NULL,
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_sent_at TIMESTAMPTZ,
    
    -- Status
    status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'reminder_sent', 'completed', 'cancelled')),
    completed_follow_up_id UUID REFERENCES assessment_follow_ups(id),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_follow_ups_chain ON assessment_follow_ups(chain_id, follow_up_number);
CREATE INDEX idx_follow_ups_user ON assessment_follow_ups(user_id, created_at DESC);
CREATE INDEX idx_follow_ups_source ON assessment_follow_ups(source_type, source_id);
CREATE INDEX idx_follow_ups_parent ON assessment_follow_ups(parent_follow_up_id) WHERE parent_follow_up_id IS NOT NULL;
CREATE INDEX idx_follow_ups_confidence ON assessment_follow_ups(confidence_score DESC);
CREATE INDEX idx_follow_ups_urgency ON assessment_follow_ups(urgency_level, created_at DESC);
CREATE INDEX idx_follow_ups_created ON assessment_follow_ups(created_at DESC);

CREATE INDEX idx_events_chain ON follow_up_events(chain_id, event_timestamp);
CREATE INDEX idx_events_follow_up ON follow_up_events(follow_up_id, event_timestamp);
CREATE INDEX idx_events_user ON follow_up_events(user_id, event_timestamp DESC);
CREATE INDEX idx_events_type ON follow_up_events(event_type, event_timestamp DESC);

CREATE INDEX idx_medical_visits_user ON medical_visits(user_id, visit_date DESC);
CREATE INDEX idx_medical_visits_follow_up ON medical_visits(follow_up_id);
CREATE INDEX idx_medical_visits_date ON medical_visits(visit_date DESC);

CREATE INDEX idx_schedules_user ON follow_up_schedules(user_id, scheduled_date);
CREATE INDEX idx_schedules_date ON follow_up_schedules(scheduled_date) WHERE status = 'scheduled';
CREATE INDEX idx_schedules_chain ON follow_up_schedules(chain_id);

-- Create composite indexes for common query patterns
CREATE INDEX idx_follow_ups_user_chain ON assessment_follow_ups(user_id, chain_id, follow_up_number);
CREATE INDEX idx_follow_ups_temporal ON assessment_follow_ups(chain_id, days_since_original);

-- Add comments for documentation
COMMENT ON TABLE assessment_follow_ups IS 'Stores follow-up assessments with temporal tracking and progression analysis';
COMMENT ON TABLE follow_up_events IS 'Event sourcing table tracking all follow-up interactions and discoveries';
COMMENT ON TABLE medical_visits IS 'Normalized medical visit data with AI-enhanced explanations';
COMMENT ON TABLE follow_up_schedules IS 'Manages follow-up scheduling and reminders';

COMMENT ON COLUMN assessment_follow_ups.chain_id IS 'UUID linking all related follow-ups in a temporal chain';
COMMENT ON COLUMN assessment_follow_ups.diagnostic_certainty IS 'Medical certainty level: provisional (initial), probable (likely), definitive (confirmed)';
COMMENT ON COLUMN assessment_follow_ups.assessment_evolution IS 'Tracks how the diagnosis has evolved over the follow-up chain';
COMMENT ON COLUMN medical_visits.layman_explanation IS 'AI-generated plain English explanation of medical terminology';

-- Create a view for easy chain querying
CREATE OR REPLACE VIEW follow_up_chains AS
SELECT 
    af.chain_id,
    af.user_id,
    af.source_type,
    af.source_id,
    COUNT(*) as total_follow_ups,
    MIN(af.created_at) as chain_started,
    MAX(af.created_at) as last_follow_up,
    MAX(af.confidence_score) as peak_confidence,
    ARRAY_AGG(af.primary_assessment ORDER BY af.follow_up_number) as assessment_progression,
    ARRAY_AGG(af.confidence_score ORDER BY af.follow_up_number) as confidence_progression,
    MAX(af.follow_up_number) as latest_follow_up_number,
    BOOL_OR(af.medical_visit IS NOT NULL) as has_medical_visits
FROM assessment_follow_ups af
GROUP BY af.chain_id, af.user_id, af.source_type, af.source_id;

-- Grant permissions
GRANT ALL ON assessment_follow_ups TO authenticated;
GRANT ALL ON follow_up_events TO authenticated;
GRANT ALL ON medical_visits TO authenticated;
GRANT ALL ON follow_up_schedules TO authenticated;
GRANT SELECT ON follow_up_chains TO authenticated;

GRANT SELECT ON assessment_follow_ups TO anon;
GRANT SELECT ON follow_up_chains TO anon;

-- Add RLS policies (adjust based on your security requirements)
ALTER TABLE assessment_follow_ups ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_schedules ENABLE ROW LEVEL SECURITY;

-- Users can only see their own follow-ups
CREATE POLICY "Users can view own follow-ups" ON assessment_follow_ups
    FOR SELECT USING (auth.uid() = user_id);
    
CREATE POLICY "Users can create own follow-ups" ON assessment_follow_ups
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own events" ON follow_up_events
    FOR SELECT USING (auth.uid() = user_id);
    
CREATE POLICY "Users can create own events" ON follow_up_events
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view own medical visits" ON medical_visits
    FOR SELECT USING (auth.uid() = user_id);
    
CREATE POLICY "Users can manage own medical visits" ON medical_visits
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own schedules" ON follow_up_schedules
    FOR ALL USING (auth.uid() = user_id);
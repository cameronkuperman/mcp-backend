-- General Assessment System Database Migration
-- This creates all tables needed for the general health assessment feature

-- 1. Create enum for assessment categories (if not exists)
DO $$ BEGIN
    CREATE TYPE assessment_category AS ENUM (
        'energy', 
        'mental', 
        'sick', 
        'medication', 
        'multiple', 
        'unsure', 
        'physical'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. Flash Assessments Table (quick text-based triage)
CREATE TABLE IF NOT EXISTS flash_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    
    -- Input
    user_query TEXT NOT NULL,
    
    -- AI Response
    ai_response TEXT NOT NULL,
    main_concern TEXT,
    urgency TEXT CHECK (urgency IN ('low', 'medium', 'high', 'emergency')),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    
    -- Recommendations
    suggested_next_action TEXT CHECK (suggested_next_action IN ('general-assessment', 'body-scan', 'see-doctor', 'monitor')),
    should_use_general_assessment BOOLEAN DEFAULT FALSE,
    should_use_body_scan BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    model_used TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. General Assessments Table (structured category-based)
CREATE TABLE IF NOT EXISTS general_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    
    -- Category & Input
    category assessment_category NOT NULL,
    form_data JSONB NOT NULL,
    
    -- Analysis
    analysis_result JSONB NOT NULL,
    primary_assessment TEXT,
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    urgency_level TEXT CHECK (urgency_level IN ('low', 'medium', 'high', 'emergency')),
    
    -- Recommendations
    recommendations TEXT[],
    follow_up_needed BOOLEAN DEFAULT FALSE,
    doctor_visit_suggested BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    model_used TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. General Deep Dive Sessions (conversational multi-step)
CREATE TABLE IF NOT EXISTS general_deepdive_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    
    -- Initial context
    category assessment_category NOT NULL,
    initial_complaint TEXT NOT NULL,
    form_data JSONB,
    
    -- Session state
    questions JSONB[] DEFAULT '{}',
    answers JSONB[] DEFAULT '{}',
    current_step INTEGER DEFAULT 0,
    internal_state JSONB,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'analysis_ready', 'completed', 'abandoned')),
    
    -- Final analysis
    final_analysis JSONB,
    final_confidence FLOAT,
    key_findings TEXT[],
    reasoning_snippets TEXT[],
    
    -- Metadata
    model_used TEXT,
    session_duration_ms INTEGER,
    total_tokens_used INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    CONSTRAINT valid_session_state CHECK (
        (status = 'completed' AND final_analysis IS NOT NULL) OR
        (status != 'completed')
    )
);

-- 5. Timeline Events Table (unified health history)
CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    
    -- Event type and source
    event_type TEXT NOT NULL CHECK (event_type IN ('flash', 'general_quick', 'general_deep', 'body_quick', 'body_deep', 'photo', 'chat')),
    event_category TEXT NOT NULL CHECK (event_category IN ('body', 'general', 'photo', 'chat')),
    
    -- Reference
    source_table TEXT NOT NULL,
    source_id UUID NOT NULL,
    
    -- Display data
    title TEXT NOT NULL,
    summary TEXT,
    icon_type TEXT,
    color_scheme TEXT,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'emergency')),
    confidence FLOAT,
    
    -- Grouping
    thread_id UUID,
    is_follow_up BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    metadata JSONB,
    tags TEXT[],
    
    -- Timestamps
    event_timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES for performance
CREATE INDEX IF NOT EXISTS idx_flash_user ON flash_assessments(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_general_user ON general_assessments(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_general_category ON general_assessments(category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deepdive_user ON general_deepdive_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deepdive_status ON general_deepdive_sessions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_user ON timeline_events(user_id, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_category ON timeline_events(user_id, event_category, event_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_timeline_source ON timeline_events(source_table, source_id);

-- AUTO-GENERATE TIMELINE EVENTS WITH TRIGGERS
CREATE OR REPLACE FUNCTION create_timeline_event() RETURNS TRIGGER AS $$
BEGIN
    -- Skip if no user_id
    IF NEW.user_id IS NULL THEN
        RETURN NEW;
    END IF;

    INSERT INTO timeline_events (
        user_id,
        event_type,
        event_category,
        source_table,
        source_id,
        title,
        summary,
        icon_type,
        color_scheme,
        severity,
        confidence,
        event_timestamp
    ) VALUES (
        NEW.user_id,
        CASE
            WHEN TG_TABLE_NAME = 'flash_assessments' THEN 'flash'
            WHEN TG_TABLE_NAME = 'general_assessments' THEN 'general_quick'
            WHEN TG_TABLE_NAME = 'general_deepdive_sessions' THEN 'general_deep'
            WHEN TG_TABLE_NAME = 'quick_scans' THEN 'body_quick'
            WHEN TG_TABLE_NAME = 'deep_dive_sessions' THEN 'body_deep'
        END,
        CASE
            WHEN TG_TABLE_NAME LIKE '%general%' OR TG_TABLE_NAME = 'flash_assessments' THEN 'general'
            ELSE 'body'
        END,
        TG_TABLE_NAME,
        NEW.id,
        CASE
            WHEN TG_TABLE_NAME = 'flash_assessments' THEN 'Flash: ' || LEFT(NEW.user_query, 50)
            WHEN TG_TABLE_NAME = 'general_assessments' THEN 'General Assessment: ' || NEW.category::text
            WHEN TG_TABLE_NAME = 'general_deepdive_sessions' THEN 'Deep Dive: ' || NEW.category::text
            ELSE 'Health Assessment'
        END,
        CASE
            WHEN TG_TABLE_NAME = 'flash_assessments' THEN NEW.main_concern
            WHEN TG_TABLE_NAME = 'general_assessments' THEN NEW.primary_assessment
            ELSE NULL
        END,
        CASE
            WHEN TG_TABLE_NAME = 'flash_assessments' THEN 'sparkles'
            WHEN TG_TABLE_NAME LIKE '%deep%' THEN 'brain'
            ELSE 'zap'
        END,
        CASE
            WHEN TG_TABLE_NAME = 'flash_assessments' THEN 'amber'
            WHEN TG_TABLE_NAME LIKE '%deep%' THEN 'indigo'
            ELSE 'emerald'
        END,
        COALESCE(NEW.urgency_level, NEW.urgency),
        NEW.confidence_score,
        NEW.created_at
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for each table
DROP TRIGGER IF EXISTS create_flash_timeline ON flash_assessments;
CREATE TRIGGER create_flash_timeline
    AFTER INSERT ON flash_assessments
    FOR EACH ROW EXECUTE FUNCTION create_timeline_event();

DROP TRIGGER IF EXISTS create_general_timeline ON general_assessments;
CREATE TRIGGER create_general_timeline
    AFTER INSERT ON general_assessments
    FOR EACH ROW EXECUTE FUNCTION create_timeline_event();

DROP TRIGGER IF EXISTS create_deepdive_timeline ON general_deepdive_sessions;
CREATE TRIGGER create_deepdive_timeline
    AFTER INSERT ON general_deepdive_sessions
    FOR EACH ROW EXECUTE FUNCTION create_timeline_event();

-- Row Level Security (RLS)
ALTER TABLE flash_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE general_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE general_deepdive_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY;

-- RLS Policies - Users can only see their own data
CREATE POLICY "Users can view own flash assessments" ON flash_assessments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own general assessments" ON general_assessments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own deepdive sessions" ON general_deepdive_sessions
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can view own timeline events" ON timeline_events
    FOR ALL USING (auth.uid() = user_id);

-- Service role can access everything (for backend)
CREATE POLICY "Service role has full access to flash" ON flash_assessments
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to general" ON general_assessments
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to deepdive" ON general_deepdive_sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access to timeline" ON timeline_events
    FOR ALL USING (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON flash_assessments TO authenticated;
GRANT ALL ON general_assessments TO authenticated;
GRANT ALL ON general_deepdive_sessions TO authenticated;
GRANT ALL ON timeline_events TO authenticated;
GRANT ALL ON flash_assessments TO service_role;
GRANT ALL ON general_assessments TO service_role;
GRANT ALL ON general_deepdive_sessions TO service_role;
GRANT ALL ON timeline_events TO service_role;

-- Add comments for documentation
COMMENT ON TABLE flash_assessments IS 'Quick text-based health triage assessments';
COMMENT ON TABLE general_assessments IS 'Structured category-based health assessments';
COMMENT ON TABLE general_deepdive_sessions IS 'Multi-step conversational health assessments';
COMMENT ON TABLE timeline_events IS 'Unified timeline of all health-related events';

COMMENT ON COLUMN general_assessments.category IS 'Health concern category: energy, mental, sick, medication, multiple, unsure, physical';
COMMENT ON COLUMN timeline_events.event_type IS 'Specific type of health event';
COMMENT ON COLUMN timeline_events.event_category IS 'High-level category: body (3D), general, photo, or chat';
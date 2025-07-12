-- Create deep_dive_sessions table
CREATE TABLE IF NOT EXISTS deep_dive_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT,  -- Nullable for anonymous users
    body_part TEXT NOT NULL,
    form_data JSONB NOT NULL,
    model_used TEXT NOT NULL DEFAULT 'deepseek/deepseek-r1',
    
    -- Q&A tracking
    questions JSONB[] DEFAULT '{}',  -- Array of {question, answer, timestamp}
    current_step INTEGER DEFAULT 0,
    
    -- Analysis state
    internal_state JSONB,  -- Confidence scores, hypotheses
    status TEXT CHECK (status IN ('active', 'completed', 'abandoned')) DEFAULT 'active',
    last_question TEXT,  -- Store the current question for continue flow
    
    -- Results
    final_analysis JSONB,
    final_confidence INTEGER,
    reasoning_chain TEXT[],
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    tokens_used JSONB,
    
    -- Link to existing tables
    llm_summary TEXT  -- Will be saved to llm_context table
);

-- Create indexes separately
CREATE INDEX IF NOT EXISTS idx_deep_dive_user ON deep_dive_sessions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deep_dive_status ON deep_dive_sessions (status, created_at DESC);

-- Add summary_id to quick_scans for tracking
ALTER TABLE quick_scans ADD COLUMN IF NOT EXISTS summary_generated BOOLEAN DEFAULT FALSE;

-- Add RLS policies for deep_dive_sessions
ALTER TABLE deep_dive_sessions ENABLE ROW LEVEL SECURITY;

-- Policy for users to read their own deep dive sessions
CREATE POLICY "Users can read own deep dive sessions" ON deep_dive_sessions
    FOR SELECT
    USING (user_id = auth.uid()::text OR user_id IS NULL);

-- Policy for users to insert their own deep dive sessions
CREATE POLICY "Users can insert own deep dive sessions" ON deep_dive_sessions
    FOR INSERT
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

-- Policy for users to update their own deep dive sessions
CREATE POLICY "Users can update own deep dive sessions" ON deep_dive_sessions
    FOR UPDATE
    USING (user_id = auth.uid()::text OR user_id IS NULL)
    WITH CHECK (user_id = auth.uid()::text OR user_id IS NULL);

-- Grant permissions
GRANT ALL ON deep_dive_sessions TO authenticated;
GRANT ALL ON deep_dive_sessions TO anon;  -- For anonymous deep dives
GRANT ALL ON deep_dive_sessions TO service_role;

-- Add comments
COMMENT ON TABLE deep_dive_sessions IS 'Stores Deep Dive medical analysis sessions with Q&A history';
COMMENT ON COLUMN deep_dive_sessions.questions IS 'Array of question/answer pairs with timestamps';
COMMENT ON COLUMN deep_dive_sessions.internal_state IS 'Internal analysis state including confidence scores and hypotheses';
COMMENT ON COLUMN deep_dive_sessions.reasoning_chain IS 'Chain of reasoning steps for transparency';
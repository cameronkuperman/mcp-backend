-- Weekly AI Predictions Storage Tables

-- Table to store weekly generated predictions
CREATE TABLE IF NOT EXISTS weekly_ai_predictions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- Prediction data
    dashboard_alert JSONB,
    predictions JSONB NOT NULL,
    pattern_questions JSONB NOT NULL,
    body_patterns JSONB NOT NULL,
    
    -- Metadata
    generated_at TIMESTAMPTZ NOT NULL,
    generation_status TEXT NOT NULL DEFAULT 'pending' CHECK (generation_status IN ('pending', 'completed', 'failed')),
    error_message TEXT,
    data_quality_score INTEGER,
    
    -- Tracking
    viewed_at TIMESTAMPTZ,
    is_current BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_weekly_predictions_user_id ON weekly_ai_predictions(user_id);
CREATE INDEX idx_weekly_predictions_generated_at ON weekly_ai_predictions(generated_at);
CREATE INDEX idx_weekly_predictions_is_current ON weekly_ai_predictions(is_current);
CREATE INDEX idx_weekly_predictions_user_current ON weekly_ai_predictions(user_id, is_current);

-- User preferences for weekly generation
CREATE TABLE IF NOT EXISTS user_ai_preferences (
    user_id TEXT PRIMARY KEY,
    
    -- Weekly generation preferences
    weekly_generation_enabled BOOLEAN DEFAULT TRUE,
    preferred_day_of_week INTEGER DEFAULT 3 CHECK (preferred_day_of_week >= 0 AND preferred_day_of_week <= 6), -- 0=Sunday, 3=Wednesday
    preferred_hour INTEGER DEFAULT 17 CHECK (preferred_hour >= 0 AND preferred_hour <= 23), -- 17 = 5 PM
    timezone TEXT DEFAULT 'UTC',
    
    -- Initial setup
    initial_predictions_generated BOOLEAN DEFAULT FALSE,
    initial_generation_date TIMESTAMPTZ,
    
    -- Last generation tracking
    last_generation_date TIMESTAMPTZ,
    next_scheduled_generation TIMESTAMPTZ,
    generation_failure_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Function to mark old predictions as not current
CREATE OR REPLACE FUNCTION mark_old_predictions_not_current()
RETURNS TRIGGER AS $$
BEGIN
    -- When inserting a new prediction, mark all previous ones as not current
    IF NEW.generation_status = 'completed' THEN
        UPDATE weekly_ai_predictions 
        SET is_current = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = NEW.user_id 
        AND id != NEW.id
        AND is_current = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for marking old predictions
CREATE TRIGGER update_current_predictions 
AFTER INSERT OR UPDATE ON weekly_ai_predictions
FOR EACH ROW EXECUTE FUNCTION mark_old_predictions_not_current();

-- Row Level Security
ALTER TABLE weekly_ai_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_ai_preferences ENABLE ROW LEVEL SECURITY;

-- RLS Policies for weekly_ai_predictions
CREATE POLICY "Users can view their own predictions" ON weekly_ai_predictions
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage all predictions" ON weekly_ai_predictions
    FOR ALL USING (auth.role() = 'service_role');

-- RLS Policies for user_ai_preferences
CREATE POLICY "Users can view their own preferences" ON user_ai_preferences
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can update their own preferences" ON user_ai_preferences
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert their own preferences" ON user_ai_preferences
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage all preferences" ON user_ai_preferences
    FOR ALL USING (auth.role() = 'service_role');

-- Add updated_at trigger
CREATE TRIGGER update_weekly_predictions_updated_at BEFORE UPDATE
    ON weekly_ai_predictions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE
    ON user_ai_preferences FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to get users due for weekly generation
CREATE OR REPLACE FUNCTION get_users_due_for_generation()
RETURNS TABLE(user_id TEXT, preferred_hour INTEGER, timezone TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.user_id,
        p.preferred_hour,
        p.timezone
    FROM user_ai_preferences p
    WHERE 
        p.weekly_generation_enabled = TRUE
        AND p.initial_predictions_generated = TRUE
        AND EXTRACT(DOW FROM CURRENT_TIMESTAMP AT TIME ZONE p.timezone) = p.preferred_day_of_week
        AND (
            p.last_generation_date IS NULL 
            OR p.last_generation_date < CURRENT_TIMESTAMP - INTERVAL '6 days'
        );
END;
$$ LANGUAGE plpgsql;

-- Function to check if user needs initial predictions
CREATE OR REPLACE FUNCTION user_needs_initial_predictions(p_user_id TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    needs_init BOOLEAN;
BEGIN
    SELECT NOT COALESCE(initial_predictions_generated, FALSE)
    INTO needs_init
    FROM user_ai_preferences
    WHERE user_id = p_user_id;
    
    -- If no preferences exist, they need initial predictions
    IF needs_init IS NULL THEN
        RETURN TRUE;
    END IF;
    
    RETURN needs_init;
END;
$$ LANGUAGE plpgsql;
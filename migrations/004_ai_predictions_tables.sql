-- AI Predictions and Alerts Tables

-- Create table for logging AI alerts shown to users
CREATE TABLE IF NOT EXISTS ai_alerts_log (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    alert_id UUID NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    title TEXT NOT NULL,
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    generated_at TIMESTAMPTZ NOT NULL,
    viewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    dismissed BOOLEAN DEFAULT FALSE,
    action_taken TEXT,
    
    -- For analytics
    was_accurate BOOLEAN,
    user_feedback TEXT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_ai_alerts_user_id ON ai_alerts_log(user_id);
CREATE INDEX idx_ai_alerts_generated_at ON ai_alerts_log(generated_at);
CREATE INDEX idx_ai_alerts_severity ON ai_alerts_log(severity);

-- Create table for storing AI predictions (optional, for history)
CREATE TABLE IF NOT EXISTS ai_predictions_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    prediction_type TEXT NOT NULL CHECK (prediction_type IN ('immediate', 'seasonal', 'longterm')),
    prediction_data JSONB NOT NULL,
    confidence INTEGER NOT NULL CHECK (confidence >= 0 AND confidence <= 100),
    generated_at TIMESTAMPTZ NOT NULL,
    
    -- Track accuracy
    outcome_occurred BOOLEAN,
    outcome_date TIMESTAMPTZ,
    outcome_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_ai_predictions_user_id ON ai_predictions_history(user_id);
CREATE INDEX idx_ai_predictions_type ON ai_predictions_history(prediction_type);
CREATE INDEX idx_ai_predictions_generated_at ON ai_predictions_history(generated_at);

-- Row Level Security
ALTER TABLE ai_alerts_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_predictions_history ENABLE ROW LEVEL SECURITY;

-- RLS Policies for ai_alerts_log
CREATE POLICY "Users can view their own alerts" ON ai_alerts_log
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can update their own alerts" ON ai_alerts_log
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage all alerts" ON ai_alerts_log
    FOR ALL USING (auth.role() = 'service_role');

-- RLS Policies for ai_predictions_history
CREATE POLICY "Users can view their own predictions" ON ai_predictions_history
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage all predictions" ON ai_predictions_history
    FOR ALL USING (auth.role() = 'service_role');

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_ai_alerts_updated_at BEFORE UPDATE
    ON ai_alerts_log FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
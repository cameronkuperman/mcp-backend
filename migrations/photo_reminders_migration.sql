-- Photo Reminders Table Migration
-- This migration adds support for photo analysis follow-up reminders and tracking

-- Create photo_reminders table for storing reminder configurations
CREATE TABLE IF NOT EXISTS photo_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES photo_sessions(id) ON DELETE CASCADE,
    analysis_id UUID NOT NULL REFERENCES photo_analyses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    enabled BOOLEAN DEFAULT true,
    interval_days INTEGER NOT NULL DEFAULT 30,
    reminder_method TEXT NOT NULL DEFAULT 'email' CHECK (reminder_method IN ('email', 'sms', 'in_app', 'none')),
    reminder_text TEXT NOT NULL,
    contact_info JSONB,
    next_reminder_date TIMESTAMPTZ,
    ai_reasoning TEXT,
    last_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_photo_reminders_session_id ON photo_reminders(session_id);
CREATE INDEX IF NOT EXISTS idx_photo_reminders_user_id ON photo_reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_photo_reminders_next_date ON photo_reminders(next_reminder_date) WHERE enabled = true;

-- Add unique constraint to ensure only one reminder per session
CREATE UNIQUE INDEX IF NOT EXISTS idx_photo_reminders_session_unique ON photo_reminders(session_id);

-- Add columns to photo_uploads table for follow-up tracking
ALTER TABLE photo_uploads 
ADD COLUMN IF NOT EXISTS is_followup BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS followup_notes TEXT;

-- Add index for follow-up photos
CREATE INDEX IF NOT EXISTS idx_photo_uploads_followup ON photo_uploads(session_id, is_followup) WHERE is_followup = true;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_photo_reminders_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_photo_reminders_updated_at
BEFORE UPDATE ON photo_reminders
FOR EACH ROW
EXECUTE FUNCTION update_photo_reminders_updated_at();

-- Add RLS policies for photo_reminders
ALTER TABLE photo_reminders ENABLE ROW LEVEL SECURITY;

-- Users can only see and modify their own reminders
CREATE POLICY photo_reminders_user_policy ON photo_reminders
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Service role bypass RLS
CREATE POLICY photo_reminders_service_policy ON photo_reminders
    FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

-- Grant permissions
GRANT ALL ON photo_reminders TO authenticated;
GRANT ALL ON photo_reminders TO service_role;

-- Add comment for documentation
COMMENT ON TABLE photo_reminders IS 'Stores photo analysis follow-up reminder configurations for users';
COMMENT ON COLUMN photo_reminders.reminder_method IS 'Notification method: email, sms, in_app, or none';
COMMENT ON COLUMN photo_reminders.contact_info IS 'JSON object with email and/or phone fields depending on reminder_method';
COMMENT ON COLUMN photo_reminders.ai_reasoning IS 'AI-generated explanation for the suggested reminder interval';
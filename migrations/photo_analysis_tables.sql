-- Photo Analysis Tables Migration
-- Run this SQL in your Supabase SQL Editor

-- 1. Photo Sessions Table
CREATE TABLE IF NOT EXISTS photo_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  condition_name TEXT NOT NULL,
  description TEXT,
  is_sensitive BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_photo_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_photo_sessions_user_id ON photo_sessions(user_id);
CREATE INDEX idx_photo_sessions_created_at ON photo_sessions(created_at DESC);
CREATE INDEX idx_photo_sessions_deleted_at ON photo_sessions(deleted_at) WHERE deleted_at IS NULL;

-- 2. Photo Uploads Table
CREATE TABLE IF NOT EXISTS photo_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES photo_sessions(id) ON DELETE CASCADE,
  category VARCHAR(50) NOT NULL CHECK (category IN (
    'medical_normal', 'medical_sensitive', 'medical_gore', 
    'unclear', 'non_medical', 'inappropriate'
  )),
  storage_url TEXT, -- NULL for sensitive photos
  file_metadata JSONB NOT NULL DEFAULT '{}', -- size, mime_type, dimensions
  upload_metadata JSONB DEFAULT '{}', -- EXIF data, device info
  uploaded_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ -- Soft delete
);

CREATE INDEX idx_photo_uploads_session_id ON photo_uploads(session_id);
CREATE INDEX idx_photo_uploads_category ON photo_uploads(category);
CREATE INDEX idx_photo_uploads_deleted_at ON photo_uploads(deleted_at) WHERE deleted_at IS NULL;

-- 3. Photo Analyses Table  
CREATE TABLE IF NOT EXISTS photo_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES photo_sessions(id) ON DELETE CASCADE,
  photo_ids UUID[] NOT NULL, -- Array of analyzed photos
  analysis_data JSONB NOT NULL, -- Encrypted for sensitive
  model_used VARCHAR(100) NOT NULL,
  model_response JSONB, -- Raw model response for debugging
  confidence_score FLOAT,
  is_sensitive BOOLEAN DEFAULT false,
  expires_at TIMESTAMPTZ, -- For temporary analyses
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photo_analyses_session_id ON photo_analyses(session_id);
CREATE INDEX idx_photo_analyses_expires_at ON photo_analyses(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_photo_analyses_created_at ON photo_analyses(created_at DESC);

-- 4. Photo Tracking Suggestions Table
CREATE TABLE IF NOT EXISTS photo_tracking_suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES photo_sessions(id) ON DELETE CASCADE,
  analysis_id UUID REFERENCES photo_analyses(id) ON DELETE CASCADE,
  tracking_config_id UUID,
  metric_suggestions JSONB[] NOT NULL,
  auto_approved BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photo_tracking_suggestions_session_id ON photo_tracking_suggestions(session_id);
CREATE INDEX idx_photo_tracking_suggestions_analysis_id ON photo_tracking_suggestions(analysis_id);

-- 5. Photo Comparisons Table
CREATE TABLE IF NOT EXISTS photo_comparisons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES photo_sessions(id) ON DELETE CASCADE,
  before_photo_id UUID REFERENCES photo_uploads(id),
  after_photo_id UUID REFERENCES photo_uploads(id),
  comparison_data JSONB NOT NULL, -- AI-generated comparison
  days_between INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photo_comparisons_session_id ON photo_comparisons(session_id);
CREATE INDEX idx_photo_comparisons_created_at ON photo_comparisons(created_at DESC);

-- 6. Photo Tracking Configurations Table (for photo-based tracking)
CREATE TABLE IF NOT EXISTS photo_tracking_configurations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  session_id UUID REFERENCES photo_sessions(id),
  metric_name TEXT NOT NULL,
  y_axis_label TEXT NOT NULL,
  y_axis_min FLOAT DEFAULT 0,
  y_axis_max FLOAT DEFAULT 100,
  created_from VARCHAR(50) DEFAULT 'photo_analysis',
  source_id UUID, -- Reference to analysis_id
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photo_tracking_configurations_user_id ON photo_tracking_configurations(user_id);
CREATE INDEX idx_photo_tracking_configurations_session_id ON photo_tracking_configurations(session_id);

-- 7. Photo Tracking Data Table
CREATE TABLE IF NOT EXISTS photo_tracking_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  configuration_id UUID REFERENCES photo_tracking_configurations(id) ON DELETE CASCADE,
  value FLOAT NOT NULL,
  analysis_id UUID REFERENCES photo_analyses(id),
  notes TEXT,
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_photo_tracking_data_configuration_id ON photo_tracking_data(configuration_id);
CREATE INDEX idx_photo_tracking_data_recorded_at ON photo_tracking_data(recorded_at DESC);

-- RLS (Row Level Security) Policies

-- Enable RLS on all tables
ALTER TABLE photo_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_tracking_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_comparisons ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_tracking_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE photo_tracking_data ENABLE ROW LEVEL SECURITY;

-- Photo Sessions Policies
CREATE POLICY "Users can view their own photo sessions" ON photo_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own photo sessions" ON photo_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own photo sessions" ON photo_sessions
    FOR UPDATE USING (auth.uid() = user_id);

-- Photo Uploads Policies
CREATE POLICY "Users can view photo uploads from their sessions" ON photo_uploads
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_uploads.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can upload photos to their sessions" ON photo_uploads
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_uploads.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

-- Photo Analyses Policies
CREATE POLICY "Users can view analyses for their sessions" ON photo_analyses
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_analyses.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create analyses for their sessions" ON photo_analyses
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_analyses.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

-- Photo Tracking Suggestions Policies
CREATE POLICY "Users can view tracking suggestions for their sessions" ON photo_tracking_suggestions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_tracking_suggestions.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

-- Photo Comparisons Policies
CREATE POLICY "Users can view comparisons for their sessions" ON photo_comparisons
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM photo_sessions 
            WHERE photo_sessions.id = photo_comparisons.session_id 
            AND photo_sessions.user_id = auth.uid()
        )
    );

-- Photo Tracking Configurations Policies
CREATE POLICY "Users can view their own tracking configs" ON photo_tracking_configurations
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own tracking configs" ON photo_tracking_configurations
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tracking configs" ON photo_tracking_configurations
    FOR UPDATE USING (auth.uid() = user_id);

-- Photo Tracking Data Policies
CREATE POLICY "Users can view tracking data for their configs" ON photo_tracking_data
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM photo_tracking_configurations 
            WHERE photo_tracking_configurations.id = photo_tracking_data.configuration_id 
            AND photo_tracking_configurations.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can add tracking data to their configs" ON photo_tracking_data
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM photo_tracking_configurations 
            WHERE photo_tracking_configurations.id = photo_tracking_data.configuration_id 
            AND photo_tracking_configurations.user_id = auth.uid()
        )
    );

-- Functions for cleanup
CREATE OR REPLACE FUNCTION cleanup_expired_analyses()
RETURNS void AS $$
BEGIN
    UPDATE photo_analyses
    SET analysis_data = NULL,
        model_response = NULL
    WHERE expires_at < NOW()
    AND expires_at IS NOT NULL;
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a cron job to run cleanup daily
-- SELECT cron.schedule('cleanup-expired-photo-analyses', '0 2 * * *', 'SELECT cleanup_expired_analyses();');
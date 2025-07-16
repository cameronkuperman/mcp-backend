-- =====================================================
-- LONG-TERM SYMPTOM TRACKING DATABASE MIGRATION
-- Run this entire script in Supabase SQL Editor
-- =====================================================

-- Tracking Configurations Table
-- Stores user-approved tracking configurations based on AI analysis
CREATE TABLE IF NOT EXISTS tracking_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    
    -- Source data
    source_type TEXT NOT NULL CHECK (source_type IN ('quick_scan', 'deep_dive')),
    source_id UUID NOT NULL, -- References quick_scans.id or deep_dive_sessions.id
    
    -- Tracking configuration
    metric_name TEXT NOT NULL, -- User-editable name for what's being tracked
    metric_description TEXT, -- AI-generated description of what this tracks
    
    -- Axes configuration (user-editable)
    x_axis_label TEXT NOT NULL DEFAULT 'Date',
    y_axis_label TEXT NOT NULL, -- e.g., "Pain Level (1-10)", "Frequency per Day"
    y_axis_type TEXT NOT NULL CHECK (y_axis_type IN ('numeric', 'percentage', 'count', 'duration')),
    y_axis_min DECIMAL,
    y_axis_max DECIMAL,
    
    -- What to track
    tracking_type TEXT NOT NULL CHECK (tracking_type IN ('severity', 'frequency', 'duration', 'occurrence', 'composite')),
    symptom_keywords TEXT[], -- Keywords to look for in future scans
    body_parts TEXT[], -- Body parts associated with this tracking
    
    -- AI suggestions
    ai_suggested_questions TEXT[], -- Questions AI recommends asking during tracking
    ai_reasoning TEXT, -- Why AI thinks this is important to track
    confidence_score DECIMAL CHECK (confidence_score BETWEEN 0 AND 1),
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'archived')),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejected_reason TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_data_point TIMESTAMP WITH TIME ZONE,
    data_points_count INTEGER DEFAULT 0,
    
    -- Display preferences
    chart_type TEXT DEFAULT 'line' CHECK (chart_type IN ('line', 'bar', 'scatter', 'area')),
    color TEXT DEFAULT '#3B82F6', -- Hex color for the chart
    show_on_homepage BOOLEAN DEFAULT TRUE,
    display_order INTEGER DEFAULT 0
);

-- Tracking Data Points Table
-- Stores actual tracked values over time
CREATE TABLE IF NOT EXISTS tracking_data_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    configuration_id UUID NOT NULL REFERENCES tracking_configurations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    
    -- Data point
    value DECIMAL NOT NULL,
    unit TEXT, -- Optional unit (e.g., "times", "hours", "%")
    
    -- Source of this data point
    source_type TEXT CHECK (source_type IN ('manual', 'quick_scan', 'deep_dive', 'auto_extracted')),
    source_id UUID, -- References the scan/dive this came from
    
    -- Context
    notes TEXT, -- User notes about this data point
    metadata JSONB, -- Additional context (weather, activities, etc.)
    
    -- Timestamps
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(), -- When the symptom occurred
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() -- When this record was created
);

-- AI Tracking Suggestions Table
-- Stores AI-generated tracking suggestions before user approval
CREATE TABLE IF NOT EXISTS tracking_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    
    -- Source analysis
    source_type TEXT NOT NULL CHECK (source_type IN ('quick_scan', 'deep_dive', 'report')),
    source_id UUID NOT NULL,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- AI suggestions (array of suggestions)
    suggestions JSONB[] NOT NULL, -- Each contains metric_name, description, tracking_type, etc.
    
    -- Analysis metadata
    model_used TEXT NOT NULL,
    confidence_scores DECIMAL[], -- Confidence for each suggestion
    reasoning TEXT, -- Overall reasoning for suggestions
    
    -- User interaction
    viewed_at TIMESTAMP WITH TIME ZONE,
    actioned_at TIMESTAMP WITH TIME ZONE,
    action_taken TEXT CHECK (action_taken IN ('approved_all', 'approved_some', 'rejected_all', 'expired')),
    
    -- Expiration
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tracking Insights Table
-- Stores AI-generated insights about tracked data
CREATE TABLE IF NOT EXISTS tracking_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    configuration_id UUID NOT NULL REFERENCES tracking_configurations(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    
    -- Insight details
    insight_type TEXT NOT NULL CHECK (insight_type IN ('trend', 'correlation', 'anomaly', 'milestone', 'pattern')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- Analysis period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    data_points_analyzed INTEGER,
    
    -- Significance
    significance_score DECIMAL CHECK (significance_score BETWEEN 0 AND 1),
    confidence_level DECIMAL CHECK (confidence_level BETWEEN 0 AND 1),
    
    -- Recommendations
    recommendations TEXT[],
    action_items JSONB[],
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_tracking_configs_user ON tracking_configurations (user_id, status, created_at DESC);
CREATE INDEX idx_tracking_configs_source ON tracking_configurations (source_type, source_id);
CREATE INDEX idx_tracking_configs_homepage ON tracking_configurations (user_id, show_on_homepage, display_order) WHERE status = 'approved';

CREATE INDEX idx_tracking_data_user ON tracking_data_points (user_id, recorded_at DESC);
CREATE INDEX idx_tracking_data_config ON tracking_data_points (configuration_id, recorded_at DESC);
CREATE INDEX idx_tracking_data_source ON tracking_data_points (source_type, source_id) WHERE source_id IS NOT NULL;

CREATE INDEX idx_suggestions_user ON tracking_suggestions (user_id, created_at DESC);
CREATE INDEX idx_suggestions_source ON tracking_suggestions (source_type, source_id);
-- Note: Removed idx_suggestions_active because NOW() is not immutable
-- Instead, create a simpler index without the expires_at condition
CREATE INDEX idx_suggestions_unactioned ON tracking_suggestions (user_id, viewed_at) WHERE actioned_at IS NULL;

CREATE INDEX idx_insights_user ON tracking_insights (user_id, created_at DESC);
CREATE INDEX idx_insights_config ON tracking_insights (configuration_id, created_at DESC);
CREATE INDEX idx_insights_unread ON tracking_insights (user_id, is_read) WHERE is_read = FALSE AND is_dismissed = FALSE;

-- Enable RLS
ALTER TABLE tracking_configurations ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking_data_points ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tracking_insights ENABLE ROW LEVEL SECURITY;

-- RLS Policies for tracking_configurations
CREATE POLICY "Users can manage own tracking configs" ON tracking_configurations
    FOR ALL
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- RLS Policies for tracking_data_points
CREATE POLICY "Users can manage own tracking data" ON tracking_data_points
    FOR ALL
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- RLS Policies for tracking_suggestions
CREATE POLICY "Users can view own tracking suggestions" ON tracking_suggestions
    FOR ALL
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- RLS Policies for tracking_insights
CREATE POLICY "Users can view own tracking insights" ON tracking_insights
    FOR ALL
    USING (user_id = auth.uid()::text)
    WITH CHECK (user_id = auth.uid()::text);

-- Grant permissions
GRANT ALL ON tracking_configurations TO authenticated;
GRANT ALL ON tracking_data_points TO authenticated;
GRANT ALL ON tracking_suggestions TO authenticated;
GRANT ALL ON tracking_insights TO authenticated;

-- Helper function to get active tracking configurations for homepage
CREATE OR REPLACE FUNCTION get_homepage_tracking_configs(p_user_id TEXT)
RETURNS TABLE (
    id UUID,
    metric_name TEXT,
    y_axis_label TEXT,
    chart_type TEXT,
    color TEXT,
    latest_value DECIMAL,
    latest_date TIMESTAMP WITH TIME ZONE,
    trend TEXT,
    data_points_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tc.id,
        tc.metric_name,
        tc.y_axis_label,
        tc.chart_type,
        tc.color,
        tdp.latest_value,
        tdp.latest_date,
        CASE 
            WHEN tdp.trend_direction > 0 THEN 'increasing'
            WHEN tdp.trend_direction < 0 THEN 'decreasing'
            ELSE 'stable'
        END as trend,
        tc.data_points_count
    FROM tracking_configurations tc
    LEFT JOIN LATERAL (
        SELECT 
            value as latest_value,
            recorded_at as latest_date,
            value - LAG(value) OVER (ORDER BY recorded_at) as trend_direction
        FROM tracking_data_points
        WHERE configuration_id = tc.id
        ORDER BY recorded_at DESC
        LIMIT 1
    ) tdp ON true
    WHERE tc.user_id = p_user_id
    AND tc.status = 'approved'
    AND tc.show_on_homepage = TRUE
    ORDER BY tc.display_order, tc.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE tracking_configurations IS 'User-approved configurations for long-term symptom tracking';
COMMENT ON TABLE tracking_data_points IS 'Time-series data points for tracked symptoms';
COMMENT ON TABLE tracking_suggestions IS 'AI-generated suggestions for what symptoms to track';
COMMENT ON TABLE tracking_insights IS 'AI-generated insights from tracked symptom data';
COMMENT ON COLUMN tracking_configurations.metric_name IS 'User-editable name for the tracked metric';
COMMENT ON COLUMN tracking_configurations.tracking_type IS 'Type of tracking: severity (1-10 scale), frequency (times per period), duration (time length), occurrence (yes/no), composite (multiple factors)';
COMMENT ON COLUMN tracking_data_points.source_type IS 'How this data point was created: manual entry, extracted from scan/dive, or auto-extracted';
COMMENT ON COLUMN tracking_insights.insight_type IS 'Type of insight: trend (direction change), correlation (between symptoms), anomaly (unusual value), milestone (achievement), pattern (recurring behavior)';

-- =====================================================
-- VERIFICATION QUERIES - Run these to verify setup
-- =====================================================

-- Check all tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('tracking_configurations', 'tracking_data_points', 'tracking_suggestions', 'tracking_insights');

-- Check RLS is enabled
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('tracking_configurations', 'tracking_data_points', 'tracking_suggestions', 'tracking_insights');

-- Check indexes were created
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 'public' 
AND tablename IN ('tracking_configurations', 'tracking_data_points', 'tracking_suggestions', 'tracking_insights');

-- =====================================================
-- SUCCESS MESSAGE
-- =====================================================
-- If all tables show up in the verification queries above,
-- your tracking system is ready to use!
-- 
-- Next steps:
-- 1. Deploy the updated run_oracle.py to Railway
-- 2. Integrate the frontend using TRACKING_INTEGRATION_GUIDE.md
-- 3. Test with a Quick Scan or Deep Dive
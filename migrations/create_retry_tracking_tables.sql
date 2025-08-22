-- Enhanced retry tracking and dead letter queue tables for production-ready job system
-- Run this migration to add comprehensive retry tracking

-- 1. Job retry queue for tracking retry attempts
CREATE TABLE IF NOT EXISTS job_retry_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    user_id UUID,
    operation_key VARCHAR(255) NOT NULL,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 5,
    last_error TEXT,
    last_error_code INT,
    error_classification VARCHAR(50), -- 'retryable', 'permanent', 'unknown'
    next_retry_at TIMESTAMP WITH TIME ZONE,
    retry_strategy VARCHAR(20) DEFAULT 'exponential', -- 'exponential', 'linear', 'fibonacci', 'aggressive'
    circuit_breaker_state VARCHAR(20) DEFAULT 'closed', -- 'closed', 'open', 'half_open'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(job_name, user_id, operation_key)
);

-- Indexes for efficient querying
CREATE INDEX idx_retry_queue_next_retry ON job_retry_queue(next_retry_at) WHERE next_retry_at IS NOT NULL;
CREATE INDEX idx_retry_queue_job_user ON job_retry_queue(job_name, user_id);
CREATE INDEX idx_retry_queue_circuit_state ON job_retry_queue(circuit_breaker_state) WHERE circuit_breaker_state != 'closed';
CREATE INDEX idx_retry_queue_created ON job_retry_queue(created_at DESC);

-- 2. Dead letter queue for permanently failed jobs
CREATE TABLE IF NOT EXISTS job_dead_letter_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    user_id UUID,
    operation_key VARCHAR(255) NOT NULL,
    error_message TEXT NOT NULL,
    error_type VARCHAR(100),
    error_classification VARCHAR(50),
    retry_count INT,
    retry_history JSONB, -- Full history of retry attempts
    original_payload JSONB, -- Original job payload for manual retry
    failure_reason VARCHAR(255), -- 'max_retries', 'permanent_error', 'circuit_breaker', etc.
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for dead letter queue
CREATE INDEX idx_dlq_unresolved ON job_dead_letter_queue(created_at DESC) WHERE resolved = FALSE;
CREATE INDEX idx_dlq_job_name ON job_dead_letter_queue(job_name, created_at DESC);
CREATE INDEX idx_dlq_user ON job_dead_letter_queue(user_id) WHERE user_id IS NOT NULL;
CREATE INDEX idx_dlq_failure_reason ON job_dead_letter_queue(failure_reason);

-- 3. Circuit breaker state tracking
CREATE TABLE IF NOT EXISTS circuit_breaker_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    breaker_key VARCHAR(255) UNIQUE NOT NULL, -- Unique identifier for the circuit
    state VARCHAR(20) NOT NULL DEFAULT 'closed', -- 'closed', 'open', 'half_open'
    failure_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    consecutive_failures INT DEFAULT 0,
    last_failure_time TIMESTAMP WITH TIME ZONE,
    last_success_time TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    half_open_at TIMESTAMP WITH TIME ZONE,
    failure_threshold INT DEFAULT 5,
    success_threshold INT DEFAULT 2,
    timeout_minutes INT DEFAULT 5,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for active circuit breakers
CREATE INDEX idx_circuit_breaker_active ON circuit_breaker_state(state) WHERE state != 'closed';
CREATE INDEX idx_circuit_breaker_timeout ON circuit_breaker_state(opened_at) WHERE state = 'open';

-- 4. Retry metrics for monitoring
CREATE TABLE IF NOT EXISTS job_retry_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name VARCHAR(100) NOT NULL,
    operation_key VARCHAR(255),
    user_id UUID,
    total_attempts INT DEFAULT 0,
    successful_attempts INT DEFAULT 0,
    failed_attempts INT DEFAULT 0,
    avg_retry_count FLOAT,
    max_retry_count INT,
    avg_duration_seconds FLOAT,
    error_types JSONB DEFAULT '[]', -- Array of encountered error types
    retry_strategies_used JSONB DEFAULT '[]', -- Array of strategies used
    circuit_breaker_trips INT DEFAULT 0,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    hour INT NOT NULL DEFAULT EXTRACT(HOUR FROM NOW()),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(job_name, operation_key, date, hour)
);

-- Indexes for metrics queries
CREATE INDEX idx_retry_metrics_job_date ON job_retry_metrics(job_name, date DESC);
CREATE INDEX idx_retry_metrics_hourly ON job_retry_metrics(date, hour);
CREATE INDEX idx_retry_metrics_user ON job_retry_metrics(user_id) WHERE user_id IS NOT NULL;

-- 5. Alert configuration for monitoring
CREATE TABLE IF NOT EXISTS job_alert_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_name VARCHAR(100) UNIQUE NOT NULL,
    alert_type VARCHAR(50) NOT NULL, -- 'failure_rate', 'dlq_size', 'circuit_breaker', 'retry_rate'
    threshold_value FLOAT NOT NULL,
    threshold_period_minutes INT DEFAULT 60,
    enabled BOOLEAN DEFAULT TRUE,
    notification_channels JSONB DEFAULT '[]', -- ['email', 'slack', 'pagerduty']
    notification_recipients JSONB DEFAULT '[]',
    cooldown_minutes INT DEFAULT 30, -- Prevent alert spam
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    trigger_count INT DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Alert history for tracking
CREATE TABLE IF NOT EXISTS job_alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_config_id UUID REFERENCES job_alert_config(id) ON DELETE CASCADE,
    alert_name VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    triggered_value FLOAT,
    threshold_value FLOAT,
    severity VARCHAR(20) DEFAULT 'warning', -- 'info', 'warning', 'error', 'critical'
    message TEXT,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channels JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for recent alerts
CREATE INDEX idx_alert_history_recent ON job_alert_history(created_at DESC);
CREATE INDEX idx_alert_history_unacked ON job_alert_history(created_at DESC) WHERE acknowledged = FALSE;

-- Helper functions
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers for updated_at
CREATE TRIGGER update_job_retry_queue_updated_at BEFORE UPDATE ON job_retry_queue
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_circuit_breaker_state_updated_at BEFORE UPDATE ON circuit_breaker_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_job_retry_metrics_updated_at BEFORE UPDATE ON job_retry_metrics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_job_alert_config_updated_at BEFORE UPDATE ON job_alert_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Monitoring views
CREATE OR REPLACE VIEW job_health_dashboard AS
SELECT 
    jel.job_name,
    COUNT(DISTINCT jel.id) as total_executions_24h,
    COUNT(DISTINCT CASE WHEN jel.status = 'completed' THEN jel.id END) as successful_24h,
    COUNT(DISTINCT CASE WHEN jel.status = 'failed' THEN jel.id END) as failed_24h,
    ROUND(AVG(jel.duration_seconds)::numeric, 2) as avg_duration_seconds,
    COUNT(DISTINCT jrq.id) as active_retries,
    COUNT(DISTINCT jdlq.id) as dead_letter_items,
    COUNT(DISTINCT CASE WHEN cbs.state != 'closed' THEN cbs.id END) as open_circuit_breakers,
    MAX(jel.executed_at) as last_execution
FROM job_execution_log jel
LEFT JOIN job_retry_queue jrq ON jrq.job_name = jel.job_name
LEFT JOIN job_dead_letter_queue jdlq ON jdlq.job_name = jel.job_name AND jdlq.resolved = FALSE
LEFT JOIN circuit_breaker_state cbs ON cbs.breaker_key LIKE jel.job_name || '%'
WHERE jel.executed_at > NOW() - INTERVAL '24 hours'
GROUP BY jel.job_name;

-- Retry effectiveness view
CREATE OR REPLACE VIEW retry_effectiveness AS
SELECT 
    job_name,
    DATE(created_at) as date,
    COUNT(*) as total_retries,
    AVG(retry_count) as avg_retry_count,
    MAX(retry_count) as max_retry_count,
    COUNT(CASE WHEN retry_count >= max_retries THEN 1 END) as max_retries_reached,
    COUNT(DISTINCT user_id) as unique_users_affected,
    ARRAY_AGG(DISTINCT error_classification) as error_types
FROM job_retry_queue
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY job_name, DATE(created_at)
ORDER BY date DESC, job_name;

-- Dead letter queue summary
CREATE OR REPLACE VIEW dlq_summary AS
SELECT 
    job_name,
    failure_reason,
    COUNT(*) as count,
    MIN(created_at) as oldest_item,
    MAX(created_at) as newest_item,
    COUNT(CASE WHEN resolved = FALSE THEN 1 END) as unresolved_count,
    ARRAY_AGG(DISTINCT error_classification) as error_classifications
FROM job_dead_letter_queue
GROUP BY job_name, failure_reason
ORDER BY unresolved_count DESC, count DESC;

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON job_retry_queue TO authenticated;
GRANT SELECT, INSERT ON job_dead_letter_queue TO authenticated;
GRANT SELECT, UPDATE ON job_dead_letter_queue TO service_role; -- For resolution
GRANT SELECT, INSERT, UPDATE ON circuit_breaker_state TO service_role;
GRANT SELECT, INSERT, UPDATE ON job_retry_metrics TO service_role;
GRANT SELECT ON job_health_dashboard TO authenticated;
GRANT SELECT ON retry_effectiveness TO authenticated;
GRANT SELECT ON dlq_summary TO authenticated;

-- Row Level Security (if needed)
ALTER TABLE job_retry_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_dead_letter_queue ENABLE ROW LEVEL SECURITY;

-- Policy for users to see their own retry data
CREATE POLICY "Users can view their own retry data" ON job_retry_queue
    FOR SELECT USING (user_id = auth.uid() OR auth.uid() IN (
        SELECT id FROM profiles WHERE role = 'admin'
    ));

CREATE POLICY "Users can view their own dead letter items" ON job_dead_letter_queue
    FOR SELECT USING (user_id = auth.uid() OR auth.uid() IN (
        SELECT id FROM profiles WHERE role = 'admin'
    ));

-- Comments for documentation
COMMENT ON TABLE job_retry_queue IS 'Tracks retry attempts for failed jobs with exponential backoff';
COMMENT ON TABLE job_dead_letter_queue IS 'Stores permanently failed jobs for manual review and recovery';
COMMENT ON TABLE circuit_breaker_state IS 'Manages circuit breaker state to prevent cascading failures';
COMMENT ON TABLE job_retry_metrics IS 'Aggregated metrics for monitoring retry patterns and effectiveness';
COMMENT ON TABLE job_alert_config IS 'Configuration for automated alerts on job failures';
COMMENT ON TABLE job_alert_history IS 'History of triggered alerts for audit and analysis';
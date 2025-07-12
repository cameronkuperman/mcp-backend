-- Example queries for Quick Scan feature

-- Query to get symptom history for line graph (last 30 days)
-- Usage: Replace $1 with user_id and $2 with symptom_name
/*
SELECT
    occurrence_date,
    severity,
    symptom_name,
    body_part
FROM symptom_tracking
WHERE user_id = $1
    AND symptom_name = $2
    AND occurrence_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY occurrence_date ASC;
*/

-- Query to get all user's tracked symptoms with summary
-- Usage: Replace $1 with user_id
/*
SELECT DISTINCT
    symptom_name,
    body_part,
    COUNT(*) as occurrence_count,
    MAX(occurrence_date) as last_occurrence,
    AVG(severity)::numeric(3,1) as avg_severity,
    MAX(severity) as max_severity
FROM symptom_tracking
WHERE user_id = $1
GROUP BY symptom_name, body_part
ORDER BY last_occurrence DESC;
*/

-- Query to get recent quick scans for a user
-- Usage: Replace $1 with user_id
/*
SELECT 
    id,
    body_part,
    confidence_score,
    urgency_level,
    created_at,
    analysis_result->>'primaryCondition' as primary_condition,
    escalated_to_oracle
FROM quick_scans
WHERE user_id = $1
ORDER BY created_at DESC
LIMIT 10;
*/

-- Query to find similar symptoms across users (for analytics)
-- Usage: Replace $1 with body_part and $2 with confidence threshold
/*
SELECT 
    body_part,
    analysis_result->>'primaryCondition' as condition,
    COUNT(*) as occurrence_count,
    AVG(confidence_score) as avg_confidence
FROM quick_scans
WHERE body_part = $1
    AND confidence_score >= $2
GROUP BY body_part, analysis_result->>'primaryCondition'
ORDER BY occurrence_count DESC
LIMIT 10;
*/

-- Function to get symptom trend (increasing/decreasing/stable)
CREATE OR REPLACE FUNCTION get_symptom_trend(
    p_user_id TEXT,
    p_symptom_name TEXT,
    p_days INTEGER DEFAULT 7
) RETURNS TABLE (
    trend TEXT,
    avg_severity_recent NUMERIC,
    avg_severity_previous NUMERIC,
    change_percentage NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH recent_period AS (
        SELECT AVG(severity)::NUMERIC as avg_severity
        FROM symptom_tracking
        WHERE user_id = p_user_id
            AND symptom_name = p_symptom_name
            AND occurrence_date >= CURRENT_DATE - INTERVAL '1 day' * p_days
    ),
    previous_period AS (
        SELECT AVG(severity)::NUMERIC as avg_severity
        FROM symptom_tracking
        WHERE user_id = p_user_id
            AND symptom_name = p_symptom_name
            AND occurrence_date >= CURRENT_DATE - INTERVAL '1 day' * (p_days * 2)
            AND occurrence_date < CURRENT_DATE - INTERVAL '1 day' * p_days
    )
    SELECT 
        CASE 
            WHEN r.avg_severity IS NULL OR p.avg_severity IS NULL THEN 'insufficient_data'
            WHEN r.avg_severity > p.avg_severity * 1.1 THEN 'increasing'
            WHEN r.avg_severity < p.avg_severity * 0.9 THEN 'decreasing'
            ELSE 'stable'
        END as trend,
        COALESCE(r.avg_severity, 0) as avg_severity_recent,
        COALESCE(p.avg_severity, 0) as avg_severity_previous,
        CASE 
            WHEN p.avg_severity > 0 THEN 
                ROUND(((r.avg_severity - p.avg_severity) / p.avg_severity * 100)::NUMERIC, 1)
            ELSE 0
        END as change_percentage
    FROM recent_period r, previous_period p;
END;
$$ LANGUAGE plpgsql;

-- Function to get user's health summary
CREATE OR REPLACE FUNCTION get_user_health_summary(p_user_id TEXT)
RETURNS TABLE (
    total_scans INTEGER,
    unique_body_parts INTEGER,
    most_scanned_part TEXT,
    avg_confidence NUMERIC,
    high_urgency_count INTEGER,
    symptoms_tracked INTEGER,
    last_scan_date TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(DISTINCT qs.id)::INTEGER as total_scans,
        COUNT(DISTINCT qs.body_part)::INTEGER as unique_body_parts,
        MODE() WITHIN GROUP (ORDER BY qs.body_part) as most_scanned_part,
        AVG(qs.confidence_score)::NUMERIC(4,1) as avg_confidence,
        COUNT(CASE WHEN qs.urgency_level = 'high' THEN 1 END)::INTEGER as high_urgency_count,
        COUNT(DISTINCT st.symptom_name)::INTEGER as symptoms_tracked,
        MAX(qs.created_at) as last_scan_date
    FROM quick_scans qs
    LEFT JOIN symptom_tracking st ON st.user_id = qs.user_id
    WHERE qs.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;
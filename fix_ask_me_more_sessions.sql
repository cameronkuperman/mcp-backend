-- Fix Ask Me More Sessions Missing Data
-- Run these in Supabase SQL Editor

-- 1. Check the problematic session
SELECT 
    id,
    status,
    questions IS NOT NULL as has_questions,
    jsonb_array_length(COALESCE(questions, '[]'::jsonb)) as question_count,
    form_data IS NOT NULL as has_form_data,
    body_part,
    final_analysis IS NOT NULL as has_analysis,
    initial_questions_count,
    final_confidence,
    created_at
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';

-- 2. Check all analysis_ready sessions for missing data
SELECT 
    id,
    status,
    questions IS NOT NULL as has_questions,
    form_data IS NOT NULL as has_form_data,
    body_part IS NOT NULL as has_body_part,
    initial_questions_count,
    created_at
FROM deep_dive_sessions
WHERE status = 'analysis_ready'
ORDER BY created_at DESC
LIMIT 10;

-- 3. Fix sessions missing questions array
UPDATE deep_dive_sessions
SET questions = COALESCE(questions, '[]'::jsonb)
WHERE status IN ('analysis_ready', 'completed') 
AND questions IS NULL;

-- 4. Fix sessions missing form_data
UPDATE deep_dive_sessions
SET form_data = COALESCE(form_data, '{"symptoms": "Unknown"}'::jsonb)
WHERE status IN ('analysis_ready', 'completed') 
AND form_data IS NULL;

-- 5. Fix sessions missing initial_questions_count
UPDATE deep_dive_sessions
SET initial_questions_count = 
    CASE 
        WHEN questions IS NOT NULL THEN jsonb_array_length(questions)
        ELSE 6  -- Default to 6 if no questions array
    END
WHERE status IN ('analysis_ready', 'completed') 
AND initial_questions_count IS NULL;

-- 6. Initialize additional_questions array for Ask Me More
UPDATE deep_dive_sessions
SET additional_questions = COALESCE(additional_questions, '[]'::jsonb)
WHERE status = 'analysis_ready' 
AND additional_questions IS NULL;

-- 7. Verify the fix for specific session
SELECT 
    id,
    status,
    questions,
    initial_questions_count,
    form_data,
    body_part,
    additional_questions
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';

-- 8. Optional: See what columns exist in the table
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'deep_dive_sessions'
ORDER BY ordinal_position;
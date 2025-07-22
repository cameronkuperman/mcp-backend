-- STEP 1: Check what column types you have
SELECT 
    column_name, 
    data_type,
    udt_name,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'deep_dive_sessions'
ORDER BY ordinal_position;

-- STEP 2: Check your specific broken session
SELECT 
    id,
    status,
    questions IS NOT NULL as has_questions,
    CASE 
        WHEN questions IS NULL THEN 'NULL'
        WHEN array_length(questions, 1) IS NULL THEN 'EMPTY_ARRAY'
        ELSE concat('HAS_', array_length(questions, 1)::text, '_QUESTIONS')
    END as questions_status,
    form_data IS NOT NULL as has_form_data,
    body_part,
    initial_questions_count,
    final_confidence
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';

-- STEP 3: Try to see what's in questions column (if not NULL)
SELECT 
    id,
    questions
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';

-- STEP 4: Check recent sessions to see pattern
SELECT 
    id,
    status,
    created_at,
    CASE 
        WHEN questions IS NULL THEN 'NULL'
        WHEN array_length(questions, 1) IS NULL THEN 'EMPTY'
        ELSE array_length(questions, 1)::text
    END as question_count
FROM deep_dive_sessions
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 10;
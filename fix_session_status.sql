-- Fix Session Status for Ask Me More

-- 1. Check the problematic session
SELECT id, status, questions, initial_questions_count, final_confidence 
FROM deep_dive_sessions 
WHERE id = 'cb6cd1f0-44f0-4177-83e9-28ba7de14145';

-- 2. Check all sessions that might be stuck in 'active' but have questions
SELECT 
    id,
    status,
    array_length(questions, 1) as question_count,
    initial_questions_count,
    final_confidence,
    created_at
FROM deep_dive_sessions
WHERE status = 'active' 
AND questions IS NOT NULL 
AND array_length(questions, 1) > 0
ORDER BY created_at DESC;

-- 3. FIX: Update sessions that have questions but wrong status
UPDATE deep_dive_sessions
SET 
    status = 'analysis_ready',
    initial_questions_count = CASE 
        WHEN initial_questions_count IS NULL THEN array_length(questions, 1)
        ELSE initial_questions_count
    END
WHERE status = 'active'
AND questions IS NOT NULL
AND array_length(questions, 1) >= 1  -- Has at least 1 question
AND id = 'cb6cd1f0-44f0-4177-83e9-28ba7de14145';  -- Your specific session

-- 4. Or fix ALL sessions with this issue (be careful!)
-- UPDATE deep_dive_sessions
-- SET 
--     status = 'analysis_ready',
--     initial_questions_count = COALESCE(initial_questions_count, array_length(questions, 1))
-- WHERE status = 'active'
-- AND questions IS NOT NULL
-- AND array_length(questions, 1) >= 3;  -- Has several questions

-- 5. Verify the fix
SELECT id, status, array_length(questions, 1) as questions
FROM deep_dive_sessions 
WHERE id = 'cb6cd1f0-44f0-4177-83e9-28ba7de14145';
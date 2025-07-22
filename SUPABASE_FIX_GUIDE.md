# Supabase Fix Guide for Ask Me More

## Step 1: Check Your Session Structure

First, let's see what type of columns you have:

```sql
-- Check column types
SELECT 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'deep_dive_sessions'
AND column_name IN ('questions', 'form_data', 'additional_questions', 'final_analysis')
ORDER BY ordinal_position;
```

## Step 2: Check the Broken Session

Since `questions` is `jsonb[]` (PostgreSQL array), use this query:

```sql
-- Check specific session
SELECT 
    id,
    status,
    questions IS NOT NULL as has_questions,
    array_length(questions, 1) as question_count,  -- For arrays use array_length
    form_data IS NOT NULL as has_form_data,
    body_part,
    final_analysis IS NOT NULL as has_analysis,
    initial_questions_count,
    final_confidence,
    created_at
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';
```

## Step 3: Check All Analysis Ready Sessions

```sql
-- Check all analysis_ready sessions
SELECT 
    id,
    status,
    questions IS NOT NULL as has_questions,
    array_length(questions, 1) as question_count,
    form_data IS NOT NULL as has_form_data,
    body_part,
    initial_questions_count,
    created_at
FROM deep_dive_sessions
WHERE status = 'analysis_ready'
ORDER BY created_at DESC
LIMIT 10;
```

## Step 4: Fix Missing Data (if possible)

### Fix Missing Questions Array:
```sql
-- For jsonb[] type, initialize with empty array
UPDATE deep_dive_sessions
SET questions = ARRAY[]::jsonb[]
WHERE status IN ('analysis_ready', 'completed') 
AND questions IS NULL;
```

### Fix Missing form_data:
```sql
-- form_data is regular jsonb
UPDATE deep_dive_sessions
SET form_data = '{"symptoms": "Unknown"}'::jsonb
WHERE status IN ('analysis_ready', 'completed') 
AND form_data IS NULL;
```

### Fix Missing initial_questions_count:
```sql
-- Set based on array length or default to 6
UPDATE deep_dive_sessions
SET initial_questions_count = 
    CASE 
        WHEN questions IS NOT NULL AND array_length(questions, 1) > 0 
        THEN array_length(questions, 1)
        ELSE 6
    END
WHERE status IN ('analysis_ready', 'completed') 
AND initial_questions_count IS NULL;
```

### Fix Missing additional_questions:
```sql
-- Check type first
SELECT data_type, udt_name 
FROM information_schema.columns 
WHERE table_name = 'deep_dive_sessions' 
AND column_name = 'additional_questions';

-- If it's jsonb:
UPDATE deep_dive_sessions
SET additional_questions = '[]'::jsonb
WHERE status = 'analysis_ready' 
AND additional_questions IS NULL;

-- If it's jsonb[]:
UPDATE deep_dive_sessions
SET additional_questions = ARRAY[]::jsonb[]
WHERE status = 'analysis_ready' 
AND additional_questions IS NULL;
```

## Step 5: Verify the Fix

```sql
-- Check if session is fixed
SELECT 
    id,
    status,
    questions,
    array_length(questions, 1) as question_count,
    initial_questions_count,
    form_data,
    body_part
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';
```

## Important Notes:

### If Questions Array is Empty:
If the session shows `questions = {}` (empty), then the Q&A data was lost. You'll need to:
1. Complete a new Deep Dive session
2. The new session will properly save questions
3. Ask Me More will work on the new session

### Why This Happened:
The backend was updating sessions to `analysis_ready` without preserving the questions array. This is now fixed in the code.

### For Future Sessions:
After deploying the backend fix, all new Deep Dive sessions will:
- Preserve the questions array
- Save initial_questions_count
- Work properly with Ask Me More

## Quick Check Query:
```sql
-- See what data exists in your session
SELECT 
    id,
    status,
    CASE 
        WHEN questions IS NULL THEN 'NULL'
        WHEN array_length(questions, 1) = 0 THEN 'EMPTY'
        ELSE 'HAS_DATA'
    END as questions_status,
    array_length(questions, 1) as count
FROM deep_dive_sessions
WHERE id = '96099af5-35bf-451f-9733-9c728c642802';
```

If it shows NULL or EMPTY, the session can't be recovered - you need a new Deep Dive.
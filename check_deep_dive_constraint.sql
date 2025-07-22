-- Check current constraint on deep_dive_sessions status column
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM 
    pg_constraint
WHERE 
    conrelid = 'deep_dive_sessions'::regclass
    AND contype = 'c'
    AND conname LIKE '%status%';

-- If the constraint doesn't include 'analysis_ready', run this:
-- ALTER TABLE public.deep_dive_sessions 
-- DROP CONSTRAINT IF EXISTS deep_dive_sessions_status_check;

-- ALTER TABLE public.deep_dive_sessions
-- ADD CONSTRAINT deep_dive_sessions_status_check 
-- CHECK (status = ANY (ARRAY['active'::text, 'analysis_ready'::text, 'completed'::text, 'abandoned'::text]));
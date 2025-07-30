-- Alternative approach: Create a helper function to handle user_id conversion
-- This avoids changing column types which RLS policies prevent

-- Create a function to safely convert text to UUID
CREATE OR REPLACE FUNCTION safe_text_to_uuid(input_text TEXT)
RETURNS UUID AS $$
BEGIN
    -- Try to cast to UUID
    RETURN input_text::UUID;
EXCEPTION WHEN OTHERS THEN
    -- If it fails, check if it's already a valid UUID format
    IF input_text ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
        RETURN input_text::UUID;
    ELSE
        -- Return a deterministic UUID based on the text (for non-UUID user IDs)
        RETURN uuid_generate_v5('6ba7b810-9dad-11d1-80b4-00c04fd430c8'::uuid, input_text);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Test the function
SELECT 
    safe_text_to_uuid('550e8400-e29b-41d4-a716-446655440000') as valid_uuid,
    safe_text_to_uuid('some_text_user_id') as text_to_uuid;
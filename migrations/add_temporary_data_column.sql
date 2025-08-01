-- Migration: Add temporary_data column to photo_uploads table
-- This column stores base64 image data temporarily for sensitive photos
-- Data is automatically cleaned up after 24 hours

-- Add the temporary_data column
ALTER TABLE photo_uploads 
ADD COLUMN IF NOT EXISTS temporary_data TEXT;

-- Add index for cleanup queries
CREATE INDEX IF NOT EXISTS idx_photo_uploads_temporary_data 
ON photo_uploads(uploaded_at) 
WHERE temporary_data IS NOT NULL;

-- Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_temporary_photo_data()
RETURNS void AS $$
BEGIN
    -- Clear temporary data older than 24 hours
    UPDATE photo_uploads
    SET temporary_data = NULL
    WHERE temporary_data IS NOT NULL
    AND uploaded_at < NOW() - INTERVAL '24 hours';
    
    -- Log cleanup activity
    RAISE NOTICE 'Cleaned up temporary photo data older than 24 hours';
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a scheduled job to run cleanup daily
-- Uncomment the following line if you have pg_cron extension enabled:
-- SELECT cron.schedule('cleanup-temporary-photo-data', '0 3 * * *', 'SELECT cleanup_temporary_photo_data();');

-- Grant necessary permissions
GRANT EXECUTE ON FUNCTION cleanup_temporary_photo_data() TO service_role;

-- Success message
DO $$ 
BEGIN 
    RAISE NOTICE 'Successfully added temporary_data column to photo_uploads table';
END $$;
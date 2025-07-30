-- Fix weekly_ai_predictions to allow nullable fields during generation

-- Make prediction fields nullable (they will be null when status is 'pending')
ALTER TABLE weekly_ai_predictions 
    ALTER COLUMN predictions DROP NOT NULL,
    ALTER COLUMN pattern_questions DROP NOT NULL,
    ALTER COLUMN body_patterns DROP NOT NULL;

-- Add constraint to ensure they're not null when completed
ALTER TABLE weekly_ai_predictions 
    ADD CONSTRAINT predictions_not_null_when_completed 
    CHECK (
        generation_status != 'completed' OR 
        (predictions IS NOT NULL AND pattern_questions IS NOT NULL AND body_patterns IS NOT NULL)
    );

-- Add default empty JSON values for initial insert
ALTER TABLE weekly_ai_predictions 
    ALTER COLUMN predictions SET DEFAULT '[]'::jsonb,
    ALTER COLUMN pattern_questions SET DEFAULT '[]'::jsonb,
    ALTER COLUMN body_patterns SET DEFAULT '{}'::jsonb;
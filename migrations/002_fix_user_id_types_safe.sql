-- Migration: Fix user_id data type inconsistency (SAFE VERSION)
-- Date: 2025-01-30
-- Description: Safely converts user_id from UUID to TEXT only where needed

-- Check and fix each table individually
DO $$
BEGIN
    -- Fix health_insights if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'health_insights' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.health_insights 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted health_insights.user_id to TEXT';
    END IF;

    -- Fix health_predictions if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'health_predictions' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.health_predictions 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted health_predictions.user_id to TEXT';
    END IF;

    -- Fix shadow_patterns if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'shadow_patterns' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.shadow_patterns 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted shadow_patterns.user_id to TEXT';
    END IF;

    -- Fix analysis_generation_log if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'analysis_generation_log' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.analysis_generation_log 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted analysis_generation_log.user_id to TEXT';
    END IF;

    -- Fix user_refresh_limits if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'user_refresh_limits' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.user_refresh_limits 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted user_refresh_limits.user_id to TEXT';
    END IF;

    -- Fix export_history if needed
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'public' 
        AND table_name = 'export_history' 
        AND column_name = 'user_id' 
        AND data_type = 'uuid'
    ) THEN
        ALTER TABLE public.export_history 
        ALTER COLUMN user_id TYPE TEXT USING user_id::TEXT;
        RAISE NOTICE 'Converted export_history.user_id to TEXT';
    END IF;
END $$;

-- Verify all tables now have TEXT user_id
SELECT 
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE table_schema = 'public'
AND column_name = 'user_id'
AND table_name IN (
    'health_insights',
    'health_predictions', 
    'shadow_patterns',
    'strategic_moves',
    'analysis_generation_log',
    'user_refresh_limits',
    'export_history'
)
ORDER BY table_name;
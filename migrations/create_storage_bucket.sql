-- Create storage bucket for medical photos if it doesn't exist
-- This needs to be run via Supabase Dashboard SQL editor

-- Enable storage extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "storage";

-- Create bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'medical-photos',
    'medical-photos',
    false, -- Private bucket
    10485760, -- 10MB limit
    ARRAY['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp']
)
ON CONFLICT (id) DO UPDATE
SET 
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];

-- RLS Policies for storage bucket
-- Allow authenticated users to upload their own files
CREATE POLICY "Users can upload their own medical photos" ON storage.objects
FOR INSERT WITH CHECK (
    bucket_id = 'medical-photos' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Allow users to view their own files
CREATE POLICY "Users can view their own medical photos" ON storage.objects
FOR SELECT USING (
    bucket_id = 'medical-photos' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Allow users to delete their own files
CREATE POLICY "Users can delete their own medical photos" ON storage.objects
FOR DELETE USING (
    bucket_id = 'medical-photos' 
    AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Service role bypass (for backend operations)
CREATE POLICY "Service role bypass" ON storage.objects
FOR ALL USING (
    auth.role() = 'service_role'
);
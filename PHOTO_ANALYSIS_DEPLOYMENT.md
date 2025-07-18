# Photo Analysis Deployment Guide

## Prerequisites
1. Ensure these environment variables are set in Railway:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY` or `SUPABASE_SERVICE_ROLE_KEY`
   - `OPENROUTER_API_KEY`
   - `SUPABASE_STORAGE_BUCKET` (optional, defaults to 'medical-photos')

## Step 1: Create Storage Bucket in Supabase
Run this SQL in your Supabase Dashboard SQL editor:

```sql
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
ON CONFLICT (id) DO NOTHING;
```

## Step 2: Apply Database Migrations
Run the migrations in order:
1. `/migrations/photo_analysis_tables.sql` - Creates all required tables
2. `/migrations/create_storage_bucket.sql` - Sets up storage bucket and RLS policies

## Step 3: Deploy to Railway
The latest commit fixes the photo analysis download error. Deploy it to Railway.

## Step 4: Test the Deployment

### 1. Check Health Endpoint
```bash
curl https://your-app.railway.app/api/photo-analysis/health
```

### 2. Check Storage Configuration
```bash
curl https://your-app.railway.app/api/photo-analysis/debug/storage
```

This should show:
- `bucket_exists: true`
- `storage_bucket: "medical-photos"`

### 3. Test Photo Upload Flow
```javascript
// 1. Create session
const sessionResponse = await fetch('/api/photo-analysis/sessions', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'your-user-id',
    condition_name: 'Test condition',
    description: 'Testing photo upload'
  })
});

// 2. Upload photos
const formData = new FormData();
formData.append('photos', photoFile);
formData.append('user_id', 'your-user-id');
formData.append('session_id', sessionData.session_id);

const uploadResponse = await fetch('/api/photo-analysis/upload', {
  method: 'POST',
  body: formData
});

// 3. Analyze photos
const analyzeResponse = await fetch('/api/photo-analysis/analyze', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    session_id: sessionData.session_id,
    photo_ids: uploadData.uploaded_photos.map(p => p.id)
  })
});
```

## Troubleshooting

### 500 Error on /analyze endpoint
1. Check Railway logs for specific error messages
2. Verify storage bucket exists using debug endpoint
3. Ensure SERVICE_KEY is set (not just ANON_KEY)
4. Check that uploaded photos have `storage_url` in database

### CORS Issues
- Frontend URL must be in `ALLOWED_ORIGINS` env var or set to "*"

### Storage Issues
- Run debug script locally: `python debug_photo_analysis.py`
- Check Supabase dashboard for storage bucket status
- Verify RLS policies are correctly applied

## What This Fix Changes
1. **Proper download handling**: The Supabase storage client returns different response types depending on the version. The fix handles all possible response types:
   - Response objects with `.content` attribute
   - Direct bytes responses
   - File-like objects with `.read()` method
   - Dict responses with 'data' key
   - Objects with `.data` attribute

2. **Better error logging**: Added debug logging to help diagnose issues in production

3. **Configurable storage bucket**: Can now set via `SUPABASE_STORAGE_BUCKET` env var

4. **Debug endpoints**: Added `/api/photo-analysis/debug/storage` to check configuration
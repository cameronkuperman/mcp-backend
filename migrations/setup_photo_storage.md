# Setting up Supabase Storage for Photo Analysis

## 1. Create Storage Bucket

Go to your Supabase Dashboard → Storage → Create a new bucket:

- **Name**: `medical-photos`
- **Public**: ❌ No (Keep it private)
- **File size limit**: 10MB
- **Allowed MIME types**: `image/jpeg, image/png, image/heic, image/heif, image/webp`

## 2. Bucket Policies

After creating the bucket, set up the following RLS policies:

### SELECT Policy (View Photos)
```sql
-- Policy name: Users can view their own photos
(bucket_id = 'medical-photos' AND auth.uid()::text = (storage.foldername(name))[1])
```

### INSERT Policy (Upload Photos)
```sql
-- Policy name: Users can upload to their folder
(bucket_id = 'medical-photos' AND auth.uid()::text = (storage.foldername(name))[1])
```

### UPDATE Policy (Update Photos)
```sql
-- Policy name: Users can update their own photos
(bucket_id = 'medical-photos' AND auth.uid()::text = (storage.foldername(name))[1])
```

### DELETE Policy (Delete Photos)
```sql
-- Policy name: Users can delete their own photos
(bucket_id = 'medical-photos' AND auth.uid()::text = (storage.foldername(name))[1])
```

## 3. Storage Structure

Photos will be stored with the following path structure:
```
medical-photos/
└── {user_id}/
    └── {session_id}/
        └── {timestamp}_{filename}
```

## 4. Service Role Access

The backend uses the SERVICE_ROLE_KEY for storage operations, which bypasses RLS. This allows:
- Creating signed URLs for temporary access
- Managing photos on behalf of users
- Cleanup operations

## 5. Environment Variables

Ensure these are set in your `.env` file:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## 6. Testing Storage

You can test the storage setup with:
```bash
curl -X POST http://localhost:8000/api/photo-analysis/upload \
  -H "Content-Type: multipart/form-data" \
  -F "photos=@test_image.jpg" \
  -F "user_id=test-user-id" \
  -F "condition_name=Test Rash"
```

## Security Notes

1. **Signed URLs**: All photo access uses signed URLs with 1-hour expiry
2. **Path-based isolation**: Each user's photos are isolated by user_id in the path
3. **Service key**: Only the backend has the service key for full access
4. **No public access**: The bucket is private, preventing direct URL access

## Cleanup Considerations

For production, consider:
1. Implementing a retention policy (e.g., delete photos after 1 year)
2. Regular cleanup of orphaned files
3. Storage quota monitoring per user
4. Compression before upload on the frontend
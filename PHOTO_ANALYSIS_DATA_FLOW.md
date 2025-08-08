# Photo Analysis Data Flow Documentation

## Overview
The photo analysis system retrieves and manages medical images and their analysis history through a sophisticated data flow involving Supabase storage and database tables.

## Data Storage Architecture

### Database Tables
1. **photo_sessions** - Stores session metadata (user_id, condition_name, dates)
2. **photo_uploads** - Stores individual photo records with metadata
3. **photo_analyses** - Stores AI analysis results for photos

### Storage Bucket
- Uses Supabase Storage bucket for actual image files
- Sensitive photos can be temporarily stored as base64 in database

## Key Data Retrieval Patterns

### 1. Session History Retrieval
When fetching previous sessions (`GET /api/photo-analysis/sessions`):
```
user_id → photo_sessions table → session list with metadata
```

### 2. Photo Retrieval for Analysis
When analyzing photos (`POST /api/photo-analysis/analyze`):
```
photo_ids → photo_uploads table → storage_url → Supabase Storage → image data
```

### 3. Analysis History Retrieval
When getting analysis history (`GET /api/photo-analysis/session/{session_id}/analysis-history`):
```
session_id → photo_analyses table → all analyses
           → photo_uploads table → all photos
           → Generate signed URLs (24hr expiry) for viewing
```

## Smart Photo Batching
When comparing many photos (>40), the system uses `SmartPhotoBatcher`:
- Always includes first photo (baseline)
- Always includes 5 most recent photos
- Intelligently selects middle photos based on:
  - Time gaps between photos
  - Previous analysis confidence scores
  - Detected changes in prior comparisons

## Comparison Logic
When `comparison_photo_ids` are provided:
1. Fetches comparison photos from `photo_uploads` table
2. Downloads images from Supabase Storage
3. Sends both current and comparison photos to AI model
4. AI performs visual comparison and trend analysis
5. Results stored with comparison metadata

## Data Flow Example
```
User uploads photo →
  1. Categorize photo (medical_normal/sensitive/unclear)
  2. Store in Supabase Storage (if not sensitive)
  3. Create photo_uploads record
  4. If auto_compare enabled:
     - Fetch previous photos from session
     - Apply smart batching if >40 photos
  5. Send to AI model (GPT-5 or Gemini 2.5 Pro)
  6. Store analysis in photo_analyses table
  7. Return analysis with signed URLs for viewing
```

## Security Considerations
- Sensitive photos stored temporarily as base64
- All storage URLs are signed with expiration (1-24 hours)
- Session-based access control
- Soft delete for data retention

## Models Used
- **Primary**: `openai/gpt-5` for photo analysis
- **Fallback**: `google/gemini-2.5-pro` for vision tasks
- **Ultra Think**: `x-ai/grok-4` for complex reasoning

## Ultra Think Feature
The Ultra Think endpoint (`/api/deep-dive/ultra-think`) provides maximum reasoning capabilities:
- Uses Grok 4 model for advanced pattern recognition
- Analyzes complete session history including Q&A and medical data
- Identifies patterns missed by standard analysis
- Considers rare conditions and complex interactions
- Provides confidence progression tracking
- Available after initial analysis is complete (analysis_ready or completed state)

## Key Features
- Automatic comparison with previous photos
- Smart batching for large photo sets
- Timeline navigation with full history
- 24-hour signed URLs for secure access
- Support for sensitive content handling
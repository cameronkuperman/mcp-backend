# Photo Analysis API Documentation

## Overview
The Photo Analysis API provides AI-powered medical image analysis with privacy-focused handling of sensitive content. The system categorizes photos, provides medical assessments, tracks conditions over time, and generates comprehensive reports.

## Key Features
- **Smart Categorization**: Automatically classifies photos into appropriate categories
- **Privacy Protection**: Sensitive photos analyzed without permanent storage
- **Medical Analysis**: Detailed AI-powered assessment using Gemini 2.5 Pro
- **Progress Tracking**: Compare photos over time (non-sensitive only)
- **Report Integration**: Include photo analyses in comprehensive medical reports

## Photo Categories

### 1. `medical_normal`
Standard medical conditions safe for storage:
- Skin conditions (rashes, acne, eczema, psoriasis)
- Injuries (cuts, bruises, sprains)
- Visible infections (non-intimate areas)
- Post-surgical healing (non-intimate)
- Any medical condition NOT in private areas

### 2. `medical_sensitive`
Medical conditions in intimate areas:
- Genital conditions
- Anal/perineal conditions
- **Important**: These photos are analyzed but NOT stored permanently
- Analysis results are kept forever, only photos are temporary

### 3. `medical_gore`
Severe but legitimate medical content:
- Deep wounds
- Active surgical procedures
- Severe trauma
- Major burns

### 4. `unclear`
Photos that cannot be properly analyzed:
- Too blurry
- Poor lighting
- Obstructed view

### 5. `non_medical`
Not medical content

### 6. `inappropriate`
Illegal content (extremely rare)

## Sensitive Photo Workflow

### How It Works
1. **Upload**: Photo is uploaded and categorized
2. **Temporary Storage**: If sensitive, base64 data stored in `temporary_data` field
3. **Analysis**: Full medical analysis performed normally
4. **Cleanup**: Photo data deleted after 24 hours
5. **Results Persist**: Analysis results kept permanently

### User Experience
When a sensitive photo is detected, the frontend should display:
```
⚠️ Sensitive Content Detected

This photo contains sensitive medical content. 

What will happen:
✓ Photo will be analyzed by our medical AI
✓ Analysis results will be saved permanently
✗ Photo will NOT be stored permanently
✗ You cannot track visual changes over time

Options:
[Proceed with Analysis] [Retake Different Photo]
```

### Technical Implementation
```json
// Sensitive photo upload response
{
  "session_id": "uuid",
  "uploaded_photos": [{
    "id": "photo-uuid",
    "category": "medical_sensitive",
    "stored": false,
    "preview_url": null
  }],
  "requires_action": {
    "type": "sensitive_modal",
    "affected_photos": ["photo-uuid"],
    "message": "Sensitive content detected. Photos will be analyzed temporarily without permanent storage."
  }
}
```

## API Endpoints

### 1. Create Photo Session
```
POST /api/photo-analysis/sessions
Content-Type: application/json

{
  "user_id": "user-uuid",
  "condition_name": "Skin Rash on Arm",
  "description": "Red, itchy rash that appeared 3 days ago"
}

Response:
{
  "session_id": "session-uuid",
  "condition_name": "Skin Rash on Arm",
  "created_at": "2025-01-31T..."
}
```

### 2. Categorize Photo
```
POST /api/photo-analysis/categorize
Content-Type: multipart/form-data

photo: [file]
session_id: "session-uuid" (optional)

Response:
{
  "category": "medical_normal",
  "confidence": 0.95,
  "subcategory": "dermatological_rash"
}
```

### 3. Upload Photos
```
POST /api/photo-analysis/upload
Content-Type: multipart/form-data

photos: [files] (max 5)
session_id: "session-uuid"
user_id: "user-uuid"
condition_name: "Condition Name" (if new session)
description: "Optional description"

Response:
{
  "session_id": "session-uuid",
  "uploaded_photos": [
    {
      "id": "photo-uuid",
      "category": "medical_normal",
      "stored": true,
      "preview_url": "https://..."
    }
  ],
  "requires_action": null
}
```

### 4. Analyze Photos
```
POST /api/photo-analysis/analyze
Content-Type: application/json

{
  "session_id": "session-uuid",
  "photo_ids": ["photo-uuid-1", "photo-uuid-2"],
  "context": "Additional context from user",
  "comparison_photo_ids": ["older-photo-uuid"],
  "temporary_analysis": false
}

Response:
{
  "analysis_id": "analysis-uuid",
  "analysis": {
    "primary_assessment": "Atopic dermatitis (eczema)",
    "confidence": 85,
    "visual_observations": [
      "Red, inflamed patches on forearm",
      "Visible scaling and dryness",
      "No signs of infection"
    ],
    "differential_diagnosis": [
      "Contact dermatitis",
      "Psoriasis"
    ],
    "recommendations": [
      "Apply fragrance-free moisturizer 3x daily",
      "Avoid hot showers",
      "See dermatologist if no improvement in 1 week"
    ],
    "red_flags": [],
    "trackable_metrics": [
      {
        "metric_name": "Rash Size",
        "current_value": 5,
        "unit": "cm",
        "suggested_tracking": "weekly"
      }
    ]
  },
  "comparison": {
    "days_between": 7,
    "changes": {
      "size": {"from": 3, "to": 5, "unit": "cm", "change": 67},
      "color": {"description": "Increased redness"},
      "texture": {"description": "More scaling visible"}
    },
    "trend": "worsening",
    "ai_summary": "The rash has expanded and shows increased inflammation"
  },
  "expires_at": null
}
```

### 5. Get Photo Sessions
```
GET /api/photo-analysis/sessions?user_id=uuid&limit=20&offset=0

Response:
{
  "sessions": [
    {
      "id": "session-uuid",
      "condition_name": "Skin Rash",
      "created_at": "2025-01-31T...",
      "last_photo_at": "2025-01-31T...",
      "photo_count": 3,
      "analysis_count": 2,
      "is_sensitive": false,
      "latest_summary": "Atopic dermatitis",
      "thumbnail_url": "https://..."
    }
  ],
  "total": 5,
  "has_more": false
}
```

### 6. Approve Tracking from Photo Analysis
```
POST /api/photo-analysis/tracking/approve
Content-Type: application/json

{
  "analysis_id": "analysis-uuid",
  "metric_configs": [
    {
      "metric_name": "Rash Size",
      "y_axis_label": "Size (cm)",
      "y_axis_min": 0,
      "y_axis_max": 20,
      "initial_value": 5
    }
  ]
}

Response:
{
  "tracking_configs": [
    {
      "id": "config-uuid",
      "metric_name": "Rash Size",
      "configuration_id": "config-uuid"
    }
  ],
  "dashboard_url": "/dashboard#tracking"
}
```

## Error Handling

### Retry Logic
- All AI calls automatically retry up to 3 times with exponential backoff
- Primary model: `google/gemini-2.5-pro`
- Fallback model: `google/gemini-2.0-flash-exp:free`

### Common Errors
```json
// File too large
{
  "status_code": 413,
  "detail": "File too large (max 10MB)"
}

// Invalid file type
{
  "status_code": 400,
  "detail": "Invalid file type. Allowed: image/jpeg, image/png, image/heic, image/heif, image/webp"
}

// Sensitive photo without data
{
  "status_code": 400,
  "detail": "Cannot analyze photo without data"
}
```

## Best Practices

### Frontend Implementation
1. **Size Validation**: Check file size before upload (10MB max)
2. **Type Validation**: Only allow supported image types
3. **Sensitive Content Modal**: Always show warning for sensitive photos
4. **Progress Indicators**: Show upload and analysis progress
5. **Error Recovery**: Allow retry on failure

### Privacy Considerations
1. **No Permanent Storage**: Sensitive photos never stored permanently
2. **24-Hour Cleanup**: Automatic deletion of temporary data
3. **User Consent**: Always get explicit consent before analyzing sensitive content
4. **Secure Transmission**: Use HTTPS for all photo uploads
5. **Access Control**: Photos only accessible to uploading user

## Database Schema

### Required Migration
Run this migration to support sensitive photo handling:
```sql
ALTER TABLE photo_uploads 
ADD COLUMN IF NOT EXISTS temporary_data TEXT;

CREATE INDEX IF NOT EXISTS idx_photo_uploads_temporary_data 
ON photo_uploads(uploaded_at) 
WHERE temporary_data IS NOT NULL;
```

## Integration with Reports

### Photo Analysis Report
Generate a dedicated photo analysis report:
```
POST /api/photo-analysis/reports/photo-analysis
{
  "user_id": "user-uuid",
  "session_ids": ["session-uuid-1", "session-uuid-2"],
  "include_visual_timeline": true,
  "include_tracking_data": true,
  "time_range_days": 30  // Optional, null for all time
}
```

### Integration with Other Reports
Photo analyses can be included in any report type by adding `photo_session_ids`:

#### Specialist Reports
```
POST /api/reports/specialist
{
  "analysis_id": "analysis-uuid",
  "specialty": "dermatology",
  "photo_session_ids": ["session-uuid"]  // Optional
}
```

#### Comprehensive Reports
```
POST /api/reports/comprehensive
{
  "analysis_id": "analysis-uuid",
  "photo_session_ids": ["session-uuid"]  // Optional
}
```

When photo data is included, reports will contain:
- Visual assessments and observations
- Progression tracking (non-sensitive photos only)
- AI-generated insights from visual data
- Correlation with other health data
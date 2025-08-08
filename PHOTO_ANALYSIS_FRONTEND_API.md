# Photo Analysis Frontend API Guide

## Core Endpoints for Frontend

### 1. Get User's Photo Sessions
```
GET /api/photo-analysis/sessions?user_id={user_id}&limit=20&offset=0
```
**Returns:** List of all photo sessions for user
```json
{
  "sessions": [
    {
      "id": "session_uuid",
      "user_id": "user_id",
      "condition_name": "Mole on arm",
      "created_at": "2024-01-20T10:00:00Z",
      "last_photo_at": "2024-01-25T14:30:00Z",
      "photo_count": 5,
      "analysis_count": 3
    }
  ],
  "total": 10,
  "has_more": false
}
```

### 2. Get Session Details with Photos
```
GET /api/photo-analysis/session/{session_id}
```
**Returns:** Complete session with all photos and analyses
```json
{
  "session": {
    "id": "session_uuid",
    "condition_name": "Mole on arm",
    "created_at": "2024-01-20T10:00:00Z"
  },
  "photos": [
    {
      "id": "photo_uuid",
      "uploaded_at": "2024-01-20T10:00:00Z",
      "preview_url": "https://signed-url-expires-24hr.com/..."
    }
  ],
  "analyses": [
    {
      "id": "analysis_uuid",
      "created_at": "2024-01-20T10:05:00Z",
      "confidence": 85,
      "analysis_data": {...}
    }
  ]
}
```

### 3. Get Analysis History (For Timeline View)
```
GET /api/photo-analysis/session/{session_id}/analysis-history?current_analysis_id={optional}
```
**Returns:** All analyses with photo URLs for timeline navigation
```json
{
  "session": {
    "id": "session_uuid",
    "condition_name": "Mole on arm"
  },
  "analyses": [
    {
      "id": "analysis_uuid",
      "date": "2024-01-20",
      "photo_url": "https://signed-url-24hr.com/...",
      "thumbnail_url": "https://signed-url-24hr.com/...",
      "confidence": 85,
      "trend": "improving",
      "key_metrics": {
        "size_mm": 4.5
      },
      "is_current": false,
      "analysis_number": 1
    }
  ],
  "navigation": {
    "current_index": 2,
    "total_analyses": 5,
    "has_previous": true,
    "has_next": true
  }
}
```

### 4. Upload & Analyze Flow

#### Step 1: Create Session (first time only)
```
POST /api/photo-analysis/sessions
Body: {
  "user_id": "user_id",
  "condition_name": "Mole on arm",
  "description": "Tracking suspicious mole"
}
```

#### Step 2: Upload Photos
```
POST /api/photo-analysis/upload
Form Data:
- session_id: "session_uuid"
- photos: [File, File, ...]  (multipart/form-data)
```
**Returns:**
```json
{
  "session_id": "session_uuid",
  "uploaded_photos": [
    {
      "id": "photo_uuid",
      "category": "medical_normal",
      "preview_url": "https://signed-url-1hr.com/..."
    }
  ]
}
```

#### Step 3: Analyze Photos
```
POST /api/photo-analysis/analyze
Body: {
  "session_id": "session_uuid",
  "photo_ids": ["photo_uuid1", "photo_uuid2"],
  "comparison_photo_ids": ["old_photo_uuid1"],  // Optional - for comparison
  "context": "2 weeks after treatment"
}
```
**Returns:**
```json
{
  "analysis_id": "analysis_uuid",
  "confidence": 85,
  "analysis": {
    "condition_assessment": "...",
    "severity": "mild",
    "recommendations": ["..."]
  },
  "comparison": {  // If comparison_photo_ids provided
    "trend": "improving",
    "changes": {
      "size": "decreased by 10%",
      "color": "lighter"
    }
  }
}
```

### 5. Follow-up Upload (with Auto-Compare)
```
POST /api/photo-analysis/session/{session_id}/follow-up
Form Data:
- photos: [File, File, ...]
- auto_compare: true  // Automatically compares with previous photos
- notes: "After 2 weeks of treatment"
```
**Returns:** Combined upload + analysis with comparison

### 6. Timeline View
```
GET /api/photo-analysis/session/{session_id}/timeline
```
**Returns:** Chronological timeline data for visualization
```json
{
  "timeline_points": [
    {
      "date": "2024-01-20",
      "photo_count": 2,
      "analysis_id": "analysis_uuid",
      "confidence": 75,
      "size_mm": 4.5,
      "trend": "baseline"
    }
  ],
  "summary": {
    "overall_trend": "improving",
    "total_days": 30,
    "improvement_percentage": 25
  }
}
```

## Key Implementation Notes

1. **Photo URLs expire in 24 hours** - Cache or refresh as needed
2. **Use `follow-up` endpoint** for subsequent uploads - handles comparison automatically
3. **Smart Batching** - When >40 photos, system auto-selects most relevant for comparison
4. **Sensitive photos** - Stored as base64 temporarily, no permanent storage
5. **Analysis History** endpoint provides everything needed for timeline/gallery view

## Frontend Display Flow
1. User clicks "View History" → Call `/sessions` endpoint
2. Select session → Call `/session/{id}/analysis-history`
3. Display timeline with photos using provided URLs
4. Navigate between analyses using `navigation` metadata
5. For new photos → Use `/follow-up` endpoint with `auto_compare=true`